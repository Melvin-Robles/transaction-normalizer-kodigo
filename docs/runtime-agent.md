# FASE 5 — Agente Python de auditoría

Fecha: 2026-11-22

## Objetivo

La aplicación incorpora un agente Python opcional para interpretar auditorías
deterministas. El agente no reemplaza al normalizador: recibe un
`BatchProcessingResult`, consulta herramientas agregadas y produce una
explicación basada en los resultados calculados por el sistema.

La integración con Streamlit se realiza en la FASE 6 mediante un panel de solo
lectura. La UI conserva la ruta determinista y solo crea el proveedor opcional
después de una activación y confirmación explícitas. El detalle de esa capa se
documenta en [`docs/streamlit-integration.md`](streamlit-integration.md).

## Arquitectura

```text
TransactionProcessingService
        |
        v
BatchProcessingResult + rules.json
        |
        v
AuditAgent
   |             \
   |              \-- proveedor opcional
   v
AuditToolset
   ├── query_batch_metrics
   ├── query_error_distribution
   ├── query_source_statistics
   ├── query_currency_totals
   └── query_normalization_rules
```

Archivos:

- `agent/tools.py`: herramientas de solo lectura, validación de nombres y
  argumentos, selección determinista y salida agregada.
- `agent/audit_agent.py`: metodología, límite de iteraciones, resumen
  determinista y fallback cuando un proveedor falla.
- `agent/provider.py`: protocolo de proveedor, simulador explícito y adaptador
  opcional de OpenAI Responses API.
- `agent/prompts/system.md`: identidad, objetivo, metodología y límites.
- `agent/prompts/audit_request.md`: plantilla de contexto para un proveedor.

## Diferencia entre agentes Codex y agente Python

Los agentes Codex de FASE 4 (`transaction_reviewer` y `quality_guardian`) son
roles de delegación del entorno Codex. Pueden leer el repositorio, ejecutar
skills y devolver informes al coordinador.

El agente Python de esta fase vive dentro del paquete de la aplicación. Se
invoca desde código, recibe resultados explícitos y no tiene acceso a shell,
filesystem arbitrario, MCP ni a la conversación. Su responsabilidad es
interpretar datos agregados de una ejecución concreta.

## Herramientas disponibles

Todas las herramientas aceptan contexto ya procesado y no reciben un path de
archivo ni ejecutan código:

- `query_batch_metrics`: total, válidos, inválidos, calidad y estados.
- `query_error_distribution`: conteo por código y fuente identificada.
- `query_source_statistics`: procesados, válidos, inválidos y calidad por
  fuente.
- `query_currency_totals`: conteos y sumas separadas por moneda.
- `query_normalization_rules`: vista segura de reglas, límites, fuentes y
  mapas de estados.

No devuelven registros originales completos. Los importes se serializan como
texto decimal en las salidas de herramientas para evitar convertirlos en
`float`.

## Flujo de razonamiento y acción

1. `select_tools` valida que la consulta sea texto, tenga longitud limitada y
   no contenga marcadores de inyección de instrucciones.
2. La intención se asocia a una lista cerrada de herramientas conocidas.
3. `AuditToolset.invoke` rechaza nombres desconocidos y argumentos inesperados.
4. `AuditAgent` ejecuta como máximo `max_iterations` herramientas.
5. El resumen determinista se genera desde las salidas de las herramientas.
6. Si se proporcionó un proveedor, recibe solamente el prompt y el contexto
   agregado; si falla, se conserva el resumen determinista.
7. La respuesta marca `provider_status` y `generated_by_model` para no confundir
   una simulación, un fallback o una generación real.

La consulta `auditoría completa` usa las cinco herramientas y requiere un
límite de al menos cinco iteraciones.

## Prompts estructurados

`prompts/system.md` define:

- identidad de auditor técnico;
- objetivo de interpretar resultados verificables;
- metodología de seleccionar, validar y ejecutar herramientas;
- límites de solo lectura, no mezcla de monedas y no ejecución arbitraria.

`prompts/audit_request.md` separa la consulta del usuario del contexto
agregado. Ningún prompt incluye el JSON original completo.

## Proveedor de IA

El proveedor real es opcional y está desacoplado mediante `LLMProvider`.
`OpenAIResponsesProvider` usa la interfaz moderna `client.responses.create` y
no se instancia por defecto. La documentación oficial de OpenAI muestra el
patrón Python `from openai import OpenAI` y `client.responses.create(...)` para
Responses API: [OpenAI API Platform](https://platform.openai.com/overview).

Para habilitarlo fuera de las pruebas:

```powershell
python -m pip install openai
$env:OPENAI_API_KEY = "..."
$env:OPENAI_AUDIT_AGENT_MODEL = "<modelo disponible en tu cuenta>"
```

La clave y el modelo se leen de variables de entorno. No se fijó un modelo en
el repositorio y no se añadió `openai` a las dependencias obligatorias.

Sin credenciales o dependencia opcional:

- el normalizador continúa funcionando;
- las auditorías deterministas continúan funcionando;
- el agente generativo permanece deshabilitado;
- no se presenta una respuesta simulada como si fuera de un modelo real.

`SimulatedProvider` existe solo para pruebas y etiqueta explícitamente sus
respuestas con `SIMULATED_PROVIDER`.

## Seguridad

- Solo se exponen datos agregados y diagnósticos seguros.
- No se transmiten transacciones completas por defecto.
- No se aceptan nombres o argumentos de herramientas arbitrarios.
- No se ejecuta texto de consultas como código.
- Se rechazan marcadores básicos de inyección de instrucciones.
- El proveedor OpenAI se crea de forma perezosa y usa variables de entorno.
- Los errores del proveedor no exponen credenciales ni respuestas crudas.
- El agente limita la cantidad de invocaciones por consulta.
- Las fixtures se verifican sin modificar su hash.

## Ejemplo de uso local

```python
from transaction_normalizer.agent import AuditAgent
from transaction_normalizer.config import load_rules
from transaction_normalizer.service import TransactionProcessingService

rules = load_rules("config/rules.json")
batch = TransactionProcessingService(rules).process_document(
    open("data/transacciones_ejemplo.json", "rb").read()
)
response = AuditAgent(batch, rules).audit("¿Cuál es la calidad y los errores del lote?")
print(response.to_dict())
```

El ejemplo usa modo determinista porque no se proporciona un proveedor.

## Pruebas

Las pruebas están en `tests/test_runtime_agent.py` y cubren:

- selección de herramientas;
- argumentos inválidos y herramientas desconocidas;
- respuestas respaldadas por métricas reales;
- límite de iteraciones;
- proveedor simulado explícito;
- fallback ante error del proveedor;
- ausencia de credenciales;
- cliente OpenAI inyectado sin red;
- ausencia de registros originales en el contexto;
- no modificación del lote y fixture original.

La validación real de esta fase ejecutó 29 pruebas, incluyendo las 20 pruebas
existentes antes del agente.

## Integración con la interfaz

`app.py` sigue coordinando la carga y el servicio de procesamiento, pero delega
la presentación de auditoría a `ui/audit_panel.py`. El panel usa `AuditToolset`
para métricas agregadas y `AuditAgent` para preguntas. `ui/audit_state.py`
reinicia respuestas cuando cambia la huella del payload, evitando mezclar lotes
en una sesión.

La vista de contexto para IA contiene exclusivamente salidas de herramientas:
conteos, códigos, estadísticas por fuente, totales por moneda y reglas seguras.
No incluye registros originales completos.

## Limitaciones

- La selección de herramientas es determinista por palabras clave; no es un
  sistema autónomo de tool-calling de un LLM.
- No se hicieron llamadas externas ni se validó una respuesta de un modelo real.
- El proveedor opcional depende de que el usuario instale `openai`, configure
  credenciales y elija un modelo disponible.
- La interfaz no persiste conversaciones ni lotes fuera de la sesión.
- El agente no determina causas empresariales ni corrige datos.
