# Instrucciones persistentes para agentes

## Alcance

Este repositorio contiene un normalizador local de transacciones construido con
Python y Streamlit. Estas instrucciones aplican a cualquier agente o persona
que modifique el proyecto.

## Principios de implementación

- Mantener Python claro, modular y fácil de revisar.
- Separar presentación, ingestión, configuración, dominio, métricas y
  exportación.
- Aplicar DRY sin ocultar reglas de negocio importantes detrás de abstracciones
  innecesarias.
- Tratar todo JSON recibido como entrada no confiable.
- Validar tipos, formatos, límites, fuentes, estados, monedas e identificadores
  antes de normalizar.
- Manejar errores de forma controlada y comprensible, sin mostrar tracebacks al
  usuario final.
- Preservar `Decimal` durante los cálculos monetarios; no sustituirlo por
  `float`.
- Normalizar y exportar fechas en UTC.
- Mantener `config/rules.json` como fuente de verdad para reglas configurables.
- No incluir secretos, credenciales, tokens ni datos sensibles en el
  repositorio.

## Contratos que deben preservarse

- Fuentes A, B y C y su detección automática.
- Duplicados identificados por `(source, id)`.
- Procesamiento parcial: un registro inválido no cancela el lote completo.
- Métricas y sumas separadas por moneda.
- Exportaciones JSON del resultado normalizado y de los diagnósticos.
- Límites de seguridad de tamaño y cantidad de registros.
- Interfaz Streamlit operativa.

## Pruebas obligatorias

Después de cualquier cambio se deben ejecutar, como mínimo:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py src tests
```

Si cambia la interfaz o el flujo de carga, también debe verificarse el arranque
de Streamlit y documentarse la comprobación realizada. No se deben afirmar
pruebas que no se hayan ejecutado realmente.

## Cambios de reglas

No cambiar formatos, monedas, estados, límites ni políticas solo para hacer
pasar una prueba. Si una mejora requiere modificar un contrato, documentar la
decisión, actualizar las pruebas y explicar el impacto antes de implementarla.

## Agent Skills locales

Usar la skill adecuada cuando la solicitud corresponda a su responsabilidad:

- `transaction-auditor`: analizar un lote JSON ya procesado, sus diagnósticos,
  calidad y distribuciones. No modifica transacciones.
- `normalization-rules`: revisar o explicar `config/rules.json` y su
  compatibilidad con los adaptadores. No modifica la configuración.
- `regression-validator`: ejecutar comprobaciones después de cambios de código,
  adaptadores o validaciones. No cambia tests para ocultar fallos.

Las skills se encuentran en `.agents/skills/`. Sus scripts reutilizan el
servicio real y deben mantener sus códigos de salida y restricciones de
seguridad. No afirmar activación automática de una skill cuando solo se haya
ejecutado su script manualmente.

## Agentes personalizados del proyecto

La configuración local de Codex se encuentra en `.codex/` y no modifica la
configuración global del usuario:

- `transaction_reviewer`: auditor técnico de lotes y configuración. Usa
  `transaction-auditor` para datos y `normalization-rules` para reglas.
- `quality_guardian`: revisor de pruebas y contratos. Usa
  `regression-validator` después de cambios de código.

La concurrencia del proyecto está limitada a dos subagentes en
`.codex/config.toml`. Los agentes heredan permisos, modelo, proveedor y MCP de
la sesión principal; sus instrucciones de revisión no crean un sandbox nuevo.

### Cuándo delegar

- Delegar una auditoría de lote a `transaction_reviewer` cuando se necesiten
  métricas, códigos de error o explicación de calidad.
- Delegar una revisión de `rules.json` al mismo agente cuando se necesite
  verificar fuentes, formatos, mapas o límites.
- Delegar verificación de una modificación a `quality_guardian` cuando cambien
  adaptadores, validaciones, servicio, exportaciones o pruebas.
- Usar ambos en paralelo para una revisión completa: el primero analiza datos y
  configuración; el segundo comprueba regresiones del código.

### Flujo de coordinación

```text
Solicitud de auditoría
        |
        v
Coordinador Codex
        +--> transaction_reviewer
        |       +--> transaction-auditor
        |       +--> normalization-rules
        |
        +--> quality_guardian
                +--> regression-validator
        |
        v
Consolidación y revisión humana
```

La revisión humana es obligatoria antes de modificar transacciones, cambiar
reglas financieras, aceptar recomendaciones como hechos, aplicar correcciones
de código o publicar resultados. La existencia y sintaxis de los TOML no prueba
que Codex haya activado un agente personalizado en una sesión concreta.

## Agente Python de auditoría

`src/transaction_normalizer/agent/` contiene un runtime agéntico de la
aplicación, distinto de los agentes Codex. Usa herramientas agregadas de solo
lectura sobre `BatchProcessingResult`, limita iteraciones y deja el proveedor
generativo deshabilitado por defecto. La FASE 6 lo presenta en Streamlit a
través de `ui/audit_panel.py`: el modo local no requiere red y el modo IA solo
se habilita con configuración, activación y confirmación explícitas. La UI no
envía el JSON original completo y reinicia el contexto cuando cambia el lote.
La arquitectura y sus límites están documentados en
`docs/runtime-agent.md` y `docs/streamlit-integration.md`.
