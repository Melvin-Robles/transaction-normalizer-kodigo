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
