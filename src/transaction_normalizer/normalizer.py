"""Compatibilidad pública para normalizar lotes de transacciones."""

from __future__ import annotations

from typing import Any

from .models import ProcessingResult
from .sources.registry import SourceRegistry, build_source_registry


def normalize_records(
    records: list[Any],
    rules: dict[str, Any],
    registry: SourceRegistry | None = None,
) -> ProcessingResult:
    """Normaliza un lote y conserva la API histórica basada en diccionarios."""

    result = ProcessingResult()
    source_registry = registry or build_source_registry(rules)
    seen: set[tuple[str, str]] = set()

    for index, record in enumerate(records):
        normalized, error = source_registry.normalize(record, index, rules, seen)
        if error is not None:
            result.invalid.append(error.to_dict())
        else:
            result.valid.append(normalized.to_dict())
            seen.add((normalized.source, normalized.id))
    return result

