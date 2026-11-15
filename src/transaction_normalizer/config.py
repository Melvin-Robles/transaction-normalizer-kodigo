"""Carga y validación de la configuración externa de reglas."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .models import ConfigurationError


_REQUIRED_POLICIES = {
    "unknown_source",
    "invalid_record",
    "duplicate",
    "duplicate_key",
    "allow_extra_fields",
    "allow_negative_amounts",
    "allow_zero_amounts",
    "allow_implicit_currency",
    "exchange_rate_conversion",
    "naive_datetime_timezone",
    "output_timezone",
    "max_amount",
    "max_id_length",
    "max_file_bytes",
    "max_records",
}
_REQUIRED_SOURCE_FIELDS = {
    "discriminator",
    "required_fields",
    "id_field",
    "id_type",
    "amount_field",
    "amount_style",
    "currency_style",
    "timestamp_field",
    "date_formats",
    "timezone_required",
    "status_field",
    "status_map",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConfigurationError(message)


def load_rules(path: str | Path) -> dict[str, Any]:
    """Lee ``rules.json`` y valida su estructura esencial.

    La función no crea mapas de negocio alternativos: devuelve la configuración
    que después consumen las capas de normalización y de interfaz.
    """

    rules_path = Path(path)
    try:
        raw = rules_path.read_bytes()
        data = json.loads(raw.decode("utf-8-sig"))
    except FileNotFoundError as exc:
        raise ConfigurationError("No se encontró el archivo de reglas.") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ConfigurationError("El archivo de reglas no contiene JSON UTF-8 válido.") from exc

    _validate_rules(data)
    return data


def _validate_rules(rules: Any) -> None:
    """Valida tipos y campos necesarios sin imponer reglas fuera del contrato."""

    _require(isinstance(rules, dict), "La configuración debe ser un objeto JSON.")
    _require(isinstance(rules.get("policies"), dict), "Falta la sección policies.")
    policies = rules["policies"]
    missing = _REQUIRED_POLICIES - set(policies)
    _require(not missing, "Faltan políticas obligatorias en la configuración.")
    _require(isinstance(policies["max_id_length"], int) and not isinstance(policies["max_id_length"], bool), "max_id_length debe ser entero.")
    _require(isinstance(policies["max_file_bytes"], int) and policies["max_file_bytes"] > 0, "max_file_bytes debe ser positivo.")
    _require(isinstance(policies["max_records"], int) and policies["max_records"] > 0, "max_records debe ser positivo.")
    try:
        max_amount = Decimal(str(policies["max_amount"]))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ConfigurationError("max_amount debe ser un importe decimal.") from exc
    _require(max_amount.is_finite() and max_amount > 0, "max_amount debe ser positivo y finito.")

    currencies = rules.get("currencies")
    _require(isinstance(currencies, dict) and currencies, "Debe existir al menos una moneda configurada.")
    for code, definition in currencies.items():
        _require(isinstance(code, str) and code.strip(), "Los códigos de moneda deben ser textos no vacíos.")
        _require(isinstance(definition, dict), "Cada moneda debe tener una definición.")
        _require(definition.get("decimal_places") == 2, "La configuración exige dos decimales monetarios.")

    sources = rules.get("sources")
    _require(isinstance(sources, dict) and sources, "Debe existir al menos una fuente configurada.")
    discriminators: set[str] = set()
    for source, definition in sources.items():
        _require(isinstance(source, str) and source.strip(), "Cada fuente debe tener un nombre.")
        _require(isinstance(definition, dict), f"La fuente {source} no es un objeto.")
        missing_source = _REQUIRED_SOURCE_FIELDS - set(definition)
        _require(not missing_source, f"La fuente {source} no tiene todos sus campos de configuración.")
        discriminator = definition["discriminator"]
        _require(isinstance(discriminator, str) and discriminator, f"El discriminador de {source} no es válido.")
        _require(discriminator not in discriminators, "Los discriminadores de fuentes deben ser únicos.")
        discriminators.add(discriminator)
        _require(isinstance(definition["required_fields"], list), f"required_fields de {source} debe ser una lista.")
        _require(discriminator in definition["required_fields"], f"El discriminador de {source} debe ser obligatorio.")
        _require(isinstance(definition["status_map"], dict) and definition["status_map"], f"status_map de {source} no es válido.")
        _require(isinstance(definition["date_formats"], list) and definition["date_formats"], f"date_formats de {source} no es válido.")
        _require(isinstance(definition["timezone_required"], bool), f"timezone_required de {source} debe ser booleano.")

    _require(isinstance(rules.get("normalized_schema"), dict), "Falta normalized_schema.")
    _require(isinstance(rules.get("metrics"), dict), "Falta la sección metrics.")


def configured_max_amount(rules: dict[str, Any]) -> Decimal:
    """Devuelve el máximo monetario como ``Decimal``."""

    return Decimal(str(rules["policies"]["max_amount"]))

