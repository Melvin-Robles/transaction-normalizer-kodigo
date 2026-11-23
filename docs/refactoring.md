# FASE 2 — Refactorización de Transaction Normalizer

Fecha: 2026-11-22

## Objetivo

Separar responsabilidades del código existente sin cambiar el contrato
observable de normalización, métricas, exportaciones ni la interfaz Streamlit.
Esta fase no incorpora skills, agentes, proveedores LLM ni funcionalidades
visuales nuevas.

## Arquitectura anterior

Antes de la fase 2:

- `app.py` coordinaba la lectura, normalización, métricas, filtros y
  presentación.
- `normalizer.py` contenía detección de fuente, validación de campos, parsing
  de IDs, importes, monedas, estados y fechas en una sola unidad.
- Los resultados internos y públicos eran diccionarios sin modelos tipados.
- No existía un servicio de aplicación independiente de Streamlit.
- No existían adaptadores explícitos ni registro de fuentes.
- La lógica de filtrado vivía dentro de la función de UI.

El detalle de la línea base y sus resultados está en
[`docs/baseline.md`](baseline.md).

## Arquitectura nueva

```text
app.py
└── TransactionProcessingService
    ├── ingest.py
    ├── SourceRegistry
    │   ├── SourceAAdapter
    │   ├── SourceBAdapter
    │   ├── SourceCAdapter
    │   └── ConfiguredSourceAdapter (fallback configurable)
    ├── validation.py
    ├── metrics.py
    └── ProcessingResult

app.py ──> filters.py ──> resultados normalizados
                     └── exports.py
```

### Módulos añadidos

- `models.py` ahora contiene `NormalizedTransaction`, `Diagnostic` y
  `BatchProcessingResult`.
- `validation.py` centraliza validaciones compartidas de IDs, importes,
  monedas, estados, fechas y diagnósticos.
- `sources/base.py` contiene el flujo común de validación de un adaptador.
- `sources/source_a.py`, `source_b.py` y `source_c.py` son puntos de extensión
  independientes para cada fuente.
- `sources/registry.py` detecta fuentes por discriminador y delega al
  adaptador correspondiente.
- `service.py` coordina ingestión, normalización y métricas sin importar
  Streamlit.
- `filters.py` contiene el filtrado y ordenamiento como función pura.

### Compatibilidad mantenida

La función pública sigue disponible:

```python
normalize_records(records, rules) -> ProcessingResult
```

`ProcessingResult.valid` e `invalid` siguen siendo listas de diccionarios con
las mismas claves. El servicio usa modelos tipados internamente y convierte al
formato histórico solo en el borde de compatibilidad.

## Decisiones de diseño

### Modelos tipados sin romper consumidores existentes

Se introdujeron dataclasses inmutables para el dominio interno:

- `NormalizedTransaction` conserva `Decimal` y el orden de los seis campos.
- `Diagnostic` evita transportar el registro original dentro de un error.
- `BatchProcessingResult` agrupa registros, resultado y métricas para el caso
  de uso de aplicación.

No se reemplazaron las listas de diccionarios de `ProcessingResult`, porque la
UI y las exportaciones existentes dependen de esa forma.

### Reglas de negocio configurables

Los adaptadores reciben la definición de su fuente desde `rules.json`. Los
mapas de estados, campos, formatos, monedas y límites no se copiaron a
constantes alternativas de Python.

El registro usa adaptadores explícitos para A, B y C. Si se añade una fuente
configurada con otro nombre y un contrato compatible, se crea un adaptador
genérico configurado; la incorporación de formatos realmente nuevos requerirá
un adaptador específico.

### Validaciones compartidas

El parsing común se movió a `validation.py` para evitar duplicar las reglas de
IDs, importes, monedas, estados y timestamps. La validación mantiene:

- `Decimal` para importes.
- Dos decimales sin redondear valores con precisión excesiva.
- Fechas de salida en UTC.
- Duplicados por `(source, id)`.
- Los códigos y mensajes de error existentes.

### Servicio independiente de Streamlit

`TransactionProcessingService` permite probar el caso de uso con bytes o con
registros directamente, sin inicializar la interfaz. `app.py` queda a cargo de
selección de datos, mensajes y representación visual.

### Filtros puros

`filter_valid_records` recibe filtros explícitos y devuelve una lista nueva.
Esto permite probar la intersección de estado, moneda, fuente, fechas e ID sin
simular widgets de Streamlit.

## Evidencia de validación

Se ejecutaron:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py src tests
```

Resultado actual:

```text
13 tests ejecutados
13 OK
```

La suite incluye la caracterización original y pruebas nuevas para:

- Coordinación mediante `TransactionProcessingService`.
- Registro y detección de adaptadores.
- Modelo interno `NormalizedTransaction`.
- Filtros puros combinados.

El ejemplo integrado conserva:

```text
3 procesados
3 válidos
0 inválidos
USD 201.00
EUR 99.99
```

## Riesgos pendientes

- Los adaptadores A/B/C son actualmente especializaciones del flujo común y
  todavía no encapsulan comportamientos radicalmente distintos por fuente.
  Esto es intencional para no duplicar reglas durante esta fase.
- `ProcessingResult` continúa usando diccionarios en su frontera pública.
- La validación de configuración podría evolucionar hacia modelos tipados en
  una fase posterior, pero hacerlo ahora ampliaría el riesgo del contrato.
- La UI aún contiene detalles de presentación que podrían extraerse más
  adelante, pero ya no ejecuta ingestión, normalización ni filtrado de datos.
- No se han añadido skills, agentes ni LLM por instrucción de esta fase.
- La verificación visual manual de Streamlit sigue siendo necesaria después de
  cada cambio importante de interfaz.

## Criterio para la siguiente fase

Antes de añadir Agent Skills se debe mantener esta separación: una skill podrá
inspeccionar, explicar o verificar resultados, pero las decisiones de validez,
precisión monetaria, fechas, duplicados y exportación continuarán siendo
deterministas y verificables mediante pruebas.
