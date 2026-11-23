# Casos límite

La regresión debe cubrir, como mínimo:

- JSON vacío, corrupto o con raíz no soportada.
- Registros `null`, strings, listas o fuentes desconocidas.
- Campos obligatorios ausentes.
- Fuentes ambiguas o campo `source` contradictorio.
- Importes negativos, cero, demasiado precisos, booleanos o fuera de límite.
- Céntimos de B, decimal de A y euro con coma de C.
- Monedas no soportadas y símbolos contradictorios.
- Fechas imposibles, sin zona horaria o con offset convertido a UTC.
- Estados no configurados y estados con espacios/mayúsculas.
- Duplicados dentro de una fuente y mismo ID entre fuentes distintas.
- Archivos por encima de los límites de bytes o registros.
