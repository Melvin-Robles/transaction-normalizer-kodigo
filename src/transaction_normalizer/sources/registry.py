"""Registro y detección de adaptadores de fuentes."""

from __future__ import annotations

from typing import Any, TypeAlias

from ..models import Diagnostic, NormalizedTransaction
from ..validation import diagnostic
from .base import ConfiguredSourceAdapter
from .source_a import SourceAAdapter
from .source_b import SourceBAdapter
from .source_c import SourceCAdapter


Adapter: TypeAlias = ConfiguredSourceAdapter
AdapterFactory: TypeAlias = type[ConfiguredSourceAdapter]

_KNOWN_ADAPTERS: dict[str, AdapterFactory] = {
    "A": SourceAAdapter,
    "B": SourceBAdapter,
    "C": SourceCAdapter,
}


class SourceRegistry:
    """Colección de adaptadores indexada por fuente y discriminador."""

    def __init__(self, adapters: dict[str, Adapter]) -> None:
        self._adapters = dict(adapters)

    def matching(self, record: dict[str, Any]) -> list[Adapter]:
        """Devuelve los adaptadores cuyos discriminadores aparecen en la fila."""

        return [adapter for adapter in self._adapters.values() if adapter.discriminator in record]

    def normalize(
        self,
        record: Any,
        index: int,
        rules: dict[str, Any],
        seen: set[tuple[str, str]],
    ) -> tuple[NormalizedTransaction | None, Diagnostic | None]:
        """Detecta la fuente y delega la validación al adaptador correspondiente."""

        if not isinstance(record, dict):
            return None, diagnostic(
                index,
                None,
                "INVALID_RECORD_TYPE",
                "El registro debe ser un objeto JSON.",
            )

        matching = self.matching(record)
        if len(matching) == 0:
            return None, diagnostic(index, None, "UNKNOWN_SOURCE", "No se identificó una fuente conocida.")
        if len(matching) > 1:
            return None, diagnostic(
                index,
                None,
                "AMBIGUOUS_SOURCE",
                "El registro contiene varios discriminadores de fuente.",
            )
        return matching[0].normalize(record, index, rules, seen)


def build_source_registry(rules: dict[str, Any]) -> SourceRegistry:
    """Construye el registro desde las fuentes activas de la configuración."""

    adapters: dict[str, Adapter] = {}
    for source_name, definition in rules["sources"].items():
        factory = _KNOWN_ADAPTERS.get(source_name)
        if factory is None:
            adapters[source_name] = ConfiguredSourceAdapter(source_name, definition)
        else:
            adapters[source_name] = factory(definition)
    return SourceRegistry(adapters)
