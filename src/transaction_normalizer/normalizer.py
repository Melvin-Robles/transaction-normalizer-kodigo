"""Validación y transformación de registros por fuente."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from .config import configured_max_amount
from .models import ProcessingResult


_DIGITS = re.compile(r"^\d+$")
_MAJOR_AMOUNT = re.compile(r"^\d+(?:\.\d{1,2})?$")
_EURO_AMOUNT = re.compile(r"^€\s*\d+(?:,\d{1,2})?$")


def normalize_records(records: list[Any], rules: dict[str, Any]) -> ProcessingResult:
    """Normaliza cada entrada, conservando exactamente un diagnóstico si falla."""

    result = ProcessingResult()
    seen: set[tuple[str, str]] = set()
    sources = rules["sources"]
    for index, record in enumerate(records):
        valid, error = _normalize_one(record, index, rules, seen)
        if error is not None:
            result.invalid.append(error)
        else:
            result.valid.append(valid)
            seen.add((valid["source"], valid["id"]))
    return result


def _diagnostic(index: int, source: str | None, code: str, message: str) -> dict[str, Any]:
    return {"index": index, "source": source, "error_code": code, "message": message}


def _normalize_one(record: Any, index: int, rules: dict[str, Any], seen: set[tuple[str, str]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(record, dict):
        return None, _diagnostic(index, None, "INVALID_RECORD_TYPE", "El registro debe ser un objeto JSON.")

    sources = rules["sources"]
    matching = [name for name, definition in sources.items() if definition["discriminator"] in record]
    if len(matching) == 0:
        return None, _diagnostic(index, None, "UNKNOWN_SOURCE", "No se identificó una fuente conocida.")
    if len(matching) > 1:
        return None, _diagnostic(index, None, "AMBIGUOUS_SOURCE", "El registro contiene varios discriminadores de fuente.")
    source = matching[0]
    definition = sources[source]

    if "source" in record and _source_label(record["source"]) != source:
        return None, _diagnostic(index, source, "SOURCE_CONFLICT", "El campo source contradice la fuente detectada.")

    for field in definition["required_fields"]:
        if field not in record:
            return None, _diagnostic(index, source, "MISSING_FIELD", "Falta un campo obligatorio del registro.")

    identifier, error_code = _normalize_id(record[definition["id_field"]], definition["id_type"], rules)
    if error_code:
        return None, _diagnostic(index, source, "INVALID_ID", "El identificador no cumple el formato permitido.")

    amount, currency, amount_error = _normalize_amount_and_currency(record, definition, rules)
    if amount_error:
        return None, _diagnostic(index, source, amount_error, _amount_message(amount_error))

    timestamp = _normalize_timestamp(record[definition["timestamp_field"]], definition)
    if timestamp is None:
        return None, _diagnostic(index, source, "INVALID_TIMESTAMP", "La fecha no cumple el formato requerido.")

    status_value = record[definition["status_field"]]
    status_map = {str(k).strip().casefold(): v for k, v in definition["status_map"].items()}
    status = status_map.get(status_value.strip().casefold()) if isinstance(status_value, str) else None
    if status is None:
        return None, _diagnostic(index, source, "UNKNOWN_STATUS", "El estado no está configurado para esta fuente.")

    key = (source, identifier)
    if key in seen:
        return None, _diagnostic(index, source, "DUPLICATE_TRANSACTION", "Ya existe una transacción válida con la misma fuente e identificador.")

    return {
        "id": identifier,
        "amount": amount,
        "currency": currency,
        "timestamp": timestamp,
        "status": status,
        "source": source,
    }, None


def _source_label(value: Any) -> str | None:
    return value.strip().upper() if isinstance(value, str) else None


def _normalize_id(value: Any, id_type: str, rules: dict[str, Any]) -> tuple[str | None, str | None]:
    if id_type == "nonempty_string":
        if not isinstance(value, str) or not value.strip():
            return None, "INVALID_ID"
        identifier = value
    elif id_type == "nonnegative_integer_or_digits_string":
        if isinstance(value, bool):
            return None, "INVALID_ID"
        if isinstance(value, int):
            if value < 0:
                return None, "INVALID_ID"
            identifier = str(value)
        elif isinstance(value, str) and _DIGITS.fullmatch(value):
            identifier = value
        else:
            return None, "INVALID_ID"
    else:
        return None, "INVALID_ID"
    if len(identifier) > int(rules["policies"]["max_id_length"]):
        return None, "INVALID_ID"
    return identifier, None


def _normalize_amount_and_currency(record: dict[str, Any], definition: dict[str, Any], rules: dict[str, Any]) -> tuple[Decimal | None, str | None, str | None]:
    style = definition["amount_style"]
    raw_amount = record[definition["amount_field"]]
    if style == "major_units_decimal_point":
        amount = _parse_major_amount(raw_amount)
        if amount is None:
            return None, None, "INVALID_AMOUNT"
        currency = _parse_currency(record.get(definition["currency_field"]), rules)
        if currency is None:
            return None, None, "UNSUPPORTED_CURRENCY"
    elif style == "minor_units_integer":
        amount = _parse_minor_amount(raw_amount)
        if amount is None:
            return None, None, "INVALID_AMOUNT"
        currency = _parse_currency(record.get(definition["currency_field"]), rules)
        if currency is None:
            return None, None, "UNSUPPORTED_CURRENCY"
    elif style == "euro_symbol_decimal_comma":
        amount = _parse_euro_amount(raw_amount)
        if amount is None:
            return None, None, "INVALID_AMOUNT"
        currency = _currency_from_euro_rules(rules)
        if currency is None:
            return None, None, "UNSUPPORTED_CURRENCY"
        for optional_field in definition.get("optional_currency_fields_to_cross_check", []):
            if optional_field in record and _parse_currency(record[optional_field], rules) != currency:
                return None, None, "CURRENCY_MISMATCH"
    else:
        return None, None, "INVALID_AMOUNT"

    if amount <= 0 or amount > configured_max_amount(rules):
        return None, None, "INVALID_AMOUNT"
    return amount, currency, None


def _parse_major_amount(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        return None
    if isinstance(value, str) and _MAJOR_AMOUNT.fullmatch(value) is None:
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        return None
    return _two_decimals(amount)


def _parse_minor_amount(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        if value < 0:
            return None
        try:
            raw = str(value)
        except (ValueError, OverflowError):
            return None
    elif isinstance(value, str) and _DIGITS.fullmatch(value):
        raw = value
    else:
        return None
    try:
        amount = Decimal(raw) / Decimal(100)
    except (InvalidOperation, ValueError, TypeError, DivisionByZero):
        return None
    return _two_decimals(amount)


def _parse_euro_amount(value: Any) -> Decimal | None:
    if not isinstance(value, str) or _EURO_AMOUNT.fullmatch(value.strip()) is None:
        return None
    normalized = value.strip()[1:].replace(" ", "").replace(",", ".")
    try:
        return _two_decimals(Decimal(normalized))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _two_decimals(amount: Decimal) -> Decimal | None:
    if not amount.is_finite() or amount.as_tuple().exponent < -2:
        return None
    try:
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, OverflowError):
        return None


def _parse_currency(value: Any, rules: dict[str, Any]) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized if normalized in rules["currencies"] else None


def _currency_from_euro_rules(rules: dict[str, Any]) -> str | None:
    currencies = rules["currencies"]
    euro = currencies.get("EUR")
    if isinstance(euro, dict) and euro.get("symbol") == "€":
        return "EUR"
    return None


def _normalize_timestamp(value: Any, definition: dict[str, Any]) -> str | None:
    if not isinstance(value, str):
        return None
    if definition["timezone_required"]:
        try:
            candidate = value
            if candidate.endswith("Z"):
                candidate = candidate[:-1] + "+00:00"
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                return None
            utc_value = parsed.astimezone(timezone.utc)
            return utc_value.strftime("%Y-%m-%dT%H:%M:%SZ")
        except (TypeError, ValueError, OverflowError):
            return None

    for date_format in definition["date_formats"]:
        try:
            parsed = datetime.strptime(value, date_format)
        except (TypeError, ValueError, OverflowError):
            continue
        if parsed.strftime(date_format) != value:
            continue
        return parsed.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return None


def _amount_message(error_code: str) -> str:
    messages = {
        "INVALID_AMOUNT": "El importe no cumple el formato, precisión o límites permitidos.",
        "UNSUPPORTED_CURRENCY": "La moneda no está configurada como admitida.",
        "CURRENCY_MISMATCH": "La moneda declarada contradice el símbolo del importe.",
    }
    return messages.get(error_code, "El importe o la moneda no son válidos.")

