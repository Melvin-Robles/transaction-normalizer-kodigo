# Evidencia de ejecución multiagente y runtime

Fecha de consolidación: 2026-11-22

Este documento distingue evidencia reportada en la FASE 4 de comprobaciones
ejecutadas nuevamente durante la FASE 5. No se inventan invocaciones ni
respuestas de proveedores externos.

## Evidencia reportada por Codex en la FASE 4

Durante la FASE 4 se utilizó la herramienta real de delegación
`multi_agent_v1` con dos subagentes en paralelo, respetando el límite de dos
configurado en `.codex/config.toml`.

### `transaction_reviewer`

- Identificador de agente: `01a2067a-93d7-72d1-8713-021056fc95d6`.
- Nickname reportado por Codex: `Euclid`.
- Skills utilizadas: `transaction-auditor`, `normalization-rules`.
- Herramientas ejecutadas:

  ```powershell
  python .agents/skills/transaction-auditor/scripts/audit_batch.py data/pruebas_ui/transacciones_mixtas.json
  python .agents/skills/normalization-rules/scripts/validate_rules.py --rules config/rules.json
  ```

- Resultado reportado:
  - 9 procesados.
  - 3 válidos.
  - 6 inválidos.
  - Calidad: 33.33%.
  - Códigos: `MISSING_FIELD`, `INVALID_AMOUNT`, `CURRENCY_MISMATCH`,
    `DUPLICATE_TRANSACTION`, `INVALID_RECORD_TYPE`, `UNKNOWN_SOURCE`, una
    ocurrencia de cada uno.
  - Configuración válida y adaptadores A/B/C compatibles.

### `quality_guardian`

- Identificador de agente: `01a2067a-921d-7103-8638-7d0879506930`.
- Nickname reportado por Codex: `Kepler`.
- Skill utilizada: `regression-validator`.
- Herramienta ejecutada:

  ```powershell
  python .agents/skills/regression-validator/scripts/run_regression.py --timeout 60
  ```

- Resultado reportado:
  - 20 pruebas OK.
  - `compileall` OK.
  - Ejemplo integrado OK.
  - 3 procesados, 3 válidos, 0 inválidos.
  - USD 201.00 y EUR 99.99.

Estos resultados fueron devueltos por los subagentes en la conversación de la
FASE 4. La evidencia confirma delegación real, pero los subagentes no expusieron
un parámetro técnico que demostrara que Codex hubiera seleccionado
automáticamente los archivos TOML por nombre.

## Comprobaciones ejecutadas en la FASE 5

En esta sesión se ejecutaron localmente:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py src tests .agents/skills .codex
python .agents/skills/transaction-auditor/scripts/audit_batch.py data/pruebas_ui/transacciones_mixtas.json
python .agents/skills/normalization-rules/scripts/validate_rules.py --rules config/rules.json
python .agents/skills/regression-validator/scripts/run_regression.py --timeout 60
```

Resultado actual:

- 29 pruebas OK.
- Compilación OK.
- Reglas válidas.
- Auditoría del lote mixto: 9/3/6.
- Runner de regresión: `overall_passed: true`.
- Ejemplo integrado: 3/3/0, USD 201.00, EUR 99.99.

También se ejecutaron pruebas directas del runtime Python:

- modo determinista sin proveedor;
- proveedor simulado explícitamente etiquetado;
- error de proveedor con fallback determinista;
- ausencia de credenciales sin llamada de red;
- cliente OpenAI falso inyectado para comprobar la interfaz Responses;
- límite de iteraciones en auditoría completa;
- hash de fixture y lote sin modificaciones.

No se realizaron llamadas reales a OpenAI ni a ningún servicio externo.

## Comprobaciones de la integración Streamlit en FASE 6 y FASE 7

La integración fue implementada en el commit `4563960`. Las comprobaciones
automatizadas con `streamlit.testing.v1.AppTest` confirmaron:

- arranque del ejemplo sin proveedor;
- auditoría local determinista;
- consulta personalizada de importes por moneda;
- carga del lote mixto con 9 procesados, 3 válidos y 6 inválidos;
- estado vacío al seleccionar carga sin archivo;
- reinicio de estado cuando cambia la huella del lote;
- disponibilidad del proveedor sin exponer secretos.

La suite consolidada de la FASE 7 ejecutó 36 pruebas, además de
`compileall` y `regression-validator`. Streamlit se arrancó localmente y
respondió HTTP 200; esa comprobación no se presenta como inspección visual.
No se realizaron llamadas reales al proveedor LLM.

## Skills utilizadas en FASE 5

- `transaction-auditor`: contrato y reportes agregados de calidad.
- `normalization-rules`: contrato y vista segura de configuración.
- `regression-validator`: ejecución de pruebas, compilación y ejemplo.

Sus scripts reutilizan el servicio real; el agente Python reutiliza los mismos
resultados mediante `BatchProcessingResult`.

## Limitaciones de la evidencia

- La evidencia de la FASE 4 es un reporte devuelto por Codex y se conserva como
  tal; no se presenta como una nueva ejecución de esta sesión.
- La validación de custom agents TOML no equivale a activación automática de un
  nombre de agente en el cliente.
- El proveedor real OpenAI no se probó con red ni credenciales.
- La UI no persiste lotes ni conversaciones fuera de la sesión.
- Las respuestas del runtime sin proveedor son deterministas, no generativas.
