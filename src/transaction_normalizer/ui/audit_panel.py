"""Panel Streamlit para consultar el agente de auditoría existente."""

from __future__ import annotations

import importlib.util
import os
from typing import Any

import streamlit as st

from transaction_normalizer.agent import AuditAgent, AuditResponse, OpenAIResponsesProvider
from transaction_normalizer.agent.provider import ProviderConfigurationError, ProviderError
from transaction_normalizer.agent.tools import AuditToolset, ToolError
from transaction_normalizer.models import BatchProcessingResult

from .audit_state import ensure_audit_state


SUGGESTED_QUERIES = (
    "¿Cuál es la calidad general del lote?",
    "¿Cuáles son los errores más frecuentes?",
    "¿Qué fuentes presentan más problemas?",
    "¿Cuáles son los importes por moneda?",
    "¿Qué reglas están relacionadas con los errores detectados?",
    "¿Qué recomendaciones de calidad puedes ofrecer?",
)


def ai_provider_availability() -> dict[str, bool]:
    """Comprueba disponibilidad sin revelar valores de configuración."""

    try:
        dependency = importlib.util.find_spec("openai") is not None
    except (ImportError, ValueError):
        dependency = False
    return {
        "dependency": dependency,
        "api_key": bool(os.getenv("OPENAI_API_KEY")),
        "model": bool(os.getenv("OPENAI_AUDIT_AGENT_MODEL")),
    }


def render_audit_panel(
    batch: BatchProcessingResult | None,
    rules: dict[str, Any],
    batch_key: str | None = None,
) -> None:
    """Renderiza métricas y consultas sin duplicar cálculos del dominio."""

    st.subheader("Auditoría inteligente de transacciones")
    if batch is None:
        st.info("Procesa un lote para habilitar la auditoría local y sus métricas.")
        return

    if batch_key is None:
        # La aplicación pasa una huella del payload. Este fallback solo sirve
        # para consumidores de la función fuera de app.py.
        batch_key = f"batch-{id(batch)}"
    state = ensure_audit_state(st.session_state, batch_key)

    try:
        toolset = AuditToolset(batch, rules)
        metrics = toolset.invoke("query_batch_metrics")
        errors = toolset.invoke("query_error_distribution")
        sources = toolset.invoke("query_source_statistics")
        currencies = toolset.invoke("query_currency_totals")
    except ToolError as exc:
        st.error(f"No se pudo construir el resumen de auditoría: {exc}")
        return

    st.caption("Lote activo: " + (batch_key[:12] if batch_key else "desconocido"))
    _render_metrics(metrics)
    _render_distributions(errors, sources, currencies)
    st.divider()
    _render_local_query(batch, rules, state)
    _render_ai_query(batch, rules, state)


def _render_metrics(metrics: dict[str, Any]) -> None:
    """Muestra conteos calculados por la herramienta de métricas."""

    columns = st.columns(4)
    columns[0].metric("Procesados", f"{metrics['total_processed']:,}")
    columns[1].metric("Válidos", f"{metrics['valid_count']:,}")
    columns[2].metric("Inválidos", f"{metrics['invalid_count']:,}")
    columns[3].metric("Calidad", f"{metrics['quality_percent']:.2f}%")


def _render_distributions(
    errors: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    currencies: dict[str, Any],
) -> None:
    """Muestra distribuciones agregadas, manteniendo las monedas separadas."""

    error_rows = [
        {"Código": code, "Cantidad": count}
        for code, count in errors["by_code"].items()
    ]
    source_rows = [
        {
            "Fuente": source,
            "Procesados": values["processed"],
            "Válidos": values["valid"],
            "Inválidos": values["invalid"],
            "Calidad": f"{values['quality_percent']:.2f}%",
        }
        for source, values in sources.items()
    ]
    currency_rows = [
        {
            "Moneda": currency,
            "Válidos": currencies["valid_count_by_currency"].get(currency, 0),
            "Total válidos": currencies["all_valid_totals_by_currency"].get(currency, "0.00"),
            "Total SUCCESS": currencies["success_totals_by_currency"].get(currency, "0.00"),
        }
        for currency in sorted(currencies["all_valid_totals_by_currency"])
    ]

    error_column, source_column = st.columns(2, gap="large")
    with error_column:
        st.caption("Errores por categoría")
        if error_rows:
            st.dataframe(error_rows, use_container_width=True, hide_index=True)
        else:
            st.success("No hay errores en este lote.")
    with source_column:
        st.caption("Distribución por fuente")
        if source_rows:
            st.dataframe(source_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No hay fuentes para mostrar.")

    st.caption("Totales monetarios separados")
    if currency_rows:
        st.dataframe(currency_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No hay importes válidos para resumir.")


def _render_local_query(
    batch: BatchProcessingResult,
    rules: dict[str, Any],
    state: dict[str, Any],
) -> None:
    """Ejecuta siempre la ruta local, determinista y sin proveedor externo."""

    st.markdown("#### Auditoría local basada en reglas")
    st.caption("Resultados reproducibles mediante herramientas Python de solo lectura.")
    selected = st.selectbox(
        "Pregunta sugerida",
        SUGGESTED_QUERIES,
        key="audit_suggested_query",
    )
    custom = st.text_input(
        "Consulta personalizada",
        key="audit_custom_query",
        placeholder="Escribe una pregunta sobre el lote actual",
    ).strip()
    query = custom or selected
    if st.button("Ejecutar auditoría local", key="run_local_audit", type="primary"):
        try:
            response = AuditAgent(batch, rules).audit(query)
        except Exception as exc:
            st.error(f"No se pudo completar la auditoría local: {exc}")
        else:
            state["deterministic_response"] = response
            state["ai_response"] = None

    response = state.get("deterministic_response")
    if isinstance(response, AuditResponse) and response.query == query:
        _render_response(response, "Resultado de auditoría local")
    elif response is not None:
        st.info("La consulta cambió. Ejecuta de nuevo la auditoría para actualizar el resultado.")


def _render_ai_query(
    batch: BatchProcessingResult,
    rules: dict[str, Any],
    state: dict[str, Any],
) -> None:
    """Expone IA solo tras habilitación, disponibilidad y consentimiento."""

    st.markdown("#### Auditoría asistida por IA")
    st.caption("Opcional: puede transmitir contexto agregado al proveedor configurado.")
    enabled = st.checkbox(
        "Habilitar auditoría asistida por IA",
        key="audit_ai_enabled",
    )
    availability = ai_provider_availability()
    ready = all(availability.values())

    if not enabled:
        st.info("Modo IA deshabilitado. La auditoría local sigue disponible.")
        return
    if not ready:
        st.warning(
            "Modo IA no disponible: faltan dependencia, credencial o modelo. "
            "La aplicación mantiene la auditoría local sin realizar conexiones."
        )
        return

    response = state.get("deterministic_response")
    if not isinstance(response, AuditResponse):
        st.info("Ejecuta primero una auditoría local para generar el contexto agregado.")
        return

    with st.expander("Vista previa del contexto agregado", expanded=True):
        st.json(response.tool_results, expanded=False)
        st.caption("No se incluyen registros originales completos ni contenido del archivo JSON.")
    st.warning(
        "El proveedor podría recibir las métricas y diagnósticos agregados mostrados arriba. "
        "Revisa la vista previa antes de continuar."
    )
    confirmed = st.checkbox(
        "Confirmo que autorizo enviar este contexto agregado al proveedor configurado.",
        key="audit_privacy_confirm",
    )
    if st.button("Ejecutar auditoría con IA", key="run_ai_audit", disabled=not confirmed):
        try:
            provider = OpenAIResponsesProvider()
            ai_response = AuditAgent(batch, rules, provider=provider).audit(response.query)
        except (ProviderConfigurationError, ProviderError) as exc:
            st.error(f"El proveedor no está disponible: {exc}")
        except Exception:
            st.error("La auditoría con IA no pudo completarse. La auditoría local permanece disponible.")
        else:
            state["ai_response"] = ai_response

    ai_response = state.get("ai_response")
    if isinstance(ai_response, AuditResponse):
        _render_response(ai_response, "Resultado de auditoría asistida por IA")


def _render_response(response: AuditResponse, title: str) -> None:
    """Renderiza una respuesta segura y sus metadatos trazables."""

    st.caption(title)
    if response.generated_by_model:
        st.warning("Respuesta generada por un proveedor configurado; valida sus recomendaciones.")
    elif response.provider_status == "error":
        st.info("El proveedor falló y se conserva el resumen determinista verificable.")
    else:
        st.success("Respuesta determinista basada en datos agregados del lote.")
    st.text(response.summary)

    with st.expander("Detalles de la auditoría", expanded=False):
        mode = "Auditoría asistida por IA" if response.generated_by_model else "Auditoría local basada en reglas"
        st.write({
            "modo": mode,
            "estado_proveedor": response.provider_status,
            "herramientas_utilizadas": list(response.selected_tools),
            "iteraciones": response.iterations,
            "finalizada": True,
            "errores_controlados": list(response.warnings),
        })
