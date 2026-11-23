# Matriz de evidencias académicas

Esta matriz organiza la evidencia disponible para la rúbrica. No garantiza una
puntuación máxima: la evaluación final depende de la revisión del docente y de
las evidencias que se acepten como válidas.

## Criterio 1 — Refactorización profunda y justificada (máximo 2.5)

**Implementado:** separación de modelos, validaciones, ingestión, servicio,
adaptadores A/B/C, registro de fuentes, métricas, filtros, exportaciones y UI.

**Archivos:** `src/transaction_normalizer/`, `app.py`,
[`docs/refactoring.md`](refactoring.md), [`docs/baseline.md`](baseline.md).

**Evidencia:** commit `5d560b7`; contratos de A/B/C, `Decimal`, UTC,
duplicados, procesamiento parcial y exportaciones comprobados por tests.

**Limitaciones:** `ProcessingResult` conserva diccionarios en su frontera
pública por compatibilidad; la UI aún depende de Streamlit para presentación.

## Criterio 2 — Skills reutilizables y documentadas (máximo 2.5)

**Implementado:** `transaction-auditor`, `normalization-rules` y
`regression-validator`, cada una con `SKILL.md`, script ejecutable y recursos
de referencia.

**Archivos:** `.agents/skills/`, `tests/test_skills.py`,
[`docs/skill-validation.md`](skill-validation.md).

**Evidencia:** auditoría del ejemplo 3/3/0, lote mixto 9/3/6, reglas válidas y
runner de regresión exitoso.

**Limitaciones:** ejecutar un script local no prueba activación automática de
una skill por Codex; esa activación depende del cliente.

## Criterio 3 — Personalización avanzada de agentes (máximo 2)

**Implementado:** agentes Codex `transaction_reviewer` y `quality_guardian`,
prompts estructurados, skills asociadas, límite de concurrencia y runtime
`AuditAgent` con herramientas cerradas, prompts y proveedor desacoplado.

**Archivos:** `.codex/`, `src/transaction_normalizer/agent/`,
[`docs/agent-personalization.md`](agent-personalization.md),
[`docs/agent-execution-evidence.md`](agent-execution-evidence.md).

**Evidencia:** delegación real reportada en FASE 4, 29 pruebas del runtime en
FASE 5, 36 pruebas consolidadas después de la integración.

**Limitaciones:** no se ha probado una llamada real de OpenAI; no se afirma
que los TOML hayan sido seleccionados automáticamente por nombre en todos los
clientes Codex.

## Criterio 4 — Uso consciente de IA y validación humana (máximo 1.5)

**Implementado:** desarrollo incremental asistido, restricciones de privacidad,
fallback determinista, modo local sin credenciales, revisión de diffs y
pruebas automatizadas.

**Archivos:** [`docs/ai-assisted-development.md`](ai-assisted-development.md),
`AGENTS.md`, `provider.py`, `ui/audit_panel.py`.

**Evidencia:** no se realizaron llamadas externas; las respuestas financieras
se obtienen de funciones Python; el modo IA requiere opt-in y confirmación.

**Pendiente:** inspección visual manual, aprobación explícita de cualquier
recomendación de negocio y eventual prueba controlada de proveedor real.

## Criterio 5 — Código limpio y documentación técnica (máximo 1.5)

**Implementado:** tipos, separación de responsabilidades, errores controlados,
pruebas `unittest`, documentación de arquitectura, skills, agentes, runtime,
Streamlit, uso de IA y rúbrica.

**Archivos:** `README.md`, `AGENTS.md`, `docs/`, `tests/` y el paquete `src/`.

**Evidencia:** 36 pruebas aprobadas, `compileall`, `git diff --check`,
regression-validator y arranque Streamlit HTTP 200.

**Limitaciones:** permanecen avisos de deprecación de `use_container_width` en
la UI existente; no se corrigieron porque no afectan el contrato de esta fase.

## Resumen de validación

```text
unittest: 36 OK
compileall: OK
regression-validator: overall_passed=true
ejemplo: 3 procesados, 3 válidos, 0 inválidos, USD 201.00, EUR 99.99
mixto: 9 procesados, 3 válidos, 6 inválidos
OpenAI real: no ejecutado
inspección visual manual: pendiente
```
