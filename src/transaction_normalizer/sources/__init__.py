"""Adaptadores de las fuentes de transacciones."""

from .registry import SourceRegistry, build_source_registry

__all__ = ["SourceRegistry", "build_source_registry"]
