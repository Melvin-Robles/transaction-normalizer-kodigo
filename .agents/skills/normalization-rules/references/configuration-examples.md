# Ejemplos de revisión

## Configuración válida

La configuración actual es válida cuando `validate_rules.py` devuelve código 0
y reporta adaptadores `SourceAAdapter`, `SourceBAdapter` y `SourceCAdapter`.

```powershell
python .agents/skills/normalization-rules/scripts/validate_rules.py --rules config/rules.json
```

## Configuración inválida

Un archivo JSON que elimina `policies` debe producir un fallo controlado de
carga. La skill debe reportar el error y no crear una versión corregida:

```json
{}
```

Una fuente con `amount_style` desconocido debe aparecer como error de
compatibilidad, separada de recomendaciones como `allow_extra_fields`.
