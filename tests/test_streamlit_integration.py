"""Pruebas de integración de la auditoría con la interfaz Streamlit."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from transaction_normalizer.ui.audit_panel import ai_provider_availability
from transaction_normalizer.ui.audit_state import AUDIT_STATE_KEY, ensure_audit_state


ROOT = Path(__file__).resolve().parents[1]


class StreamlitIntegrationTests(unittest.TestCase):
    def test_app_starts_with_local_audit_and_no_provider_call(self) -> None:
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertIn("Auditoría inteligente de transacciones", [item.value for item in app.subheader])
        self.assertTrue(any("Modo IA deshabilitado" in item.value for item in app.info))
        self.assertNotIn("run_ai_audit", [item.key for item in app.button])

    def test_local_query_uses_current_batch_and_aggregated_response(self) -> None:
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        app.button(key="run_local_audit").click().run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Respuesta determinista" in item.value for item in app.success))
        rendered = " ".join(item.value for item in app.text)
        self.assertIn("3 procesado(s)", rendered)
        self.assertNotIn("tx_001", rendered)

    def test_custom_currency_query_uses_real_agent_tools(self) -> None:
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        app.text_input(key="audit_custom_query").set_value(
            "¿Cuáles son los importes por moneda?"
        ).run(timeout=30)
        app.button(key="run_local_audit").click().run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        rendered = " ".join(item.value for item in app.text)
        self.assertIn("EUR", rendered)
        self.assertIn("99.99", rendered)
        self.assertIn("201.00", rendered)

    def test_mixed_batch_upload_renders_current_metrics(self) -> None:
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        app.button(key="use_upload_button").click().run(timeout=30)
        app.file_uploader[0].upload(
            "transacciones_mixtas.json",
            (ROOT / "data" / "pruebas_ui" / "transacciones_mixtas.json").read_bytes(),
            "application/json",
        ).run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        metric_values = {(item.label, item.value) for item in app.metric}
        self.assertIn(("Procesadas", "9"), metric_values)
        self.assertIn(("Inválidas", "6"), metric_values)
        self.assertIn(("Calidad", "33.33%"), metric_values)

    def test_upload_mode_without_file_shows_empty_audit_state(self) -> None:
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        app.button(key="use_upload_button").click().run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Procesa un lote" in item.value for item in app.info))

    def test_context_resets_when_batch_key_changes(self) -> None:
        state: dict[str, object] = {}
        first = ensure_audit_state(state, "first")
        first["deterministic_response"] = "response"

        second = ensure_audit_state(state, "second")

        self.assertEqual(state[AUDIT_STATE_KEY], second)
        self.assertEqual(second["batch_key"], "second")
        self.assertIsNone(second["deterministic_response"])

    def test_provider_availability_does_not_expose_secret_values(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch(
            "transaction_normalizer.ui.audit_panel.importlib.util.find_spec",
            return_value=None,
        ):
            availability = ai_provider_availability()

        self.assertEqual(availability, {"dependency": False, "api_key": False, "model": False})
        self.assertNotIn("OPENAI_API_KEY", repr(availability))


if __name__ == "__main__":
    unittest.main()
