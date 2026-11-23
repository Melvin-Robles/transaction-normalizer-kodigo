"""Adaptador de la fuente C."""

from __future__ import annotations

from typing import Any

from .base import ConfiguredSourceAdapter


class SourceCAdapter(ConfiguredSourceAdapter):
    """Punto de extensión para el formato de la fuente C."""

    def __init__(self, definition: dict[str, Any]) -> None:
        super().__init__("C", definition)
