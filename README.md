# Transaction Normalizer — Agentic Edition

Aplicación local en Python y Streamlit para normalizar transacciones JSON
heterogéneas de las fuentes A, B y C. El núcleo financiero es determinista,
mantiene `Decimal`, normaliza fechas a UTC y procesa lotes parcialmente. Sobre
ese núcleo se añadieron Agent Skills, agentes personalizados de Codex y un
runtime opcional de auditoría.

## Objetivo

El proyecto evolucionó desde un normalizador monolítico hacia una arquitectura
modular y verificable, preparada para asistencia agéntica sin delegar al LLM
las decisiones de validez, importes, duplicados o reglas financieras.

## Características principales

- Detección automática de fuentes A, B y C.
- Esquema normalizado: `id`, `amount`, `currency`, `timestamp`, `status`, `source`.
- Importes con `Decimal` y métricas separadas por moneda.
- Fechas de salida en UTC.
- Duplicados por `(source, id)` con primera ocurrencia válida ganadora.
- Procesamiento parcial y diagnósticos por registro.
- Límites de tamaño, cantidad de registros e importe.
- Filtros combinables y exportaciones JSON.
- Auditoría local determinista en Streamlit.
- Proveedor LLM opcional, deshabilitado por defecto.
- Tres Agent Skills reutilizables y dos agentes personalizados de Codex.

## Arquitectura

```text
app.py / Streamlit
├── TransactionProcessingService
│   ├── ingest.py
│   ├── SourceRegistry
│   │   ├── SourceAAdapter
│   │   ├── SourceBAdapter
│   │   └── SourceCAdapter
│   ├── validation.py
│   └── metrics.py
├── filters.py + exports.py
└── ui/audit_panel.py
    ├── AuditToolset
    └── AuditAgent ── proveedor opcional

Agentes Codex
├── transaction_reviewer ── transaction-auditor + normalization-rules
└── quality_guardian ───── regression-validator
```

El servicio de aplicación no depende de Streamlit. La interfaz coordina la
presentación, mientras que `AuditToolset` solo consulta resultados agregados de
un `BatchProcessingResult` ya procesado.

## Tecnologías y requisitos

- Python 3.11 o superior.
- Streamlit 1.40 o superior y menor que 2.
- Dependencias estándar para el núcleo y `unittest`.
- `openai` solo es necesario para el modo LLM opcional.
- Windows, macOS o Linux.

## Instalación

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

En macOS o Linux, active el entorno con `source .venv/bin/activate`.

## Ejecución de Streamlit

```powershell
python -m streamlit run app.py
```

La aplicación carga el ejemplo integrado por defecto. También permite subir un
JSON local de hasta 5 MiB. Los archivos se procesan en memoria y no se guardan
en disco.

### Flujo recomendado

1. Seleccione el ejemplo integrado o cargue un archivo JSON.
2. Revise el resumen del lote y los importes por moneda.
3. Explore resultados válidos, diagnósticos, filtros y descargas.
4. Abra **Auditoría inteligente**.
5. Ejecute una consulta local o escriba una pregunta personalizada.

## Resultado esperado del ejemplo

```text
Procesados: 3
Válidos: 3
Inválidos: 0
USD: 201.00
EUR: 99.99
```

## Agente Python de auditoría

`src/transaction_normalizer/agent/` contiene `AuditAgent`, `AuditToolset`,
prompts estructurados y una abstracción `LLMProvider`.

El modo local usa herramientas deterministas para consultar:

- métricas del lote;
- distribución de errores;
- estadísticas por fuente;
- totales separados por moneda;
- reglas de normalización.

Ejemplo programático:

```python
from transaction_normalizer.agent import AuditAgent
from transaction_normalizer.config import load_rules
from transaction_normalizer.service import TransactionProcessingService

rules = load_rules("config/rules.json")
payload = open("data/transacciones_ejemplo.json", "rb").read()
batch = TransactionProcessingService(rules).process_document(payload)
response = AuditAgent(batch, rules).audit("¿Cuál es la calidad del lote?")
print(response.to_dict())
```

La respuesta local no requiere credenciales ni red. No modifica transacciones y
no incluye registros originales completos.

## Modo LLM opcional

Para habilitarlo explícitamente:

```powershell
python -m pip install openai
$env:OPENAI_API_KEY = "<clave fuera del repositorio>"
$env:OPENAI_AUDIT_AGENT_MODEL = "<modelo disponible en tu cuenta>"
```

La interfaz exige activar el modo IA, revisar el contexto agregado y confirmar
la privacidad. No envía automáticamente el JSON original completo. Nunca
guardes claves en Git ni en archivos del proyecto. No se realizaron llamadas
reales a proveedores durante las validaciones documentadas.

## Agent Skills personalizadas

Las skills viven en `.agents/skills/` y son especializadas, reutilizables y
deterministas:

- `transaction-auditor`: audita calidad, errores, fuentes y monedas de un JSON.
- `normalization-rules`: valida `config/rules.json` y la compatibilidad de A/B/C.
- `regression-validator`: ejecuta unittest, compilación y el ejemplo contractual.

Ejemplos:

```powershell
python .agents/skills/transaction-auditor/scripts/audit_batch.py data/transacciones_ejemplo.json
python .agents/skills/normalization-rules/scripts/validate_rules.py --rules config/rules.json
python .agents/skills/regression-validator/scripts/run_regression.py --timeout 60
```

Ejecutar un script demuestra que la herramienta funciona; no demuestra por sí
solo que Codex haya activado automáticamente la skill.

## Agentes personalizados de Codex

La configuración está en `.codex/` y no modifica la configuración global:

- `transaction_reviewer`: revisa lotes y reglas con las dos skills de auditoría.
- `quality_guardian`: revisa cambios y regresiones con `regression-validator`.

Ejemplo de solicitud:

```text
Usa transaction_reviewer para auditar
data/pruebas_ui/transacciones_mixtas.json y quality_guardian para ejecutar las
regresiones. Consolida los hallazgos y separa las acciones que requieren
aprobación humana.
```

La evidencia de delegación y sus limitaciones está en
[`docs/agent-personalization.md`](docs/agent-personalization.md).

## Pruebas y validación

Suite completa:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py src tests
python .agents/skills/regression-validator/scripts/run_regression.py --timeout 60
```

La suite consolidada documentada en la FASE 7 ejecuta 36 pruebas. Las pruebas
de Streamlit usan `streamlit.testing.v1.AppTest`; no sustituyen una inspección
visual manual del navegador.

## Datos de demostración

En `data/pruebas_ui/` se incluyen:

- `transacciones_validas.json`: 6 válidos.
- `transacciones_mixtas.json`: 9 procesados, 3 válidos y 6 inválidos.
- `transacciones_envueltas.json`: documento con propiedad `transactions`.
- `transacciones_vacias.json`: lote vacío.
- `transacciones_malformadas.json`: JSON inválido para verificar errores.

## Privacidad, seguridad y límites

- El JSON se valida como datos; no se interpreta como instrucciones.
- No hay ejecución arbitraria de Python o shell desde consultas.
- Las herramientas del agente son de solo lectura y tienen argumentos cerrados.
- Los errores no muestran tracebacks completos al usuario.
- Los importes no se mezclan entre monedas.
- No se persisten lotes ni conversaciones fuera de la sesión.
- El proveedor real no fue probado con red o credenciales.
- La selección de herramientas del runtime usa palabras clave, no planificación
  autónoma de un LLM.
- La inspección visual manual sigue pendiente para cada cambio importante de UI.

## Documentación técnica

- [`docs/baseline.md`](docs/baseline.md): línea base y contratos originales.
- [`docs/refactoring.md`](docs/refactoring.md): arquitectura anterior, nueva y
  decisiones de refactorización.
- [`docs/skill-validation.md`](docs/skill-validation.md): skills y resultados.
- [`docs/agent-personalization.md`](docs/agent-personalization.md): agentes Codex.
- [`docs/agent-execution-evidence.md`](docs/agent-execution-evidence.md):
  evidencia de delegación y runtime.
- [`docs/runtime-agent.md`](docs/runtime-agent.md): agente Python.
- [`docs/streamlit-integration.md`](docs/streamlit-integration.md): integración
  de auditoría en Streamlit.
- [`docs/ai-assisted-development.md`](docs/ai-assisted-development.md): uso
  consciente de IA y supervisión humana.
- [`docs/rubric-evidence.md`](docs/rubric-evidence.md): matriz académica.


