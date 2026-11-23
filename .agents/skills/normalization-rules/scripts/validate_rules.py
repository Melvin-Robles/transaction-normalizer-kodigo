"""Validate rules.json and report adapter compatibility without changing it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from transaction_normalizer.config import load_rules  # noqa: E402
from transaction_normalizer.models import NormalizerError  # noqa: E402
from transaction_normalizer.sources.registry import build_source_registry  # noqa: E402
from transaction_normalizer.validation import SUPPORTED_AMOUNT_STYLES  # noqa: E402


def build_report(rules_path: Path) -> dict[str, Any]:
    """Return confirmed configuration findings and separate recommendations."""

    rules = load_rules(rules_path)
    registry = build_source_registry(rules)
    errors: list[str] = []
    recommendations: list[str] = []
    source_reports: list[dict[str, Any]] = []

    for source_name, definition in rules["sources"].items():
        matches = registry.matching({definition["discriminator"]: True})
        adapter_name = matches[0].__class__.__name__ if len(matches) == 1 else None
        if len(matches) != 1:
            errors.append(f"La fuente {source_name} no tiene un discriminador resoluble por el registro.")
        if definition["amount_style"] not in SUPPORTED_AMOUNT_STYLES:
            errors.append(
                f"La fuente {source_name} usa amount_style no soportado: {definition['amount_style']}."
            )
        if not definition["status_map"]:
            errors.append(f"La fuente {source_name} no tiene status_map.")
        if not definition["required_fields"]:
            errors.append(f"La fuente {source_name} no declara required_fields.")
        if adapter_name == "ConfiguredSourceAdapter":
            recommendations.append(
                f"La fuente {source_name} usa el adaptador genérico; evaluar un adaptador específico si requiere parsing propio."
            )
        source_reports.append(
            {
                "name": source_name,
                "discriminator": definition["discriminator"],
                "adapter": adapter_name,
                "required_fields": list(definition["required_fields"]),
                "amount_style": definition["amount_style"],
                "currency_style": definition["currency_style"],
                "status_values": sorted(str(key) for key in definition["status_map"]),
                "timezone_required": definition["timezone_required"],
            }
        )

    policies = rules["policies"]
    if policies["max_id_length"] <= 0:
        errors.append("max_id_length debe ser positivo.")
    if policies["max_file_bytes"] <= 0:
        errors.append("max_file_bytes debe ser positivo.")
    if policies["max_records"] <= 0:
        errors.append("max_records debe ser positivo.")
    if policies["allow_extra_fields"]:
        recommendations.append("allow_extra_fields está activo; revisar si el lote debe aplicar una política de campos desconocidos.")
    if not policies["exchange_rate_conversion"]:
        recommendations.append("No hay conversión de divisas; mantener las métricas separadas por moneda.")

    return {
        "rules_file": rules_path.name,
        "schema_version": rules["schema_version"],
        "valid": not errors,
        "errors": errors,
        "recommendations": recommendations,
        "currencies": sorted(rules["currencies"]),
        "policies": {
            "max_amount": str(policies["max_amount"]),
            "max_id_length": policies["max_id_length"],
            "max_file_bytes": policies["max_file_bytes"],
            "max_records": policies["max_records"],
            "output_timezone": policies["output_timezone"],
        },
        "normalized_schema": rules["normalized_schema"],
        "sources": source_reports,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida reglas sin modificar rules.json.")
    parser.add_argument(
        "--rules",
        type=Path,
        default=REPO_ROOT / "config" / "rules.json",
        help="Archivo de reglas a revisar",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        path = args.rules.resolve()
        if not path.is_file():
            raise OSError(f"No existe el archivo de reglas: {path}")
        report = build_report(path)
    except (OSError, NormalizerError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
