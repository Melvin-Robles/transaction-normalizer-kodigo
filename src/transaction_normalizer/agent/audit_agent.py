"""Agente de auditoría con herramientas deterministas y proveedor opcional."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..models import BatchProcessingResult
from .provider import LLMProvider, ProviderError
from .tools import AuditToolset, ToolError, select_tools


class AuditAgentError(Exception):
    """Error controlado del agente de auditoría."""


class IterationLimitError(AuditAgentError):
    """La consulta requiere más herramientas que el límite permitido."""


SYSTEM_PROMPT_PATH = Path(__file__).with_name("prompts") / "system.md"


@dataclass(frozen=True)
class AuditResponse:
    """Respuesta auditable del agente."""

    query: str
    selected_tools: tuple[str, ...]
    tool_results: dict[str, dict[str, Any]]
    summary: str
    iterations: int
    provider_status: str
    generated_by_model: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "selected_tools": list(self.selected_tools),
            "tool_results": self.tool_results,
            "summary": self.summary,
            "iterations": self.iterations,
            "provider_status": self.provider_status,
            "generated_by_model": self.generated_by_model,
            "warnings": list(self.warnings),
        }


class AuditAgent:
    """Interpreta consultas mediante herramientas locales de solo lectura."""

    def __init__(
        self,
        batch: BatchProcessingResult,
        rules: dict[str, Any],
        *,
        provider: LLMProvider | None = None,
        max_iterations: int = 5,
    ) -> None:
        if max_iterations <= 0:
            raise AuditAgentError("max_iterations debe ser positivo.")
        self._tools = AuditToolset(batch, rules)
        self._provider = provider
        self._max_iterations = max_iterations
        self._system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    def available_tools(self) -> list[dict[str, Any]]:
        """Expone únicamente metadatos de herramientas seguras."""

        return self._tools.available()

    def audit(self, query: str) -> AuditResponse:
        """Ejecuta la consulta con un número acotado de invocaciones."""

        try:
            selected = select_tools(query)
        except ToolError as exc:
            raise AuditAgentError(str(exc)) from exc
        if len(selected) > self._max_iterations:
            raise IterationLimitError(
                f"La consulta requiere {len(selected)} herramientas y el límite es {self._max_iterations}."
            )

        results: dict[str, dict[str, Any]] = {}
        for name in selected:
            results[name] = self._tools.invoke(name)
        summary = self._deterministic_summary(query, results)
        warnings: list[str] = []
        provider_status = "disabled"
        generated_by_model = False

        if self._provider is not None:
            context = json.dumps(results, ensure_ascii=False, sort_keys=True)
            try:
                provider_response = self._provider.complete(
                    system_prompt=self._system_prompt,
                    user_prompt=query,
                    context=context,
                )
                summary = provider_response.text
                provider_status = provider_response.provider_name
                generated_by_model = provider_response.generated_by_model
            except ProviderError as exc:
                provider_status = "error"
                warnings.append(str(exc))
                warnings.append("Se conserva el resumen determinista; no se presentó el fallo como respuesta generativa.")

        return AuditResponse(
            query=query,
            selected_tools=tuple(selected),
            tool_results=results,
            summary=summary,
            iterations=len(selected),
            provider_status=provider_status,
            generated_by_model=generated_by_model,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _deterministic_summary(query: str, results: dict[str, dict[str, Any]]) -> str:
        """Genera una explicación local sin fingir una respuesta de LLM."""

        parts = [f"Consulta auditada en modo determinista: {query.strip()}"]
        metrics = results.get("query_batch_metrics")
        if metrics:
            parts.append(
                "Lote: "
                f"{metrics['total_processed']} procesado(s), "
                f"{metrics['valid_count']} válido(s), "
                f"{metrics['invalid_count']} inválido(s), "
                f"calidad {metrics['quality_percent']:.2f}%."
            )
        errors = results.get("query_error_distribution")
        if errors:
            parts.append(f"Diagnósticos por código: {errors['by_code'] or 'ninguno'}.")
        sources = results.get("query_source_statistics")
        if sources:
            parts.append(f"Calidad por fuente: {sources}.")
        currencies = results.get("query_currency_totals")
        if currencies:
            parts.append(f"Totales separados por moneda: {currencies['all_valid_totals_by_currency']}.")
        if "query_normalization_rules" in results:
            parts.append("Las reglas activas fueron consultadas desde la configuración cargada.")
        parts.append("No se modificaron datos y no se utilizó un proveedor generativo.")
        return " ".join(parts)
