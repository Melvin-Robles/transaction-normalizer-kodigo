"""Pruebas de caracterización del comportamiento existente.

Estas pruebas fijan los contratos observables antes de iniciar la
refactorización. No dependen de Streamlit ni de servicios externos.
"""

from __future__ import annotations

import copy
import json
import unittest
from decimal import Decimal
from pathlib import Path

from transaction_normalizer.config import load_rules
from transaction_normalizer.exports import (
    serialize_errors_json,
    serialize_normalized_json,
)
from transaction_normalizer.ingest import parse_json_document
from transaction_normalizer.metrics import calculate_metrics
from transaction_normalizer.models import DocumentError
from transaction_normalizer.normalizer import normalize_records


ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "config" / "rules.json"
EXAMPLE_PATH = ROOT / "data" / "transacciones_ejemplo.json"
FIXTURES_PATH = ROOT / "data" / "pruebas_ui"


class TransactionNormalizerCharacterizationTests(unittest.TestCase):
    """Documenta el comportamiento observable que debe sobrevivir al cambio."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_rules(RULES_PATH)

    def parse_and_normalize(self, payload: bytes):
        records = parse_json_document(payload, self.rules)
        return records, normalize_records(records, self.rules)

    def test_integrated_example_contract(self) -> None:
        records, result = self.parse_and_normalize(EXAMPLE_PATH.read_bytes())

        self.assertEqual(len(records), 3)
        self.assertEqual(len(result.valid), 3)
        self.assertEqual(result.invalid, [])
        self.assertEqual([row["id"] for row in result.valid], ["tx_001", "204", "A-77"])
        self.assertEqual(
            [row["amount"] for row in result.valid],
            [Decimal("100.50"), Decimal("100.50"), Decimal("99.99")],
        )
        self.assertEqual([row["currency"] for row in result.valid], ["USD", "USD", "EUR"])
        self.assertEqual({row["status"] for row in result.valid}, {"SUCCESS"})
        self.assertEqual(
            {row["timestamp"] for row in result.valid},
            {"2025-03-10T14:22:00Z"},
        )

    def test_integrated_example_metrics_do_not_mix_currencies(self) -> None:
        _, result = self.parse_and_normalize(EXAMPLE_PATH.read_bytes())
        metrics = calculate_metrics(result.valid, result.invalid, total_processed=3)

        self.assertEqual(metrics["total_processed"], 3)
        self.assertEqual(metrics["valid_count"], 3)
        self.assertEqual(metrics["invalid_count"], 0)
        self.assertEqual(
            metrics["all_valid_totals_by_currency"],
            {"USD": Decimal("201.00"), "EUR": Decimal("99.99")},
        )
        self.assertEqual(metrics["success_totals_by_currency"], metrics["all_valid_totals_by_currency"])

    def test_supported_document_shapes_and_empty_array(self) -> None:
        wrapped = FIXTURES_PATH / "transacciones_envueltas.json"
        empty = FIXTURES_PATH / "transacciones_vacias.json"

        wrapped_records, wrapped_result = self.parse_and_normalize(wrapped.read_bytes())
        empty_records, empty_result = self.parse_and_normalize(empty.read_bytes())

        self.assertEqual(len(wrapped_records), 2)
        self.assertEqual(len(wrapped_result.valid), 2)
        self.assertEqual(len(empty_records), 0)
        self.assertEqual(empty_result.valid, [])
        self.assertEqual(empty_result.invalid, [])

    def test_mixed_fixture_continues_after_invalid_records(self) -> None:
        records, result = self.parse_and_normalize(
            (FIXTURES_PATH / "transacciones_mixtas.json").read_bytes()
        )

        self.assertEqual(len(records), 9)
        self.assertEqual(len(result.valid), 3)
        self.assertEqual(len(result.invalid), 6)
        self.assertEqual(
            [error["error_code"] for error in result.invalid],
            [
                "MISSING_FIELD",
                "INVALID_AMOUNT",
                "CURRENCY_MISMATCH",
                "DUPLICATE_TRANSACTION",
                "INVALID_RECORD_TYPE",
                "UNKNOWN_SOURCE",
            ],
        )

    def test_malformed_json_and_invalid_root_are_controlled_errors(self) -> None:
        malformed = (FIXTURES_PATH / "transacciones_malformadas.json").read_bytes()

        with self.assertRaises(DocumentError):
            parse_json_document(malformed, self.rules)
        with self.assertRaises(DocumentError):
            parse_json_document(b'{"items": []}', self.rules)
        with self.assertRaises(DocumentError):
            parse_json_document(b"", self.rules)

    def test_source_specific_formats_and_timestamp_normalization(self) -> None:
        records = [
            {
                "id": "a-1",
                "amount": 1.25,
                "currency": " usd ",
                "timestamp": "2025-03-10 14:22:00",
                "status": " COMPLETED ",
            },
            {
                "transaction_id": 204,
                "total": 10050,
                "currency_code": "USD",
                "created_at": "10/03/2025 14:22",
                "state": "ok",
            },
            {
                "ref": "c-1",
                "amount": "€99,99",
                "date": "2025-03-10T16:22:00+02:00",
                "result": "success",
            },
        ]

        result = normalize_records(records, self.rules)

        self.assertEqual(len(result.valid), 3)
        self.assertEqual(result.valid[0]["amount"], Decimal("1.25"))
        self.assertEqual(result.valid[1]["amount"], Decimal("100.50"))
        self.assertEqual(result.valid[2]["amount"], Decimal("99.99"))
        self.assertTrue(all(row["timestamp"] == "2025-03-10T14:22:00Z" for row in result.valid))

    def test_invalid_records_are_diagnosed_and_processing_continues(self) -> None:
        records = [
            None,
            {"id": "missing-amount", "currency": "USD", "timestamp": "2025-03-10 14:22:00", "status": "completed"},
            {
                "id": "valid-after-error",
                "amount": 10,
                "currency": "USD",
                "timestamp": "2025-03-10 14:22:00",
                "status": "completed",
            },
        ]

        result = normalize_records(records, self.rules)

        self.assertEqual(len(result.valid), 1)
        self.assertEqual(result.valid[0]["id"], "valid-after-error")
        self.assertEqual(
            [error["error_code"] for error in result.invalid],
            ["INVALID_RECORD_TYPE", "MISSING_FIELD"],
        )

    def test_duplicates_are_per_source_and_first_valid_occurrence_wins(self) -> None:
        a = {
            "id": "204",
            "amount": 10,
            "currency": "USD",
            "timestamp": "2025-03-10 14:22:00",
            "status": "completed",
        }
        b = {
            "transaction_id": 204,
            "total": 1000,
            "currency_code": "USD",
            "created_at": "10/03/2025 14:22",
            "state": "ok",
        }

        result = normalize_records([a, dict(a), b, dict(b)], self.rules)

        self.assertEqual([(row["source"], row["id"]) for row in result.valid], [("A", "204"), ("B", "204")])
        self.assertEqual([error["error_code"] for error in result.invalid], ["DUPLICATE_TRANSACTION", "DUPLICATE_TRANSACTION"])

    def test_rules_drive_status_mapping_without_python_constant(self) -> None:
        rules = copy.deepcopy(self.rules)
        rules["sources"]["A"]["status_map"]["completed"] = "PENDING"
        record = {
            "id": "configured-status",
            "amount": 10,
            "currency": "USD",
            "timestamp": "2025-03-10 14:22:00",
            "status": "completed",
        }

        result = normalize_records([record], rules)

        self.assertEqual(result.invalid, [])
        self.assertEqual(result.valid[0]["status"], "PENDING")

    def test_exports_preserve_contract_and_do_not_expose_raw_invalid_record(self) -> None:
        _, result = self.parse_and_normalize(EXAMPLE_PATH.read_bytes())
        normalized = json.loads(serialize_normalized_json(result.valid))
        errors = [{"index": 0, "source": "A", "error_code": "INVALID_AMOUNT", "message": "safe"}]
        exported_errors = json.loads(serialize_errors_json(errors))

        self.assertEqual(
            list(normalized[0]),
            ["id", "amount", "currency", "timestamp", "status", "source"],
        )
        self.assertIsInstance(normalized[0]["amount"], (int, float))
        self.assertEqual(exported_errors, errors)
        self.assertNotIn("record", exported_errors[0])


if __name__ == "__main__":
    unittest.main()
