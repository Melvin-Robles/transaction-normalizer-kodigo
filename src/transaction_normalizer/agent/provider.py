"""Abstracción opcional de proveedores generativos para el agente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol


class ProviderError(Exception):
    """Error base de un proveedor de auditoría."""


class ProviderConfigurationError(ProviderError):
    """Faltan dependencias o configuración para usar un proveedor."""


class ProviderRequestError(ProviderError):
    """El proveedor falló al procesar una solicitud."""


@dataclass(frozen=True)
class ProviderResponse:
    """Respuesta etiquetada para no confundir simulación con generación real."""

    text: str
    provider_name: str
    generated_by_model: bool


class LLMProvider(Protocol):
    """Contrato mínimo para un proveedor de interpretación."""

    def complete(self, *, system_prompt: str, user_prompt: str, context: str) -> ProviderResponse:
        """Interpreta contexto agregado y devuelve una respuesta etiquetada."""


class SimulatedProvider:
    """Proveedor explícito de pruebas; nunca se presenta como modelo real."""

    provider_name = "simulated"

    def complete(self, *, system_prompt: str, user_prompt: str, context: str) -> ProviderResponse:
        del system_prompt, user_prompt, context
        return ProviderResponse(
            text="[SIMULATED_PROVIDER] No se generó una respuesta de un modelo real.",
            provider_name=self.provider_name,
            generated_by_model=False,
        )


class OpenAIResponsesProvider:
    """Adaptador opcional para OpenAI Responses API.

    La dependencia ``openai`` se importa solo al construir el proveedor y la
    clave se obtiene únicamente de una variable de entorno. El agente no crea
    esta clase por defecto.
    """

    provider_name = "openai-responses"

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        timeout_seconds: float = 30.0,
        client: Any | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ProviderConfigurationError("timeout_seconds debe ser positivo.")
        resolved_model = model or os.getenv("OPENAI_AUDIT_AGENT_MODEL")
        if not resolved_model:
            raise ProviderConfigurationError(
                "Configure OPENAI_AUDIT_AGENT_MODEL antes de habilitar el proveedor."
            )
        self.model = resolved_model
        if client is not None:
            self._client = client
            return
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ProviderConfigurationError(f"Falta la variable de entorno {api_key_env}.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderConfigurationError(
                "Instale la dependencia opcional openai para habilitar el proveedor."
            ) from exc
        try:
            self._client = OpenAI(api_key=api_key, timeout=timeout_seconds)
        except Exception as exc:
            raise ProviderConfigurationError("No se pudo inicializar el cliente OpenAI.") from exc

    def complete(self, *, system_prompt: str, user_prompt: str, context: str) -> ProviderResponse:
        """Realiza una solicitud Responses solo cuando el proveedor fue habilitado."""

        try:
            response = self._client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Consulta:\n{user_prompt}\n\nDatos agregados verificables:\n{context}",
                    },
                ],
            )
        except Exception as exc:
            raise ProviderRequestError("El proveedor OpenAI no pudo completar la solicitud.") from exc
        text = getattr(response, "output_text", None)
        if not isinstance(text, str) or not text.strip():
            raise ProviderRequestError("El proveedor no devolvió output_text utilizable.")
        return ProviderResponse(
            text=text.strip(),
            provider_name=self.provider_name,
            generated_by_model=True,
        )
