# Normalizador de transacciones

Aplicación web local en Python y Streamlit para cargar JSON heterogéneo de las fuentes A, B y C, normalizar los registros válidos y mostrar diagnósticos comprensibles para los inválidos.

## Requisitos

- Python 3.11 o superior.
- Windows, macOS o Linux.
- Conexión a Internet únicamente durante la instalación inicial.
- No se necesita base de datos, cuenta ni servicio externo.

## Instalación y arranque

Desde la carpeta raíz del proyecto, la que contiene `app.py`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Si PowerShell bloquea la activación del entorno virtual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Streamlit mostrará una dirección local, normalmente `http://localhost:8501`. El docente solo necesita abrir esa dirección en el navegador y utilizar la interfaz. Para detener el servidor, presione `Ctrl+C` en la terminal que lo inició.

## Recorrido recomendado en la interfaz

1. En el panel izquierdo, seleccione **Ejemplo integrado** para ver un lote preparado con las fuentes A, B y C.
2. Revise el resumen del lote: procesadas, válidas, inválidas, calidad e importes por moneda.
3. Abra **Ver ejemplos integrados** para consultar los tres JSON originales antes de la normalización.
4. Explore **Transacciones válidas** y use los filtros por estado, moneda, fuente, fecha o ID.
5. Abra **Registros inválidos** para consultar los motivos de rechazo.
6. Use los botones de descarga para obtener exactamente la vista que está observando.
7. Para cargar información propia, seleccione **Cargar archivo JSON** y arrastre un archivo o pulse **Examinar**.

## Archivos de demostración para cargar manualmente

En `data/pruebas_ui/` se incluyen archivos que pueden cargarse desde el front:

- `transacciones_validas.json`: 6 registros válidos de las tres fuentes.
- `transacciones_mixtas.json`: mezcla de registros válidos, inválidos, duplicados y sin fuente.
- `transacciones_envueltas.json`: prueba el formato `{ "transactions": [...] }`.
- `transacciones_vacias.json`: lote vacío.
- `transacciones_malformadas.json`: JSON con sintaxis incorrecta para comprobar el mensaje de error.

El archivo `data/transacciones_ejemplo.json` es el ejemplo integrado que la aplicación carga por defecto.

## Reglas principales

- El esquema normalizado contiene exactamente `id`, `amount`, `currency`, `timestamp`, `status` y `source`.
- Se admiten USD y EUR; no se convierten ni se mezclan importes entre monedas.
- A usa unidades mayores, B usa unidades menores (céntimos) y C exige el símbolo `€` con coma decimal.
- Las fechas se exportan en UTC.
- Los duplicados se controlan por `(source, id)` y solo se conserva la primera aparición válida.
- Los archivos cargados se procesan en memoria y no se guardan en disco.
- Las reglas activas se mantienen en `config/rules.json`.

## Arquitectura

- `app.py`: interfaz Streamlit y flujo de interacción.
- `src/transaction_normalizer/config.py`: carga y validación de configuración.
- `src/transaction_normalizer/ingest.py`: lectura segura y límites de entrada.
- `src/transaction_normalizer/service.py`: coordinación de ingestión, normalización y métricas sin depender de Streamlit.
- `src/transaction_normalizer/normalizer.py`: API de compatibilidad para normalización con `Decimal`.
- `src/transaction_normalizer/sources/`: adaptadores A/B/C y registro de fuentes.
- `src/transaction_normalizer/validation.py`: validaciones compartidas.
- `src/transaction_normalizer/filters.py`: filtros reutilizables sobre resultados válidos.
- `src/transaction_normalizer/metrics.py`: métricas y sumas separadas por moneda.
- `src/transaction_normalizer/exports.py`: descargas JSON seguras.
- `config/rules.json`: fuente de verdad de formatos, monedas, estados y límites.
- `data/`: ejemplo integrado y archivos de demostración para la interfaz.

## Agent Skills personalizadas

Las skills locales viven en `.agents/skills/` y no incorporan proveedores LLM ni
modifican automáticamente datos o configuración.

- `transaction-auditor`: genera auditorías JSON de lotes, con calidad, errores,
  distribución por fuente/moneda y recomendaciones fundamentadas en conteos.
- `normalization-rules`: revisa `config/rules.json`, sus límites y la
  compatibilidad con el registro real de adaptadores, sin editarlo.
- `regression-validator`: ejecuta `unittest`, compilación y el ejemplo
  integrado con subprocesses controlados y timeout.

Ejemplos:

```powershell
python .agents/skills/transaction-auditor/scripts/audit_batch.py data/transacciones_ejemplo.json
python .agents/skills/normalization-rules/scripts/validate_rules.py
python .agents/skills/regression-validator/scripts/run_regression.py
```

Cada skill contiene un `SKILL.md`, scripts ejecutables y referencias enfocadas.
La evidencia de validación se mantiene en
[`docs/skill-validation.md`](docs/skill-validation.md).

## Agentes personalizados de Codex

La personalización de agentes está definida únicamente para este repositorio:

- `.codex/config.toml`: habilita subagentes y limita la concurrencia a dos.
- `.codex/agents/transaction_reviewer.toml`: audita lotes y reglas usando
  `transaction-auditor` y `normalization-rules`.
- `.codex/agents/quality_guardian.toml`: revisa regresiones usando
  `regression-validator`.

Los agentes heredan el modelo, permisos, proveedor y MCP de la sesión principal.
No se fijan modelos específicos ni se modifica la configuración global del
usuario. Para usarlos desde un cliente Codex que haya cargado el proyecto,
solicita explícitamente una delegación:

```text
Usa transaction_reviewer para auditar data/pruebas_ui/transacciones_mixtas.json
y quality_guardian para ejecutar las regresiones. Espera ambos resultados y
consolida los hallazgos, separando las acciones que requieren aprobación humana.
```

La arquitectura y la evidencia de validación están documentadas en
[`docs/agent-personalization.md`](docs/agent-personalization.md). La sintaxis de
los TOML no implica por sí sola que un cliente haya activado un agente
personalizado en una sesión concreta.

## Agente Python de auditoría

La FASE 5 añade un runtime agéntico desacoplado en
`src/transaction_normalizer/agent/`. Por defecto funciona de forma
determinista sobre métricas agregadas y no requiere credenciales:

```python
from transaction_normalizer.agent import AuditAgent

response = AuditAgent(batch, rules).audit("¿Cuál es la calidad y los errores del lote?")
print(response.to_dict())
```

Incluye herramientas para métricas, errores, fuentes, monedas y reglas. El
proveedor OpenAI es opcional, usa Responses API, requiere `openai`,
`OPENAI_API_KEY` y `OPENAI_AUDIT_AGENT_MODEL`, y no se activa automáticamente.
No se realizaron llamadas externas durante las pruebas. Consulta
[`docs/runtime-agent.md`](docs/runtime-agent.md) y
[`docs/agent-execution-evidence.md`](docs/agent-execution-evidence.md).

