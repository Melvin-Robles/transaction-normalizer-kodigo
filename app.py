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
    """Renderiza la experiencia completa de carga, resumen y exploración."""

    st.set_page_config(
        page_title="Normalizador de transacciones",
        page_icon="↔",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _show_header()

    try:
        rules = load_rules(RULES_PATH)
    except ConfigurationError as exc:
        st.error(str(exc))
        st.info("Corrija config/rules.json y vuelva a cargar la página.")
        return

    payload, label = _show_data_source()
    if payload is None:
        return

    try:
        records = parse_json_document(payload, rules)
        result = normalize_records(records, rules)
    except DocumentError as exc:
        st.error(f"No se pudo procesar {label}: {exc}")
        st.info("Puede seleccionar otro archivo desde el panel izquierdo sin reiniciar la aplicación.")
        return
    except Exception:
        st.error(f"No se pudo procesar {label} por un error interno controlado.")
        return

    metrics = calculate_metrics(result.valid, result.invalid, total_processed=len(records))
    _show_batch_summary(metrics, label)
    if label == "transacciones_ejemplo.json":
        _show_integrated_examples(records)
    filtered_valid = _show_valid_filters(result.valid)
    _show_results(filtered_valid, result.invalid)


def _show_header() -> None:
    """Muestra una cabecera breve con orientación para la primera visita."""

    st.title("Normalizador de transacciones")
    st.caption("Convierte JSON heterogéneo en datos consistentes, revisables y listos para descargar.")
    with st.container(border=True):
        st.subheader("Cómo empezar")
        st.caption("Una guía rápida para orientarte en la pantalla")
        steps = st.columns(3)
        for column, number, title, description in zip(
            steps,
            ["01", "02", "03"],
            ["Elige los datos", "Revisa el lote", "Explora y descarga"],
            [
                "Usa el ejemplo integrado o carga un archivo JSON.",
                "Comprueba cuántas filas son válidas y la calidad del lote.",
                "Aplica filtros, revisa diagnósticos y descarga tu vista.",
            ],
        ):
            column.markdown(f"**{number} · {title}**")
            column.caption(description)
        st.caption("El procesamiento es local: los archivos cargados se mantienen en memoria y no se guardan en disco.")


def _show_data_source() -> tuple[bytes | None, str]:
    """Presenta el selector de entrada y devuelve bytes más etiqueta segura."""

    with st.sidebar:
        st.header("1 · Elige los datos")
        st.caption("Puedes empezar con el ejemplo integrado o cargar tu propio JSON.")
        mode = st.radio(
            "Fuente de datos",
            ["Ejemplo integrado", "Cargar archivo JSON"],
            captions=["Ideal para conocer la aplicación", "Procesamiento local en memoria"],
            label_visibility="collapsed",
        )
        st.divider()

        if mode == "Ejemplo integrado":
            try:
                payload = DEFAULT_DATA_PATH.read_bytes()
            except OSError:
                st.error("No se encontró el ejemplo integrado.")
                return None, "datos de ejemplo"
            st.success("Ejemplo listo")
            st.caption("3 transacciones de las fuentes A, B y C.")
            return payload, "transacciones_ejemplo.json"

        upload = st.file_uploader(
            "Selecciona un archivo JSON",
            type=["json"],
            accept_multiple_files=False,
            help="Máximo 5 MiB. El archivo se procesa en memoria y no se guarda en disco.",
        )
        if upload is None:
            st.info("Aún no hay archivo. Arrástralo aquí o pulsa Examinar.")
            return None, "archivo cargado"
        size_kb = upload.size / 1024 if upload.size is not None else 0
        st.success("Archivo listo para procesar")
        st.caption(f"{upload.name} · {size_kb:.1f} KB")
        return upload.getvalue(), upload.name or "archivo cargado"


def _show_batch_summary(metrics: dict[str, Any], label: str) -> None:
    """Muestra el resultado del procesamiento con jerarquía visual clara."""

    st.subheader("2 · Resumen del lote")
    st.caption(f"Fuente activa: **{label}** · {metrics['total_processed']} registro(s) leído(s)")
    total = metrics["total_processed"]
    validity = (metrics["valid_count"] / total * 100) if total else 0
    cards = st.columns(4)
    cards[0].metric("Procesadas", f"{metrics['total_processed']:,}", help="Filas leídas del documento JSON.")
    cards[1].metric("Válidas", f"{metrics['valid_count']:,}", help="Filas normalizadas al esquema de seis campos.")
    cards[2].metric("Inválidas", f"{metrics['invalid_count']:,}", help="Filas separadas con un diagnóstico.")
    cards[3].metric("Tasa de validez", f"{validity:.1f}%", help="Válidas dividido entre procesadas.")
    st.progress(validity / 100 if total else 0, text=f"Calidad del lote: {validity:.1f}% de filas válidas")

    totals = metrics["all_valid_totals_by_currency"]
    success = metrics["success_totals_by_currency"]
    currencies = sorted(set(totals) | set(success))
    if currencies:
        st.caption("Importes por moneda · no se convierten ni se suman entre divisas")
        amount_cards = st.columns(max(1, min(3, len(currencies))))
        for card, currency in zip(amount_cards, currencies):
            card.metric(f"{currency} · todos los válidos", f"{totals.get(currency, 0):.2f}")
            card.caption(f"SUCCESS: {success.get(currency, 0):.2f}")
    else:
        st.info("El lote no contiene importes válidos para resumir.")

    statuses = metrics["status_counts"]
    if statuses:
        st.caption("Estados encontrados: " + " · ".join(f"{key}: {value}" for key, value in statuses.items()))


def _show_integrated_examples(records: list[Any]) -> None:
    """Permite inspeccionar los tres registros JSON incluidos en el proyecto."""

    with st.expander("Ver ejemplos integrados", expanded=True):
        st.caption("Estos son los registros originales antes de la normalización. Cada tarjeta representa una fuente distinta.")
        cards = st.columns(max(1, min(3, len(records))))
        for index, (card, record) in enumerate(zip(cards, records), start=1):
            source_name = _example_source_name(record)
            with card:
                st.markdown(f"**{source_name}**")
                st.caption(f"Registro de ejemplo {index}")
                st.json(record, expanded=False)


def _example_source_name(record: Any) -> str:
    """Identifica la fuente de una fixture de ejemplo sin mostrar reglas internas."""

    if isinstance(record, dict):
        if "id" in record:
            return "Fuente A"
        if "transaction_id" in record:
            return "Fuente B"
        if "ref" in record:
            return "Fuente C"
    return "Registro"


def _show_valid_filters(valid: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filtra y ordena válidos dentro de un panel desplegable."""

    st.subheader("3 · Explora las transacciones")
    with st.expander("Filtros y orden", expanded=True):
        st.caption("Combina varios filtros para encontrar exactamente las filas que necesitas.")
        states = ["Todos"] + sorted({row["status"] for row in valid})
        currencies = ["Todas"] + sorted({row["currency"] for row in valid})
        sources = ["Todas"] + sorted({row["source"] for row in valid})
        col1, col2, col3 = st.columns(3)
        state = col1.selectbox("Estado", states, help="Filtra por SUCCESS, FAILED o PENDING.")
        currency = col2.selectbox("Moneda", currencies)
        source = col3.selectbox("Fuente", sources, help="A, B o C según el formato de origen.")
        query = st.text_input("Buscar por ID", placeholder="Ejemplo: tx_001 o 204", help="Acepta coincidencias parciales y no distingue mayúsculas.").strip().casefold()
        date_col, sort_col, direction_col = st.columns([2, 1, 1])
        dates = date_col.date_input("Rango de fechas UTC", value=(), format="YYYY-MM-DD")
        sort_by = sort_col.selectbox("Ordenar por", ["Fecha", "Importe", "ID"])
        descending = direction_col.checkbox("Más recientes / mayores primero")

    filtered: list[dict[str, Any]] = []
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

    sort_key = {
        "Fecha": lambda row: row["timestamp"],
        "Importe": lambda row: row["amount"],
        "ID": lambda row: row["id"].casefold(),
    }[sort_by]
    filtered.sort(key=sort_key, reverse=descending)
    st.caption(f"Mostrando **{len(filtered)}** de **{len(valid)}** transacción(es) válidas")
    return filtered


def _show_results(filtered: list[dict[str, Any]], invalid: list[dict[str, Any]]) -> None:
    """Presenta únicamente las dos vistas operativas del resultado."""

    valid_tab, invalid_tab = st.tabs([
        f"Transacciones válidas · {len(filtered)}",
        f"Registros inválidos · {len(invalid)}",
    ])
    with valid_tab:
        st.caption("Vista normalizada. El importe se muestra con su moneda para facilitar la lectura.")
        st.dataframe(
            [_display_valid_row(row) for row in filtered],
            use_container_width=True,
            hide_index=True,
            height=400,
        )
        st.download_button(
            "Descargar resultados visibles",
            serialize_normalized_json(filtered),
            "transacciones_filtradas.json",
            "application/json",
            use_container_width=True,
        )
        if not filtered:
            st.info("No hay transacciones que coincidan con los filtros actuales. Prueba a quitar algún filtro.")

    with invalid_tab:
        if not invalid:
            st.success("Excelente: no hay registros inválidos en este lote.")
            return
        codes = ["Todos"] + sorted({row["error_code"] for row in invalid})
        selected_code = st.selectbox("Filtrar diagnósticos por código", codes, key="invalid_code")
        shown_errors = [row for row in invalid if selected_code == "Todos" or row["error_code"] == selected_code]
        st.caption(f"Mostrando **{len(shown_errors)}** de **{len(invalid)}** diagnóstico(s)")
        st.dataframe(
            [_display_error_row(row) for row in shown_errors],
            use_container_width=True,
            hide_index=True,
            height=400,
        )
        st.download_button(
            "Descargar diagnósticos visibles",
            serialize_errors_json(shown_errors),
            "registros_invalidos.json",
            "application/json",
            use_container_width=True,
        )


def _display_valid_row(row: dict[str, Any]) -> dict[str, Any]:
    """Adapta una fila normalizada para una lectura rápida en pantalla."""

    return {**row, "amount": f"{row['currency']} {row['amount']:.2f}"}


def _display_error_row(row: dict[str, Any]) -> dict[str, Any]:
    """Adapta un diagnóstico para mostrar fila humana y motivo seguro."""

    return {
        "fila": row["index"] + 1,
        "fuente": row["source"] or "—",
        "código": row["error_code"],
        "motivo": row["message"],
    }


if __name__ == "__main__":
    main()

