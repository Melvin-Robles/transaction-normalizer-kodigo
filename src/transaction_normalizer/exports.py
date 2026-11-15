"""Serialización segura de salidas sin exponer la carga original."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any


_NORMALIZED_FIELDS = ("id", "amount", "currency", "timestamp", "status", "source")


def serialize_normalized_json(records: list[dict[str, Any]]) -> str:
    """Exporta seis campos exactos y deja ``amount`` como número JSON."""

    rows: list[str] = []
    for record in records:
        values: list[str] = []
        for field in _NORMALIZED_FIELDS:
            values.append(json.dumps(field, ensure_ascii=False) + ":" + _encode_value(record[field], field))
        rows.append("{" + ",".join(values) + "}")
    return "[" + ",".join(rows) + "]"


def _encode_value(value: Any, field: str) -> str:
    if field == "amount":
        try:
            decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
            if not decimal_value.is_finite() or decimal_value.as_tuple().exponent < -2:
                raise ValueError("importe no exportable")
            return format(decimal_value.quantize(Decimal("0.01")), "f")
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError("El importe no puede exportarse como número JSON.") from exc
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def serialize_errors_json(errors: list[dict[str, Any]]) -> str:
    """Exporta solo diagnósticos controlados, nunca el registro crudo."""

    return json.dumps(errors, ensure_ascii=False, separators=(",", ":"))

