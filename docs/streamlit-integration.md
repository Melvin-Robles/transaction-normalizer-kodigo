# Integración de auditoría inteligente en Streamlit

## Objetivo

La FASE 6 incorpora el agente Python de auditoría a la interfaz existente sin
crear un segundo motor de normalización ni cambiar las reglas financieras. La
normalización continúa siendo responsabilidad de `TransactionProcessingService`
y la auditoría recibe el `BatchProcessingResult` real de esa ejecución.

## Arquitectura

```text
app.py
  ├── _show_data_source
  ├── TransactionProcessingService.process_document
  ├── _show_batch_summary
  ├── _show_input_preview
  ├── pestaña Resultados
  │     ├── filtros
  │     └── exportaciones JSON
  └── pestaña Auditoría inteligente
        └── ui.audit_panel.render_audit_panel
              ├── AuditToolset (métricas agregadas)
              └── AuditAgent (consultas locales o proveedor explícito)
```

La huella SHA-256 del payload identifica el lote activo. `ui.audit_state`
conserva únicamente respuestas agregadas y reinicia el contexto cuando cambia
la huella; no copia ni cachea globalmente los registros financieros.

## Componentes de la interfaz

- **Normalización**: selector del ejemplo integrado o cargador JSON, con la
  validación y el procesamiento existentes.
- **Resultados**: tablas de válidos e inválidos, filtros combinables y
  descargas JSON sin cambios de contrato.
- **Auditoría inteligente**: conteos, calidad, errores por código,
  distribución por fuente y totales por moneda usando las herramientas reales
  de `agent/tools.py`.
- **Detalles de la auditoría**: estado del proveedor, herramientas utilizadas,
  iteraciones, finalización y errores controlados. No muestra razonamiento
  privado del modelo.

## Flujo de auditoría

1. El servicio procesa el lote en memoria.
2. El panel consulta `AuditToolset` para mostrar datos agregados.
3. El usuario selecciona una pregunta sugerida o escribe una consulta.
4. La auditoría local ejecuta `AuditAgent` sin proveedor y produce una
   respuesta reproducible.
5. La ruta IA solo aparece después de activar el modo, revisar la vista previa
   agregada y confirmar explícitamente la privacidad.
6. Si el proveedor falla, se muestra un error controlado y se conserva la
   auditoría local.

## Modos y configuración opcional

La ruta local siempre está disponible para un lote válido. La ruta IA requiere,
sin mostrar sus valores:

- dependencia `openai` instalada;
- `OPENAI_API_KEY` configurada;
- `OPENAI_AUDIT_AGENT_MODEL` configurada;
- activación explícita del usuario y confirmación de privacidad.

La interfaz no crea el proveedor ni intenta conectarse mientras el usuario no
confirma la acción. El proveedor recibe el contexto agregado de las
herramientas, no el JSON original completo.

## Ejemplos de consultas

```text
¿Cuál es la calidad general del lote?
¿Cuáles son los errores más frecuentes?
¿Qué fuentes presentan más problemas?
¿Cuáles son los importes por moneda?
¿Qué reglas están relacionadas con los errores detectados?
¿Qué recomendaciones de calidad puedes ofrecer?
```

Para probar la ruta local desde Streamlit, cargue el ejemplo integrado, abra
**Auditoría inteligente** y pulse **Ejecutar auditoría local**. No se requiere
API ni conexión externa.

## Seguridad y manejo de errores

- Las consultas no ejecutan Python, shell ni nombres de herramientas dados por
  el usuario.
- Las respuestas se renderizan como texto seguro, no como HTML confiable.
- No se muestran claves, payloads completos ni tracebacks al usuario.
- Importes permanecen separados por moneda y se calculan en el dominio.
- La UI captura errores del agente y mantiene operativos resultados y modo
  local.
- Cambiar de archivo invalida el estado de auditoría anterior.

## Validación

La integración se prueba con `streamlit.testing.v1.AppTest` para comprobar:

- arranque sin proveedor;
- visualización del panel y del ejemplo integrado;
- ejecución de una consulta local;
- estado vacío al seleccionar carga sin archivo;
- reinicio del contexto al cambiar de lote;
- ausencia de secretos en el diagnóstico de disponibilidad.

Las herramientas y el agente mantienen sus pruebas deterministas en
`tests/test_runtime_agent.py`. Las regresiones generales se ejecutan con
`unittest`, `compileall` y el runner de `regression-validator`.

En esta fase se ejecutaron 34 pruebas automatizadas: las 29 existentes, 4
pruebas nuevas de integración/estado de Streamlit y 1 prueba de selección de
la consulta de recomendaciones. Todas terminaron con éxito.

## Limitaciones

- La selección de herramientas continúa siendo determinista por palabras clave;
  no es un planificador autónomo basado en LLM.
- No se realizan llamadas externas durante las pruebas automatizadas.
- La disponibilidad real del proveedor depende de la instalación y
  configuración del entorno del usuario.
- No se persisten lotes, conversaciones ni resultados fuera de la sesión de
  Streamlit.
