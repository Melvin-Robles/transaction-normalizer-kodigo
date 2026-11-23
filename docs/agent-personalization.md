# FASE 4 — Personalización multiagente en Codex

Fecha: 2026-11-22

## Objetivo

Configurar dos agentes personalizados de ámbito de proyecto para revisar el
Transaction Normalizer con responsabilidades distintas y reutilizar las tres
Agent Skills de la FASE 3.

La configuración sigue el formato vigente de Codex:

- `.codex/config.toml` contiene la configuración global de agentes del proyecto.
- `.codex/agents/*.toml` contiene un agente por archivo.
- Cada agente define `name`, `description` y `developer_instructions`.
- No se fijan modelos ni esfuerzos de razonamiento; se heredan de la sesión
  principal.
- Los agentes heredan permisos, proveedor y MCP de la sesión principal.
- La concurrencia máxima se limita a dos subagentes.

## Arquitectura

```text
Solicitud del usuario
        |
        v
Coordinador principal de Codex
        |
        +--> transaction_reviewer
        |       +--> transaction-auditor
        |       +--> normalization-rules
        |
        +--> quality_guardian
                +--> regression-validator
        |
        v
Resultados verificables
        |
        v
Informe consolidado + revisión humana
```

Los agentes son complementarios: `transaction_reviewer` estudia datos y
configuración; `quality_guardian` verifica código y contratos. No se creó un
tercer agente porque el coordinador principal puede consolidar ambos resultados.

## Agente `transaction_reviewer`

Archivo: `.codex/agents/transaction_reviewer.toml`

Responsabilidad: auditoría técnica de lotes JSON y `config/rules.json`.

Usa:

- `transaction-auditor` para calidad, diagnósticos y distribuciones.
- `normalization-rules` para reglas, fuentes, formatos, estados y límites.

Debe devolver objetivo, skills, herramientas, datos analizados, hallazgos,
recomendaciones, limitaciones y acciones que requieren aprobación humana.
Opera en modo de revisión: no modifica archivos.

## Agente `quality_guardian`

Archivo: `.codex/agents/quality_guardian.toml`

Responsabilidad: revisión de cambios y calidad del código.

Usa `regression-validator` para ejecutar unittest, compilación y el ejemplo
integrado. Clasifica fallos, riesgos y recomendaciones, y no cambia código ni
pruebas durante una revisión de solo lectura.

## Relación con las skills

Las skills se mantienen en `.agents/skills/` y se descubren desde el proyecto.
El formato oficial no requiere ni documenta un campo TOML `skills = [...]` para
activar una lista. Por eso la asociación se expresa en las instrucciones de
cada agente, que ordenan leer el `SKILL.md` correspondiente y usar sus scripts.
No se deshabilitan skills heredadas con `skills.config`, porque no es necesario
para este proyecto y limitaría capacidades no solicitadas.

## Supervisión y control humano

Los agentes pueden inspeccionar y ejecutar verificaciones locales, pero la
decisión sigue en el coordinador y en la persona responsable del proyecto.
Requiere aprobación humana:

- modificar transacciones o fixtures financieras;
- editar `config/rules.json`;
- aceptar recomendaciones como cambios de negocio;
- corregir código después de un fallo de regresión;
- publicar, enviar o compartir resultados externos.

Las instrucciones de solo lectura son una política de comportamiento; no
reemplazan permisos, sandbox ni aprobaciones de la sesión principal.

## Ejemplos de uso

Auditoría de lote:

```text
Pide a transaction_reviewer que audite
data/pruebas_ui/transacciones_mixtas.json.
Usa transaction-auditor y devuelve los errores por código,
la calidad por fuente y las recomendaciones sin modificar archivos.
```

Revisión de configuración:

```text
Pide a transaction_reviewer que revise config/rules.json,
explique A/B/C y separe errores confirmados de recomendaciones.
```

Regresión:

```text
Pide a quality_guardian que revise los cambios actuales,
ejecute regression-validator y reporte pruebas, riesgos y estado final.
```

Colaboración:

```text
Usa dos subagentes en paralelo: transaction_reviewer para datos y reglas,
quality_guardian para regresión. Espera ambos resultados y consolida solo
hallazgos verificables, indicando qué requiere revisión humana.
```

## Validación realizada

Se validó sintaxis con `tomllib` y se añadieron pruebas en
`tests/test_agent_configuration.py` para:

- `[agents].enabled` y límite de concurrencia igual a 2;
- campos obligatorios de ambos agentes;
- referencias a skills existentes;
- nombres distintos;
- ausencia de campos no permitidos para permisos, sandbox o MCP.

La validación de TOML no demuestra activación del agente. La sesión actual sí
expone herramientas de subagentes (`multi_agent_v1`) y permite delegación real,
pero la API de esta sesión no ofrece un parámetro de nombre de custom agent para
probar que un spawn concreto haya cargado estos TOML. Por eso se distingue entre
delegación real y activación automática del archivo TOML.

### Delegación real ejecutada

Se lanzaron dos subagentes en paralelo, respetando el límite de dos:

- `transaction_reviewer`: leyó su TOML y las skills de auditoría/reglas,
  ejecutó ambos scripts en modo de solo lectura y confirmó 9 procesados, 3
  válidos, 6 inválidos, seis códigos de error y reglas compatibles.
- `quality_guardian`: leyó su TOML y `regression-validator`, ejecutó el runner
  con timeout de 60 segundos y confirmó 20 pruebas OK, compilación OK y ejemplo
  integrado OK.

Esta es evidencia de delegación multiagente real en la sesión. No demuestra que
Codex haya seleccionado automáticamente los custom agents por nombre; los
subagentes recibieron una instrucción explícita de adoptar cada rol y leer su
configuración. La activación automática del TOML debe verificarse desde un
cliente Codex/CLI que descubra `.codex/agents/` y muestre el nombre del agente.

## Limitaciones

- No se configura un modelo específico porque la disponibilidad depende de la
  sesión y del cliente.
- Los agentes heredan permisos del coordinador; sus instrucciones no crean un
  entorno read-only técnico.
- La activación automática depende del cliente Codex y de la configuración
  cargada al iniciar la sesión.
- No se implementan proveedores LLM, chat de auditoría ni cambios visuales.
