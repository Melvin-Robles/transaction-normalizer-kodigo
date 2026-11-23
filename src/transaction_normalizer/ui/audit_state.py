"""Estado de sesión mínimo para la auditoría de un lote concreto."""

from __future__ import annotations

from typing import Any, MutableMapping


AUDIT_STATE_KEY = "transaction_audit_state"


def ensure_audit_state(
    session_state: MutableMapping[str, Any],
    batch_key: str,
) -> dict[str, Any]:
    """Inicializa o reinicia el contexto cuando cambia el lote procesado.

    Solo conserva la respuesta agregada del agente y metadatos de la UI. No
    almacena una copia de los registros originales ni usa cachés globales.
    """

    current = session_state.get(AUDIT_STATE_KEY)
    if not isinstance(current, dict) or current.get("batch_key") != batch_key:
        current = {
            "batch_key": batch_key,
            "deterministic_response": None,
            "ai_response": None,
        }
        session_state[AUDIT_STATE_KEY] = current
    return current
