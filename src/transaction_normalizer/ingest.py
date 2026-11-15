"""Lectura segura de documentos JSON de transacciones."""

from __future__ import annotations

import json
from typing import Any

from .models import DocumentError


def parse_json_document(payload: bytes, rules: dict[str, Any]) -> list[Any]:
    """Parsea un arreglo o un contenedor ``transactions`` sin ejecutar su contenido."""

    max_bytes = int(rules["policies"]["max_file_bytes"])
    max_records = int(rules["policies"]["max_records"])
    if not isinstance(payload, (bytes, bytearray)):
        raise DocumentError("El archivo de entrada debe leerse como bytes.")
    if len(payload) > max_bytes:
        raise DocumentError("El archivo supera el límite de tamaño permitido.")
    if not payload:
        raise DocumentError("El archivo está vacío.")

    def reject_constant(value: str) -> Any:
        raise ValueError(f"Constante JSON no permitida: {value}")

    try:
        decoded = bytes(payload).decode("utf-8-sig")
        document = json.loads(decoded, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError, OverflowError) as exc:
        raise DocumentError("No se pudo leer el documento JSON; revise su codificación y sintaxis.") from exc
    except Exception as exc:
        raise DocumentError("No se pudo leer el documento JSON por un error controlado.") from exc

    if isinstance(document, list):
        records = document
    elif isinstance(document, dict) and set(document) == {"transactions"} and isinstance(document.get("transactions"), list):
        records = document["transactions"]
    else:
        raise DocumentError("La raíz debe ser un arreglo o un objeto con la propiedad transactions.")

    if len(records) > max_records:
        raise DocumentError("El documento supera el límite de registros permitido.")
    return records

