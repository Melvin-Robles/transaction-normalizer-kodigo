"""Generate a safe, deterministic audit report for a transaction JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from transaction_normalizer.config import load_rules  # noqa: E402
from transaction_normalizer.models import NormalizerError  # noqa: E402
from transaction_normalizer.service import TransactionProcessingService  # noqa: E402


def _decimal_map(values: dict[str, Decimal]) -> dict[str, str]:
    return {key: format(value, ".2f") for key, value in sorted(values.items())}


def _bucket(source: str | None) -> str:
    return source if source else "UNKNOWN"


def build_report(payload: bytes, rules_path: Path, input_name: str) -> dict[str, Any]:
    """Process a batch and return only aggregate and safe diagnostic data."""

    rules = load_rules(rules_path)
    batch = TransactionProcessingService(rules).process_document(payload)
    valid = batch.result.valid
    invalid = batch.result.invalid
    total = batch.metrics["total_processed"]
    valid_count = batch.metrics["valid_count"]
    quality = round((valid_count / total * 100) if total else 0, 2)

    error_counts = Counter(row["error_code"] for row in invalid)
    valid_by_source = Counter(row["source"] for row in valid)
    valid_by_currency = Counter(row["currency"] for row in valid)
    invalid_by_source = Counter(_bucket(row.get("source")) for row in invalid)

    source_names = sorted(set(valid_by_source) | {key for key in invalid_by_source if key != "UNKNOWN"})
    source_quality: dict[str, dict[str, Any]] = {}
    for source in source_names:
        source_valid = valid_by_source.get(source, 0)
        source_invalid = invalid_by_source.get(source, 0)
        source_total = source_valid + source_invalid
        source_quality[source] = {
            "processed": source_total,
            "valid": source_valid,
            "invalid": source_invalid,
            "quality_percent": round(source_valid / source_total * 100, 2) if source_total else 0,
        }

    recommendations: list[str] = []
    if total == 0:
        recommendations.append("El lote está vacío; no hay registros para evaluar.")
    elif not invalid:
        recommendations.append("No se detectaron registros inválidos en el lote.")
    else:
        top_code, top_count = error_counts.most_common(1)[0]
        recommendations.append(
            f"Priorizar la revisión de {top_code}: aparece en {top_count} de {len(invalid)} diagnóstico(s)."
        )
        if invalid_by_source.get("UNKNOWN", 0):
            recommendations.append(
                "Hay diagnósticos sin fuente identificada; revisar discriminadores o tipos de registro."
            )

    return {
        "input_file": input_name,
        "summary": {
            "total_processed": total,
            "valid_count": valid_count,
            "invalid_count": len(invalid),
            "quality_percent": quality,
        },
        "errors_by_code": dict(sorted(error_counts.items())),
        "valid_by_source": dict(sorted(valid_by_source.items())),
        "invalid_by_source": dict(sorted(invalid_by_source.items())),
        "source_quality": source_quality,
        "valid_by_currency": dict(sorted(valid_by_currency.items())),
        "totals_by_currency": _decimal_map(batch.metrics["all_valid_totals_by_currency"]),
        "success_totals_by_currency": _decimal_map(batch.metrics["success_totals_by_currency"]),
        "diagnostics": [
            {
                "index": row["index"],
                "source": row["source"],
                "error_code": row["error_code"],
                "message": row["message"],
            }
            for row in invalid
        ],
        "recommendations": recommendations,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audita un lote JSON sin modificar sus transacciones.")
    parser.add_argument("input", type=Path, help="Archivo JSON de transacciones")
    parser.add_argument(
        "--rules",
        type=Path,
        default=REPO_ROOT / "config" / "rules.json",
        help="Archivo de reglas; por defecto config/rules.json",
    )
    parser.add_argument("--output", type=Path, help="Ruta opcional para guardar el reporte JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        input_path = args.input.resolve()
        rules_path = args.rules.resolve()
        if not input_path.is_file():
            raise OSError(f"No existe el archivo de entrada: {input_path}")
        if args.output is not None and args.output.resolve() == input_path:
            raise OSError("La salida no puede sobrescribir el archivo de entrada.")
        report = build_report(input_path.read_bytes(), rules_path, input_path.name)
        rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.output is None:
            print(rendered, end="")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
    except (OSError, NormalizerError, UnicodeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
