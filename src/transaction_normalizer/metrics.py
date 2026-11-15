"""Cálculo de métricas monetarias y conteos sin convertir a ``float``."""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any, Iterable


def calculate_metrics(valid: Iterable[dict[str, Any]], invalid: Iterable[dict[str, Any]], total_processed: int | None = None) -> dict[str, Any]:
    """Calcula métricas de válidos; los diagnósticos solo cuentan como inválidos."""

    valid_rows = list(valid)
    invalid_rows = list(invalid)
    total = len(valid_rows) + len(invalid_rows) if total_processed is None else int(total_processed)
    status_counts = Counter(row.get("status") for row in valid_rows)
    currency_counts = Counter(row.get("currency") for row in valid_rows)
    source_counts = Counter(row.get("source") for row in valid_rows)
    all_totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    success_totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for row in valid_rows:
        amount = row["amount"]
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        all_totals[row["currency"]] += amount
        if row["status"] == "SUCCESS":
            success_totals[row["currency"]] += amount
    return {
        "total_processed": total,
        "valid_count": len(valid_rows),
        "invalid_count": len(invalid_rows),
        "status_counts": {key: count for key, count in status_counts.items() if key is not None},
        "currency_counts": {key: count for key, count in currency_counts.items() if key is not None},
        "source_counts": {key: count for key, count in source_counts.items() if key is not None},
        "all_valid_totals_by_currency": dict(all_totals),
        "success_totals_by_currency": dict(success_totals),
    }

