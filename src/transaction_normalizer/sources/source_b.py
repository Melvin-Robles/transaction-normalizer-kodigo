"""Adaptador de la fuente B."""

from __future__ import annotations

from typing import Any

from .base import ConfiguredSourceAdapter


class SourceBAdapter(ConfiguredSourceAdapter):
    """Punto de extensión para el formato de la fuente B."""

    def __init__(self, definition: dict[str, Any]) -> None:
        super().__init__("B", definition)
