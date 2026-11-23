"""Caso de uso de aplicación para procesar documentos de transacciones."""

from __future__ import annotations

from typing import Any

from .ingest import parse_json_document
from .metrics import calculate_metrics
from .models import BatchProcessingResult
from .normalizer import normalize_records
from .sources.registry import SourceRegistry, build_source_registry


class TransactionProcessingService:
    """Coordina ingestión, normalización y métricas sin depender de Streamlit."""

    def __init__(self, rules: dict[str, Any]) -> None:
        self._rules = rules
        self._registry: SourceRegistry = build_source_registry(rules)

    def process_document(self, payload: bytes) -> BatchProcessingResult:
        """Procesa bytes JSON respetando los límites definidos en las reglas."""

        records = parse_json_document(payload, self._rules)
        return self.process_records(records)

    def process_records(self, records: list[Any]) -> BatchProcessingResult:
        """Normaliza registros ya leídos y calcula sus métricas."""

        record_list = list(records)
        result = normalize_records(record_list, self._rules, registry=self._registry)
        metrics = calculate_metrics(result.valid, result.invalid, total_processed=len(record_list))
        return BatchProcessingResult(records=record_list, result=result, metrics=metrics)
