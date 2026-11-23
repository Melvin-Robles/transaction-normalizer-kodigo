# Validación de Agent Skills personalizadas

Fecha: 2026-11-22

## Introducción

La FASE 3 añade tres skills locales en `.agents/skills/` para tareas distintas:

1. `transaction-auditor` analiza lotes y produce reportes seguros.
2. `normalization-rules` revisa la configuración y la compatibilidad de fuentes.
3. `regression-validator` ejecuta verificaciones de código y contrato.

Se mantuvo la separación de responsabilidades de la FASE 2. Ninguna skill
usa un proveedor LLM, modifica transacciones automáticamente o reemplaza la
validación determinista del motor.

## Estructura

```text
.agents/skills/
├── transaction-auditor/
│   ├── SKILL.md
│   ├── scripts/audit_batch.py
│   └── references/
├── normalization-rules/
│   ├── SKILL.md
│   ├── scripts/validate_rules.py
│   └── references/
└── regression-validator/
    ├── SKILL.md
    ├── scripts/run_regression.py
    └── references/
```

Los `SKILL.md` tienen frontmatter YAML con `name` y `description`, nombres en
minúsculas con guiones y descripciones diferenciadas. Las pruebas locales
verifican esta estructura sin agregar dependencias al proyecto.

## Responsabilidades y reutilización

### `transaction-auditor`

Reutiliza `TransactionProcessingService`, `rules.json` y los modelos existentes.
Reporta conteos, calidad, códigos de error, distribución por fuente/moneda,
totales separados y recomendaciones basadas en datos. No incluye registros
originales completos.

### `normalization-rules`

Reutiliza `load_rules`, `build_source_registry` y
`SUPPORTED_AMOUNT_STYLES`. Comprueba la estructura real, adaptadores,
discriminadores, estilos monetarios, estados y límites. Separa errores
confirmados de recomendaciones y nunca escribe `rules.json`.

### `regression-validator`

Usa `subprocess.run` con argumentos controlados, `shell=False`, timeout y
captura de salida limitada. Ejecuta `unittest`, `compileall` y el ejemplo real a
través de `TransactionProcessingService`.

## Ejemplos reproducibles

Desde la raíz del proyecto:

```powershell
python .agents/skills/transaction-auditor/scripts/audit_batch.py data/transacciones_ejemplo.json
python .agents/skills/transaction-auditor/scripts/audit_batch.py data/pruebas_ui/transacciones_mixtas.json
python .agents/skills/normalization-rules/scripts/validate_rules.py --rules config/rules.json
python .agents/skills/regression-validator/scripts/run_regression.py
```

Resultados observados durante esta fase:

- Auditoría del ejemplo: 3 procesados, 3 válidos, 0 inválidos, calidad 100%,
  USD 201.00 y EUR 99.99.
- Auditoría del lote mixto: 9 procesados, 3 válidos, 6 inválidos.
- Validación de reglas: configuración válida, fuentes A/B/C con sus adaptadores.
- Regresión acotada: unittest, compileall y ejemplo integrado correctos.

## Pruebas automatizadas

Se añadió `tests/test_skills.py`. Comprueba:

- Metadatos y recursos de las tres skills.
- Salidas reproducibles de auditoría.
- Errores controlados con JSON malformado y reglas inválidas.
- Códigos de salida.
- No modificación de los archivos de entrada.
- Ejecución del runner de regresión.

Resultado final de la suite de esta fase:

```text
17 pruebas ejecutadas
17 OK
```

También se ejecutó:

```powershell
python -m compileall -q app.py src tests .agents/skills
```

## Validación de activación

Se validó la estructura, los scripts y sus escenarios mediante ejecución
manual y pruebas automatizadas. Eso demuestra que las herramientas funcionan,
pero no equivale a observar que Codex haya activado automáticamente cada skill.
La activación real depende del selector de skills del entorno y no se afirma
como evidencia en esta fase.

El validador auxiliar de `skill-creator` se intentó ejecutar, pero el entorno no
tenía instalado el módulo opcional `PyYAML`. Por eso se usó la validación local
de frontmatter incluida en `tests/test_skills.py`; no se añadió PyYAML a las
dependencias del proyecto.

## Restricciones y limitaciones

- Las skills son locales al repositorio y no se han instalado como skills
  globales del usuario.
- La FASE 5 añadió un agente Python de auditoría, pero no lo conecta todavía a
  Streamlit ni activa un proveedor LLM por defecto.
- La auditoría no determina causas empresariales; solo resume diagnósticos del
  normalizador.
- La revisión de reglas no aplica recomendaciones automáticamente.
- El runner de regresión comprueba el arranque lógico y el contrato, pero no
  sustituye una prueba visual completa de la interfaz Streamlit.
- No se modificó `NOTA_TECNICA.docx`.
