"""Modelos y errores públicos del dominio."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class NormalizerError(Exception):
    """Error base controlado del normalizador."""


class ConfigurationError(NormalizerError):
    """La configuración no existe o no cumple su contrato."""


class DocumentError(NormalizerError):
    """El documento JSON no puede procesarse de forma segura."""


@dataclass
class ProcessingResult:
    """Resultado separado por registros válidos e inválidos."""

    valid: list[dict[str, Any]] = field(default_factory=list)
    invalid: list[dict[str, Any]] = field(default_factory=list)

