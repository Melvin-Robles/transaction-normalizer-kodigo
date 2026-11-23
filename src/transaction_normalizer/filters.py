"""Filtros puros para resultados normalizados."""

from __future__ import annotations

from datetime import date
from typing import Any, Sequence


def filter_valid_records(
    valid: Sequence[dict[str, Any]],
    *,
    state: str | None = None,
    currency: str | None = None,
    source: str | None = None,
    query: str = "",
    date_range: date | tuple[date, date] | list[date] | None = None,
    sort_by: str = "Fecha",
    descending: bool = False,
) -> list[dict[str, Any]]:
    """Aplica la intersección de filtros y devuelve una nueva lista ordenada."""

    normalized_query = query.strip().casefold()
    filtered: list[dict[str, Any]] = []
    for row in valid:
        row_date = date.fromisoformat(row["timestamp"][:10])
        if state is not None and row["status"] != state:
            continue
        if currency is not None and row["currency"] != currency:
            continue
        if source is not None and row["source"] != source:
            continue
        if normalized_query and normalized_query not in row["id"].casefold():
            continue
        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            if row_date < date_range[0] or row_date > date_range[1]:
                continue
        elif isinstance(date_range, date) and row_date != date_range:
            continue
        filtered.append(row)

    sort_key = {
        "Fecha": lambda row: row["timestamp"],
        "Importe": lambda row: row["amount"],
        "ID": lambda row: row["id"].casefold(),
    }.get(sort_by)
    if sort_key is None:
        raise ValueError(f"Criterio de orden no soportado: {sort_by}")
    filtered.sort(key=sort_key, reverse=descending)
    return filtered
