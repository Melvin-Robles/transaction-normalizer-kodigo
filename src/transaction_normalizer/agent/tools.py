"""Herramientas de auditoría agregadas y de solo lectura."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Mapping

from ..models import BatchProcessingResult


class ToolError(Exception):
    """Error controlado al seleccionar o ejecutar una herramienta."""


class UnknownToolError(ToolError):
    """La herramienta solicitada no existe."""


class ToolArgumentError(ToolError):
    """Los argumentos de una herramienta no cumplen el contrato."""


def _decimal_map(values: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in sorted(values.items()):
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
        result[key] = format(decimal_value, ".2f")
    return result


def _require_batch(batch: BatchProcessingResult) -> BatchProcessingResult:
    if not isinstance(batch, BatchProcessingResult):
        raise ToolArgumentError("El contexto de auditoría no es un BatchProcessingResult válido.")
    return batch


def query_batch_metrics(batch: BatchProcessingResult) -> dict[str, Any]:
    """Devuelve conteos y calidad sin incluir filas originales."""

    batch = _require_batch(batch)
    metrics = batch.metrics
    total = int(metrics["total_processed"])
    valid = int(metrics["valid_count"])
    return {
        "total_processed": total,
        "valid_count": valid,
        "invalid_count": int(metrics["invalid_count"]),
        "quality_percent": round(valid / total * 100, 2) if total else 0.0,
        "status_counts": dict(sorted(metrics["status_counts"].items())),
    }


def query_error_distribution(batch: BatchProcessingResult) -> dict[str, Any]:
    """Agrupa diagnósticos por código y fuente identificada."""

    batch = _require_batch(batch)
    errors = batch.result.invalid
    by_code = Counter(row["error_code"] for row in errors)
    by_source = Counter(row.get("source") or "UNKNOWN" for row in errors)
    return {
        "invalid_count": len(errors),
        "by_code": dict(sorted(by_code.items())),
        "by_source": dict(sorted(by_source.items())),
    }


def query_source_statistics(batch: BatchProcessingResult) -> dict[str, Any]:
    """Calcula estadísticas por fuente usando válidos e inválidos."""

    batch = _require_batch(batch)
    valid_by_source = Counter(row["source"] for row in batch.result.valid)
    invalid_by_source = Counter(row.get("source") or "UNKNOWN" for row in batch.result.invalid)
    sources = sorted(set(valid_by_source) | set(invalid_by_source))
    statistics: dict[str, dict[str, Any]] = {}
    for source in sources:
        valid = valid_by_source.get(source, 0)
        invalid = invalid_by_source.get(source, 0)
        processed = valid + invalid
        statistics[source] = {
            "processed": processed,
            "valid": valid,
            "invalid": invalid,
            "quality_percent": round(valid / processed * 100, 2) if processed else 0.0,
        }
    return statistics


def query_currency_totals(batch: BatchProcessingResult) -> dict[str, Any]:
    """Devuelve conteos y sumas por moneda sin mezclarlas."""

    batch = _require_batch(batch)
    metrics = batch.metrics
    return {
        "valid_count_by_currency": dict(sorted(metrics["currency_counts"].items())),
        "all_valid_totals_by_currency": _decimal_map(metrics["all_valid_totals_by_currency"]),
        "success_totals_by_currency": _decimal_map(metrics["success_totals_by_currency"]),
    }


def query_normalization_rules(rules: dict[str, Any]) -> dict[str, Any]:
    """Devuelve una vista segura y explicable de la configuración activa."""

    if not isinstance(rules, dict) or not isinstance(rules.get("sources"), dict):
        raise ToolArgumentError("Las reglas no tienen una estructura válida.")
    policies = rules.get("policies", {})
    sources: list[dict[str, Any]] = []
    for name, definition in sorted(rules["sources"].items()):
        sources.append(
            {
                "name": name,
                "discriminator": definition.get("discriminator"),
                "required_fields": list(definition.get("required_fields", [])),
                "amount_style": definition.get("amount_style"),
                "currency_style": definition.get("currency_style"),
                "date_formats": list(definition.get("date_formats", [])),
                "timezone_required": definition.get("timezone_required"),
                "status_map": dict(definition.get("status_map", {})),
            }
        )
    return {
        "schema_version": rules.get("schema_version"),
        "currencies": sorted(rules.get("currencies", {})),
        "policies": {
            key: policies[key]
            for key in (
                "max_amount",
                "max_id_length",
                "max_file_bytes",
                "max_records",
                "output_timezone",
                "exchange_rate_conversion",
            )
            if key in policies
        },
        "normalized_schema": rules.get("normalized_schema", {}),
        "sources": sources,
    }


@dataclass(frozen=True)
class ToolDefinition:
    """Metadatos de una herramienta invocable por el agente."""

    name: str
    description: str
    handler: Callable[[], dict[str, Any]]

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        }


class AuditToolset:
    """Registro cerrado de herramientas de auditoría de solo lectura."""

    def __init__(self, batch: BatchProcessingResult, rules: dict[str, Any]) -> None:
        self._definitions = {
            "query_batch_metrics": ToolDefinition(
                "query_batch_metrics",
                "Consulta conteos, calidad y estados del lote.",
                lambda: query_batch_metrics(batch),
            ),
            "query_error_distribution": ToolDefinition(
                "query_error_distribution",
                "Consulta códigos y distribución de diagnósticos inválidos.",
                lambda: query_error_distribution(batch),
            ),
            "query_source_statistics": ToolDefinition(
                "query_source_statistics",
                "Consulta estadísticas de calidad por fuente.",
                lambda: query_source_statistics(batch),
            ),
            "query_currency_totals": ToolDefinition(
                "query_currency_totals",
                "Consulta sumas y conteos separados por moneda.",
                lambda: query_currency_totals(batch),
            ),
            "query_normalization_rules": ToolDefinition(
                "query_normalization_rules",
                "Consulta las reglas de normalización activas.",
                lambda: query_normalization_rules(rules),
            ),
        }

    def available(self) -> list[dict[str, Any]]:
        """Devuelve esquemas seguros para un consumidor de herramientas."""

        return [self._definitions[name].schema() for name in sorted(self._definitions)]

    def invoke(self, name: str, arguments: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Valida argumentos y ejecuta únicamente una herramienta registrada."""

        if not isinstance(name, str) or name not in self._definitions:
            raise UnknownToolError(f"Herramienta desconocida: {name!r}")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, Mapping) or arguments:
            raise ToolArgumentError(f"{name} no acepta argumentos.")
        return self._definitions[name].handler()


_QUERY_TOOL_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("query_error_distribution", ("error", "errores", "inválid", "invalid", "diagnóstico", "rechazo")),
    ("query_source_statistics", ("fuente", "fuentes", "origen", "a/b/c")),
    ("query_currency_totals", ("moneda", "monedas", "divisa", "importe", "suma", "usd", "eur")),
    ("query_normalization_rules", ("regla", "rules", "configuración", "adaptador", "formato", "estado")),
    ("query_batch_metrics", ("métrica", "metricas", "calidad", "válid", "procesad", "resumen", "tasa")),
)

_INJECTION_MARKERS = ("ignore previous instructions", "ignore previous", "system prompt", "execute code", "run shell")


def select_tools(query: str) -> list[str]:
    """Selecciona herramientas por intención, sin ejecutar texto como código."""

    if not isinstance(query, str) or not query.strip():
        raise ToolArgumentError("La consulta debe ser un texto no vacío.")
    if len(query) > 2000:
        raise ToolArgumentError("La consulta supera el límite de 2000 caracteres.")
    normalized = query.casefold()
    if any(marker in normalized for marker in _INJECTION_MARKERS):
        raise ToolArgumentError("La consulta contiene una instrucción no permitida.")
    if "auditoría completa" in normalized or "auditoria completa" in normalized:
        return [
            "query_batch_metrics",
            "query_error_distribution",
            "query_source_statistics",
            "query_currency_totals",
            "query_normalization_rules",
        ]
    selected = [name for name, keywords in _QUERY_TOOL_KEYWORDS if any(keyword in normalized for keyword in keywords)]
    if not selected:
        raise UnknownToolError("No se pudo asociar la consulta a una herramienta segura.")
    return selected
