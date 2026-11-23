"""Adaptador de la fuente A."""

from __future__ import annotations

from typing import Any

from .base import ConfiguredSourceAdapter


class SourceAAdapter(ConfiguredSourceAdapter):
    """Punto de extensión para el formato de la fuente A."""

    def __init__(self, definition: dict[str, Any]) -> None:
        super().__init__("A", definition)
