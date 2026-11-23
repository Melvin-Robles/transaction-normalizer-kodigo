# Guía de regresiones

Interpreta los resultados en este orden:

1. `unittest`: comportamiento de casos unitarios y de integración.
2. `compileall`: errores sintácticos o módulos no compilables.
3. `integrated_example`: contrato de aceptación del ejemplo original.

Si falla `unittest`, conserva el texto de salida y corrige el código antes de
considerar cambios en pruebas. Si falla el ejemplo, compara primero las
cantidades y totales por moneda; no sustituyas el contrato por una expectativa
nueva sin documentar una decisión de negocio.
