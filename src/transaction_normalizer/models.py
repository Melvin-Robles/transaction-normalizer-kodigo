"""Modelos y errores públicos del dominio.

Las dataclasses representan el resultado interno tipado. Las interfaces
existentes siguen exponiendo diccionarios para conservar compatibilidad con la
UI y con consumidores de la versión anterior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


class NormalizerError(Exception):
    """Error base controlado del normalizador."""


class ConfigurationError(NormalizerError):
    """La configuración no existe o no cumple su contrato."""


class DocumentError(NormalizerError):
    """El documento JSON no puede procesarse de forma segura."""


@dataclass(frozen=True)
class NormalizedTransaction:
    """Transacción normalizada con el contrato de seis campos."""

    id: str
    amount: Decimal
    currency: str
    timestamp: str
    status: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        """Convierte el modelo al formato histórico consumido por la app."""

        return {
            "id": self.id,
            "amount": self.amount,
            "currency": self.currency,
            "timestamp": self.timestamp,
            "status": self.status,
            "source": self.source,
        }


@dataclass(frozen=True)
class Diagnostic:
    """Diagnóstico seguro de un registro rechazado."""

    index: int
    source: str | None
    error_code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convierte el diagnóstico al formato histórico de exportación."""

        return {
            "index": self.index,
            "source": self.source,
            "error_code": self.error_code,
            "message": self.message,
        }


@dataclass
class ProcessingResult:
    """Resultado separado por registros válidos e inválidos."""

    valid: list[dict[str, Any]] = field(default_factory=list)
    invalid: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BatchProcessingResult:
    """Resultado de aplicación: entrada, normalización y métricas."""

    records: list[Any]
    result: ProcessingResult
    metrics: dict[str, Any]

