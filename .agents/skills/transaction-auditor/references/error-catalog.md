# Catálogo de diagnósticos

Los códigos son producidos por el normalizador y se cuentan sin alterar los
registros de entrada. El índice es cero-based internamente; la UI lo muestra
como número de fila humano.

| Código | Interpretación |
|---|---|
| `INVALID_RECORD_TYPE` | La fila no es un objeto JSON. |
| `UNKNOWN_SOURCE` | No contiene un discriminador configurado. |
| `AMBIGUOUS_SOURCE` | Contiene más de un discriminador. |
| `SOURCE_CONFLICT` | `source` contradice la fuente detectada. |
| `MISSING_FIELD` | Falta un campo obligatorio. |
| `INVALID_ID` | El identificador no cumple el tipo o límite configurado. |
| `INVALID_AMOUNT` | El importe viola formato, precisión, positividad o límite. |
| `UNSUPPORTED_CURRENCY` | La moneda no aparece en `rules.json`. |
| `CURRENCY_MISMATCH` | El símbolo y la moneda declarada se contradicen. |
| `INVALID_TIMESTAMP` | La fecha no cumple el formato o zona horaria requerida. |
| `UNKNOWN_STATUS` | El estado no está en el mapa de la fuente. |
| `DUPLICATE_TRANSACTION` | Ya existe una fila válida con la misma pareja `(source, id)`. |

Un error de documento, como JSON corrupto o superar límites, no es un
diagnóstico por fila: se reporta como fallo controlado de ingestión.
