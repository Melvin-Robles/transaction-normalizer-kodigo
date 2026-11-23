"""Validaciones compartidas por los adaptadores de fuentes."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, DivisionByZero, InvalidOperation
from typing import Any

from .config import configured_max_amount
from .models import Diagnostic


_DIGITS = re.compile(r"^\d+$")
_MAJOR_AMOUNT = re.compile(r"^\d+(?:\.\d{1,2})?$")
_EURO_AMOUNT = re.compile(r"^€\s*\d+(?:,\d{1,2})?$")
SUPPORTED_AMOUNT_STYLES = frozenset(
    {
        "major_units_decimal_point",
        "minor_units_integer",
        "euro_symbol_decimal_comma",
    }
)


def diagnostic(index: int, source: str | None, code: str, message: str) -> Diagnostic:
    """Construye un diagnóstico sin conservar la carga original."""

    return Diagnostic(index=index, source=source, error_code=code, message=message)


def source_label(value: Any) -> str | None:
    """Normaliza la etiqueta opcional de fuente."""

    return value.strip().upper() if isinstance(value, str) else None


def normalize_id(value: Any, id_type: str, rules: dict[str, Any]) -> tuple[str | None, str | None]:
    """Valida y convierte un identificador a texto."""

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


def normalize_amount_and_currency(
    record: dict[str, Any], definition: dict[str, Any], rules: dict[str, Any]
) -> tuple[Decimal | None, str | None, str | None]:
    """Normaliza importe y moneda según el estilo declarado en las reglas."""

    style = definition["amount_style"]
    raw_amount = record[definition["amount_field"]]
    if style == "major_units_decimal_point":
        amount = parse_major_amount(raw_amount)
        if amount is None:
            return None, None, "INVALID_AMOUNT"
        currency = parse_currency(record.get(definition["currency_field"]), rules)
        if currency is None:
            return None, None, "UNSUPPORTED_CURRENCY"
    elif style == "minor_units_integer":
        amount = parse_minor_amount(raw_amount)
        if amount is None:
            return None, None, "INVALID_AMOUNT"
        currency = parse_currency(record.get(definition["currency_field"]), rules)
        if currency is None:
            return None, None, "UNSUPPORTED_CURRENCY"
    elif style == "euro_symbol_decimal_comma":
        amount = parse_euro_amount(raw_amount)
        if amount is None:
            return None, None, "INVALID_AMOUNT"
        currency = currency_from_euro_rules(rules)
        if currency is None:
            return None, None, "UNSUPPORTED_CURRENCY"
        for optional_field in definition.get("optional_currency_fields_to_cross_check", []):
            if optional_field in record and parse_currency(record[optional_field], rules) != currency:
                return None, None, "CURRENCY_MISMATCH"
    else:
        return None, None, "INVALID_AMOUNT"

    if amount <= 0 or amount > configured_max_amount(rules):
        return None, None, "INVALID_AMOUNT"
    return amount, currency, None


def parse_major_amount(value: Any) -> Decimal | None:
    """Parsea unidades principales con punto y hasta dos decimales."""

    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        return None
    if isinstance(value, str) and _MAJOR_AMOUNT.fullmatch(value) is None:
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        return None
    return two_decimals(amount)


def parse_minor_amount(value: Any) -> Decimal | None:
    """Parsea unidades menores enteras y las convierte a unidades principales."""

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
    return two_decimals(amount)


def parse_euro_amount(value: Any) -> Decimal | None:
    """Parsea el formato de la fuente C, por ejemplo ``€99,99``."""

    if not isinstance(value, str) or _EURO_AMOUNT.fullmatch(value.strip()) is None:
        return None
    normalized = value.strip()[1:].replace(" ", "").replace(",", ".")
    try:
        return two_decimals(Decimal(normalized))
    except (InvalidOperation, ValueError, TypeError):
        return None


def two_decimals(amount: Decimal) -> Decimal | None:
    """Rechaza valores no finitos o con más de dos decimales."""

    if not amount.is_finite() or amount.as_tuple().exponent < -2:
        return None
    try:
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, OverflowError):
        return None


def parse_currency(value: Any, rules: dict[str, Any]) -> str | None:
    """Normaliza un código de moneda y verifica que esté configurado."""

    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized if normalized in rules["currencies"] else None


def currency_from_euro_rules(rules: dict[str, Any]) -> str | None:
    """Obtiene la moneda asociada al símbolo euro configurado."""

    euro = rules["currencies"].get("EUR")
    if isinstance(euro, dict) and euro.get("symbol") == "€":
        return "EUR"
    return None


def normalize_timestamp(value: Any, definition: dict[str, Any]) -> str | None:
    """Convierte fechas configuradas a la representación UTC histórica."""

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


def normalize_status(value: Any, definition: dict[str, Any]) -> str | None:
    """Aplica el mapa de estados de la fuente sin codificarlo en Python."""

    if not isinstance(value, str):
        return None
    status_map = {str(key).strip().casefold(): mapped for key, mapped in definition["status_map"].items()}
    return status_map.get(value.strip().casefold())


def amount_message(error_code: str) -> str:
    """Devuelve el mensaje público compatible con la versión anterior."""

    messages = {
        "INVALID_AMOUNT": "El importe no cumple el formato, precisión o límites permitidos.",
        "UNSUPPORTED_CURRENCY": "La moneda no está configurada como admitida.",
        "CURRENCY_MISMATCH": "La moneda declarada contradice el símbolo del importe.",
    }
    return messages.get(error_code, "El importe o la moneda no son válidos.")
