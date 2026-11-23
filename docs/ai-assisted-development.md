# Uso consciente de IA y desarrollo asistido

## Propósito

Este documento distingue el uso de ChatGPT/Codex como apoyo técnico de la
ejecución determinista del sistema. La IA ayudó a analizar requisitos,
proponer límites, revisar cambios y diseñar pruebas; la normalización, las
métricas monetarias y las decisiones de validez permanecen en Python y
`config/rules.json`.

No se atribuyen a la persona decisiones que no estén registradas en las
instrucciones de fase. Cuando la evidencia no permite confirmar una decisión o
una ejecución, se marca como pendiente.

## Herramientas de apoyo

- ChatGPT: análisis de requisitos, revisión técnica y planificación por fases.
- Codex: inspección del repositorio, edición aplicada al proyecto, ejecución de
  pruebas y delegación de revisiones.
- `unittest`, `compileall`, AppTest y scripts locales: validación reproducible
  independiente de una respuesta generativa.

## Metodología aplicada

1. Analizar el objetivo y los contratos antes de editar.
2. Inspeccionar el código real, reglas y documentación existente.
3. Convertir requisitos en cambios pequeños y responsabilidades separadas.
4. Implementar con preservación de `Decimal`, UTC, duplicados y procesamiento
   parcial.
5. Revisar el diff y el estado de Git.
6. Ejecutar pruebas y scripts deterministas.
7. Separar evidencia observada, recomendación técnica y limitación pendiente.
8. Requerir revisión humana para cambios financieros, reglas, secretos,
   publicación o aceptación de recomendaciones.

## Registro de fases

| Fase | Evolución | Evidencia disponible |
|---|---|---|
| 1 | Auditoría inicial y caracterización | [`docs/baseline.md`](baseline.md), fixtures y pruebas iniciales |
| 2 | Modelos, validaciones, servicio, adaptadores, registro y filtros | Commit `5d560b7`, [`docs/refactoring.md`](refactoring.md) |
| 3 | Tres Agent Skills con scripts y referencias | Commit `25470dc`, [`docs/skill-validation.md`](skill-validation.md) |
| 4 | `transaction_reviewer` y `quality_guardian` | `.codex/`, delegación reportada en [`docs/agent-personalization.md`](agent-personalization.md) |
| 5 | `AuditAgent`, herramientas, prompts y proveedores desacoplados | Commit `438061c`, [`docs/runtime-agent.md`](runtime-agent.md) |
| 6 | Integración determinista y opcional en Streamlit | Commit `4563960`, [`docs/streamlit-integration.md`](streamlit-integration.md) |

## Decisiones arquitectónicas y supervisión

| Propuesta apoyada por IA | Evidencia disponible | Decisión registrada en la actividad | Justificación | Validación |
|---|---|---|---|---|
| Separar el monolito en servicio, adaptadores y validaciones | `docs/refactoring.md`, commit `5d560b7` | Solicitado explícitamente en FASE 2 | Reducir acoplamiento sin cambiar contratos | Suite de caracterización, compileall y regresión |
| Mantener skills deterministas y sin modificar datos | Tres `SKILL.md`, scripts y referencias | Solicitado explícitamente en FASE 3 | Reutilización segura y trazable | `tests/test_skills.py` y ejecuciones reales |
| Diferenciar agentes Codex del runtime Python | `docs/agent-personalization.md`, `agent/` | Solicitado explícitamente en FASE 4–5 | Evitar confundir delegación del entorno con lógica de aplicación | TOML, pruebas del runtime y evidencia de delegación |
| Usar un panel local antes del modo IA | `ui/audit_panel.py`, `audit_state.py` | Solicitado explícitamente en FASE 6 | Mantener disponibilidad sin credenciales y limitar exposición | AppTest, sin proveedor externo |
| Habilitar OpenAI solo por opt-in y contexto agregado | `provider.py`, documentación y pruebas de configuración | Solicitado explícitamente en FASE 5–6 | Reducir riesgo de transmisión financiera | Cliente falso, bloqueo sin credenciales; llamada real pendiente |

Las decisiones anteriores fueron revisadas contra el diff y las pruebas. No se
aceptaron respuestas de un LLM como prueba de importes, calidad o regresión.

## Evidencias automatizadas

La validación consolidada reportada en la FASE 7 ejecuta 36 pruebas, compilación
y el runner de regresión. Los scripts de skills confirman el ejemplo, el lote
mixto y la configuración real. AppTest cubre arranque, consultas locales,
cambio de lote, carga mixta y estado vacío.

## Pendientes de completar por el estudiante

- Realizar una inspección visual manual en navegador de las pestañas, tablas,
  filtros y descargas.
- Si se desea usar IA generativa, instalar el proveedor, configurar secretos
  fuera del repositorio, revisar la política de privacidad y aprobar una
  prueba controlada.
- Registrar una decisión humana explícita sobre cualquier recomendación de
  configuración o cambio financiero.
