"""Pruebas de los límites nuevos introducidos durante la refactorización."""

from __future__ import annotations

import json
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from transaction_normalizer.config import load_rules
from transaction_normalizer.filters import filter_valid_records
from transaction_normalizer.models import NormalizedTransaction
from transaction_normalizer.service import TransactionProcessingService
from transaction_normalizer.sources.registry import build_source_registry


ROOT = Path(__file__).resolve().parents[1]


class RefactoredComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_rules(ROOT / "config" / "rules.json")
        cls.payload = (ROOT / "data" / "transacciones_ejemplo.json").read_bytes()

    def test_service_coordinates_document_processing_without_streamlit(self) -> None:
        service = TransactionProcessingService(self.rules)

        batch = service.process_document(self.payload)

        self.assertEqual(len(batch.records), 3)
        self.assertEqual(len(batch.result.valid), 3)
        self.assertEqual(batch.result.invalid, [])
        self.assertEqual(batch.metrics["all_valid_totals_by_currency"]["USD"], Decimal("201.00"))
        self.assertEqual(batch.metrics["all_valid_totals_by_currency"]["EUR"], Decimal("99.99"))

    def test_registry_uses_independent_source_adapters_and_typed_internal_model(self) -> None:
        registry = build_source_registry(self.rules)
        record = json.loads(self.payload.decode("utf-8"))[0]

        matches = registry.matching(record)
        normalized, error = matches[0].normalize(record, 0, self.rules, set())

        self.assertEqual([adapter.source_name for adapter in matches], ["A"])
        self.assertIsNone(error)
        self.assertIsInstance(normalized, NormalizedTransaction)
        self.assertEqual(normalized.amount, Decimal("100.50"))

    def test_filter_service_preserves_intersection_and_order(self) -> None:
        service = TransactionProcessingService(self.rules)
        valid = service.process_document(self.payload).result.valid

        filtered = filter_valid_records(
            valid,
            currency="USD",
            source="B",
            query="04",
            date_range=(date(2025, 3, 10), date(2025, 3, 10)),
            sort_by="Importe",
            descending=True,
        )

        self.assertEqual([row["id"] for row in filtered], ["204"])


if __name__ == "__main__":
    unittest.main()
