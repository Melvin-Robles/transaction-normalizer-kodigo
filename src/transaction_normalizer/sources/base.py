"""Contrato y comportamiento compartido de adaptadores de fuentes."""

from __future__ import annotations

from typing import Any

from ..models import Diagnostic, NormalizedTransaction
from ..validation import (
    amount_message,
    diagnostic,
    normalize_amount_and_currency,
    normalize_id,
    normalize_status,
    normalize_timestamp,
    source_label,
)


class ConfiguredSourceAdapter:
    """Adapta una fuente configurada sin duplicar validaciones comunes."""

    def __init__(self, source_name: str, definition: dict[str, Any]) -> None:
        self.source_name = source_name
        self.definition = definition

    @property
    def discriminator(self) -> str:
        """Campo que identifica la fuente."""

        return self.definition["discriminator"]

    def normalize(
        self,
        record: dict[str, Any],
        index: int,
        rules: dict[str, Any],
        seen: set[tuple[str, str]],
    ) -> tuple[NormalizedTransaction | None, Diagnostic | None]:
        """Valida y transforma una fila ya identificada como esta fuente."""

        definition = self.definition
        if "source" in record and source_label(record["source"]) != self.source_name:
            return None, diagnostic(
                index,
                self.source_name,
                "SOURCE_CONFLICT",
                "El campo source contradice la fuente detectada.",
            )

        for field in definition["required_fields"]:
            if field not in record:
                return None, diagnostic(
                    index,
                    self.source_name,
                    "MISSING_FIELD",
                    "Falta un campo obligatorio del registro.",
                )

        identifier, error_code = normalize_id(record[definition["id_field"]], definition["id_type"], rules)
        if error_code:
            return None, diagnostic(
                index,
                self.source_name,
                "INVALID_ID",
                "El identificador no cumple el formato permitido.",
            )

        amount, currency, amount_error = normalize_amount_and_currency(record, definition, rules)
        if amount_error:
            return None, diagnostic(index, self.source_name, amount_error, amount_message(amount_error))

        timestamp = normalize_timestamp(record[definition["timestamp_field"]], definition)
        if timestamp is None:
            return None, diagnostic(
                index,
                self.source_name,
                "INVALID_TIMESTAMP",
                "La fecha no cumple el formato requerido.",
            )

        status = normalize_status(record[definition["status_field"]], definition)
        if status is None:
            return None, diagnostic(
                index,
                self.source_name,
                "UNKNOWN_STATUS",
                "El estado no está configurado para esta fuente.",
            )

        key = (self.source_name, identifier)
        if key in seen:
            return None, diagnostic(
                index,
                self.source_name,
                "DUPLICATE_TRANSACTION",
                "Ya existe una transacción válida con la misma fuente e identificador.",
            )

        return NormalizedTransaction(
            id=identifier,
            amount=amount,
            currency=currency,
            timestamp=timestamp,
            status=status,
            source=self.source_name,
        ), None
