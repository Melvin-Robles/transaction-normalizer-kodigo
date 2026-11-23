# Guía de interpretación

## Lectura recomendada

1. Comprueba `summary.total_processed` y la suma de válidos e inválidos.
2. Usa `quality_percent` como proporción descriptiva, no como garantía de
   corrección semántica.
3. Lee `errors_by_code` para priorizar revisión.
4. Compara `source_quality` solo cuando la fuente fue identificada.
5. Interpreta `totals_by_currency` y `success_totals_by_currency` por separado;
   nunca se suman monedas distintas.
6. Usa `diagnostics` para explicar filas mediante índice, fuente y código, sin
   reconstruir ni mostrar el JSON original.

## Límites de inferencia

- Un código identifica una validación fallida, no la causa empresarial final.
- Una fuente con pocos registros puede tener porcentajes inestables.
- Los registros `UNKNOWN` no deben atribuirse a A, B o C.
- Una tasa de validez alta no prueba que los datos sean verdaderos.
- Las recomendaciones de la herramienta son prioridades de revisión basadas en
  conteos, no correcciones automáticas.
