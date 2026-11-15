"""Interfaz Streamlit del normalizador; la lógica de dominio vive en ``src``."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import streamlit as st

from transaction_normalizer.config import load_rules
from transaction_normalizer.exports import serialize_errors_json, serialize_normalized_json
from transaction_normalizer.ingest import parse_json_document
from transaction_normalizer.metrics import calculate_metrics
from transaction_normalizer.models import ConfigurationError, DocumentError
from transaction_normalizer.normalizer import normalize_records


ROOT = Path(__file__).resolve().parent
RULES_PATH = ROOT / "config" / "rules.json"
DEFAULT_DATA_PATH = ROOT / "data" / "transacciones_ejemplo.json"


def main() -> None:
    st.set_page_config(page_title="Normalizador de transacciones", page_icon="↔", layout="wide")
    st.title("Normalizador de transacciones")
    st.caption("Importa JSON heterogéneo, valida por fuente y separa diagnósticos sin detener el lote.")
    st.info("Esquema de salida: id, amount, currency, timestamp, status y source. Las fuentes A, B y C se detectan por sus claves discriminadoras.")

    try:
        rules = load_rules(RULES_PATH)
    except ConfigurationError as exc:
        st.error(str(exc))
        st.info("Corrija config/rules.json y vuelva a cargar la página.")
        return

    mode = st.radio("Origen de datos", ["Datos de ejemplo", "Cargar archivo JSON"], horizontal=True)
    payload: bytes
    label: str
    if mode == "Datos de ejemplo":
        try:
            payload = DEFAULT_DATA_PATH.read_bytes()
        except OSError:
            st.error("No se encontró el archivo de ejemplo en data/transacciones_ejemplo.json.")
            return
        label = "transacciones_ejemplo.json"
    else:
        upload = st.file_uploader("Seleccione un archivo JSON (máximo 5 MiB)", type=["json"])
        if upload is None:
            st.warning("Seleccione un archivo para comenzar.")
            return
        payload = upload.getvalue()
        label = upload.name or "archivo cargado"

    try:
        records = parse_json_document(payload, rules)
        result = normalize_records(records, rules)
    except DocumentError as exc:
        st.error(f"No se pudo procesar {label}: {exc}")
        st.info("La pantalla sigue operativa: seleccione otro archivo o vuelva a usar los datos de ejemplo.")
        return
    except Exception:
        st.error(f"No se pudo procesar {label} por un error interno controlado.")
        return

    metrics = calculate_metrics(result.valid, result.invalid, total_processed=len(records))
    _show_global_metrics(metrics)
    valid_filtered = _valid_transactions_view(result.valid)
    _show_tabs(result.valid, valid_filtered, result.invalid, rules)


def _show_global_metrics(metrics: dict[str, Any]) -> None:
    total = metrics["total_processed"]
    validity = (metrics["valid_count"] / total * 100) if total else 0
    cards = st.columns(4)
    cards[0].metric("Procesadas", metrics["total_processed"])
    cards[1].metric("Válidas", metrics["valid_count"])
    cards[2].metric("Inválidas", metrics["invalid_count"])
    cards[3].metric("Tasa de validez", f"{validity:.1f}%")
    st.caption(
        "Estados válidos: " + ", ".join(f"{key}: {value}" for key, value in metrics["status_counts"].items())
        if metrics["status_counts"]
        else "No hay estados válidos que mostrar."
    )
    totals = metrics["all_valid_totals_by_currency"]
    success = metrics["success_totals_by_currency"]
    if totals:
        st.caption("Totales de todos los válidos: " + " · ".join(f"{currency} {amount:.2f}" for currency, amount in totals.items()))
        st.caption("Totales SUCCESS: " + " · ".join(f"{currency} {success.get(currency, 0):.2f}" for currency in totals))
    else:
        st.caption("No hay importes válidos que mostrar.")


def _valid_transactions_view(valid: list[dict[str, Any]]) -> list[dict[str, Any]]:
    st.subheader("Filtros de transacciones válidas")
    states = ["Todos"] + sorted({row["status"] for row in valid})
    currencies = ["Todas"] + sorted({row["currency"] for row in valid})
    sources = ["Todas"] + sorted({row["source"] for row in valid})
    col1, col2, col3 = st.columns(3)
    state = col1.selectbox("Estado", states)
    currency = col2.selectbox("Moneda", currencies)
    source = col3.selectbox("Fuente", sources)
    query = st.text_input("Buscar por ID (coincidencia parcial)").strip().casefold()
    dates = st.date_input("Rango de fechas UTC", value=())
    sort_by = st.selectbox("Ordenar por", ["Fecha", "Importe", "ID"])
    descending = st.checkbox("Orden descendente", value=False)

    filtered = []
    for row in valid:
        row_date = date.fromisoformat(row["timestamp"][:10])
        if state != "Todos" and row["status"] != state:
            continue
        if currency != "Todas" and row["currency"] != currency:
            continue
        if source != "Todas" and row["source"] != source:
            continue
        if query and query not in row["id"].casefold():
            continue
        if isinstance(dates, tuple) and len(dates) == 2:
            if row_date < dates[0] or row_date > dates[1]:
                continue
        elif isinstance(dates, date) and row_date != dates:
            continue
        filtered.append(row)

    sort_key = {"Fecha": lambda row: row["timestamp"], "Importe": lambda row: row["amount"], "ID": lambda row: row["id"]}[sort_by]
    filtered.sort(key=sort_key, reverse=descending)
    st.caption(f"Resultados filtrados: {len(filtered)}")
    return filtered


def _show_tabs(valid: list[dict[str, Any]], filtered: list[dict[str, Any]], invalid: list[dict[str, Any]], rules: dict[str, Any]) -> None:
    valid_tab, invalid_tab, rules_tab = st.tabs(["Transacciones válidas", "Registros inválidos", "Reglas activas"])
    with valid_tab:
        st.dataframe([_display_valid_row(row) for row in filtered], use_container_width=True, hide_index=True)
        st.download_button("Descargar vista filtrada", serialize_normalized_json(filtered), "transacciones_filtradas.json", "application/json")
        if not filtered:
            st.info("No hay transacciones que coincidan con los filtros actuales.")
    with invalid_tab:
        codes = ["Todos"] + sorted({row["error_code"] for row in invalid})
        selected_code = st.selectbox("Filtrar por código", codes, key="invalid_code")
        shown_errors = [row for row in invalid if selected_code == "Todos" or row["error_code"] == selected_code]
        st.dataframe([_display_error_row(row) for row in shown_errors], use_container_width=True, hide_index=True)
        st.download_button("Descargar diagnósticos", serialize_errors_json(shown_errors), "registros_invalidos.json", "application/json")
        if not shown_errors:
            st.info("No hay registros inválidos para este filtro.")
    with rules_tab:
        _show_rules(rules)


def _display_valid_row(row: dict[str, Any]) -> dict[str, Any]:
    return {**row, "amount": f"{row['currency']} {row['amount']:.2f}"}


def _display_error_row(row: dict[str, Any]) -> dict[str, Any]:
    return {"fila": row["index"] + 1, "fuente": row["source"] or "—", "código": row["error_code"], "motivo": row["message"]}


def _show_rules(rules: dict[str, Any]) -> None:
    st.write("Contrato activo leído desde config/rules.json. No se aplican conversiones de divisas.")
    for source, definition in rules["sources"].items():
        st.markdown(f"**Fuente {source}** — discriminador `{definition['discriminator']}`; importe `{definition['amount_style']}`; fecha `{', '.join(definition['date_formats'])}`.")
        st.write("Estados configurados:", ", ".join(f"{key} → {value}" for key, value in definition["status_map"].items()))
    st.write("Monedas:", ", ".join(rules["currencies"]))
    st.write("Límites:", f"{rules['policies']['max_records']} registros y {rules['policies']['max_file_bytes']} bytes por archivo.")


if __name__ == "__main__":
    main()

