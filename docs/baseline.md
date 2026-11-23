# Línea base antes de la refactorización

Fecha de registro: 2026-11-22

## Propósito

Este documento registra el comportamiento real del proyecto antes de iniciar
una refactorización profunda. Las pruebas de esta fase son de caracterización:
su objetivo es proteger los contratos existentes, no rediseñar todavía la
lógica de negocio.

## Arquitectura original

La aplicación es un monolito de presentación pequeño, respaldado por un motor
de dominio separado dentro de un paquete `src`:

- `app.py` contiene la interfaz Streamlit y coordina carga, ingestión,
  normalización, métricas y exportación.
- `config.py` carga y valida la forma esencial de `config/rules.json`.
- `ingest.py` interpreta bytes como JSON, acepta un arreglo o un contenedor
  `{"transactions": [...]}` y aplica límites de entrada.
- `normalizer.py` detecta A/B/C por discriminadores y transforma cada registro
  al esquema normalizado de seis campos.
- `metrics.py` calcula conteos y sumas mediante `Decimal`, separadas por moneda.
- `exports.py` serializa normalizados y diagnósticos como JSON.
- `models.py` define errores controlados y `ProcessingResult`.
- `config/rules.json` contiene políticas, fuentes, monedas, mapas de estados,
  esquema y reglas de métricas.
- `data/` contiene el ejemplo integrado y fixtures para la UI.

El proyecto usa el layout `src`, requiere Python 3.11 o superior y depende de
Streamlit. No se encontró una base de datos, API, cliente LLM, agente ejecutable
ni skill instalada dentro del repositorio.

## Interfaces y contratos observables

Las funciones públicas principales son:

- `load_rules(path) -> dict`.
- `parse_json_document(payload, rules) -> list`.
- `normalize_records(records, rules) -> ProcessingResult`.
- `calculate_metrics(valid, invalid, total_processed=None) -> dict`.
- `serialize_normalized_json(records) -> str`.
- `serialize_errors_json(errors) -> str`.

Los contratos que deben preservarse son:

- Fuentes A, B y C con detección automática.
- Esquema `id`, `amount`, `currency`, `timestamp`, `status`, `source`.
- Importes con `Decimal` y dos decimales.
- Fechas de salida en UTC.
- Duplicados por `(source, id)`; la primera ocurrencia válida gana.
- Procesamiento parcial de lotes y diagnósticos por registro.
- Métricas y sumas sin mezclar monedas.
- Exportaciones JSON.
- Límite de 5 MiB y 10.000 registros.
- Interfaz Streamlit operativa.

## Hallazgos técnicos

### Acoplamiento y responsabilidades

- `app.py` coordina el caso de uso y también contiene detalles de presentación,
  filtrado, adaptación de filas y navegación visual. Esto dificulta probar el
  flujo completo sin Streamlit.
- `normalizer.py` concentra la detección de fuente, validación de campos,
  parsing de IDs, importes, monedas, fechas y estados. La lógica es legible,
  pero los distintos formatos están implementados mediante ramas condicionales
  y helpers internos, lo que puede crecer con cada nueva fuente.
- Los resultados de dominio son diccionarios sin tipos estructurales fuertes.
  Esto permite flexibilidad, pero deja más contratos implícitos entre módulos.
- `metrics.py` y `exports.py` dependen de las claves textuales del diccionario
  normalizado; cualquier cambio de esquema requiere coordinación manual.

### Duplicación y mantenibilidad

- Los nombres de campos y formatos viven principalmente en `rules.json`, pero
  los estilos de importe y algunas decisiones de parsing siguen expresados en
  código mediante strings como `major_units_decimal_point`.
- La interfaz repite adaptaciones específicas para mostrar válidos e inválidos.
- No hay una abstracción explícita de adaptador por fuente ni un registro de
  parsers extensible.

### Calidad y cobertura

- Antes de esta fase no existía un directorio `tests` ejecutable en la raíz.
- El paquete `Paquete_Proyecto_Normalizador_para_Codex` contiene documentación,
  fixtures y un plan de pruebas, pero no es parte del runtime actual.
- No existe logging estructurado ni métricas de ejecución históricas.
- La captura general de errores en `app.py` protege al usuario de tracebacks,
  pero reduce el detalle disponible para diagnóstico técnico.

## Resultados de la línea base

Se ejecutó el flujo real con `config/rules.json` y
`data/transacciones_ejemplo.json`:

```text
Registros leídos: 3
Válidos: 3
Inválidos: 0
IDs: tx_001, 204, A-77
USD: 201.00
EUR: 99.99
Estados: 3 SUCCESS
Timestamp normalizado: 2025-03-10T14:22:00Z
```

También se comprobaron las fixtures disponibles:

| Fixture | Válidos | Inválidos | Resultado relevante |
|---|---:|---:|---|
| `transacciones_validas.json` | 6 | 0 | Todas las filas válidas |
| `transacciones_mixtas.json` | 3 | 6 | Continúa después de errores y detecta duplicado |
| `transacciones_envueltas.json` | 2 | 0 | Acepta el contenedor `transactions` |
| `transacciones_vacias.json` | 0 | 0 | Lote vacío controlado |
| `transacciones_malformadas.json` | — | — | `DocumentError` controlado |

Las pruebas automatizadas de caracterización se encuentran en
`tests/test_characterization.py` y usan exclusivamente `unittest` de la
biblioteca estándar.

## Riesgos de la futura refactorización

- Alterar el orden o el tipo de los seis campos exportados.
- Reemplazar `Decimal` por `float` durante parsing, métricas o serialización.
- Cambiar la interpretación de fechas sin zona horaria.
- Hacer global la unicidad de IDs y romper la unicidad por fuente.
- Convertir errores por fila en errores fatales de lote.
- Introducir reglas en Python que contradigan `rules.json`.
- Cambiar el orden o el texto de los códigos de diagnóstico que usa la UI.
- Romper los filtros o descargar filas distintas a las visibles.
- Añadir una capa de agentes que interprete datos de transacciones como
  instrucciones ejecutables.

## Plan de módulos propuesto

La siguiente estructura es una propuesta para la siguiente fase; no se
implementa en esta línea base:

```text
src/transaction_normalizer/
├── domain/
│   ├── entities.py          # modelos tipados de transacción y diagnóstico
│   ├── value_objects.py     # Money, Currency, Timestamp, TransactionId
│   └── errors.py
├── sources/
│   ├── base.py              # contrato de adaptador por fuente
│   ├── source_a.py
│   ├── source_b.py
│   ├── source_c.py
│   └── registry.py
├── application/
│   ├── normalize_batch.py   # caso de uso principal
│   ├── filter_results.py
│   └── reports.py
├── infrastructure/
│   ├── config_loader.py
│   ├── json_reader.py
│   └── serializers.py
└── presentation/
    └── streamlit_app.py
```

La futura capa de Agent Skills debe permanecer separada del dominio: una skill
puede ayudar a inspeccionar, explicar o verificar resultados, pero no debe
reemplazar las validaciones deterministas ni ejecutar instrucciones contenidas
en transacciones, archivos o mensajes externos.

## Validación humana pendiente

Antes de aceptar la refactorización se debe revisar manualmente:

1. Que el ejemplo integrado siga produciendo 3 válidos, USD 201.00 y EUR 99.99.
2. Que los casos inválidos sigan separados del lote.
3. Que la interfaz permita cargar un archivo defectuoso y luego uno válido.
4. Que los filtros y descargas coincidan con la vista mostrada.
5. Que cualquier skill o agente añadido documente sus límites, entradas,
   salidas, uso de IA y revisión humana.
