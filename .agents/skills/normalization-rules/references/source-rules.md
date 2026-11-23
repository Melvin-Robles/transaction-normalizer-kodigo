# Reglas actuales por fuente

| Fuente | Discriminador | Importe | Fecha | Estados de entrada |
|---|---|---|---|---|
| A | `id` | Unidades principales con punto | `%Y-%m-%d %H:%M:%S`, UTC implícito | `completed`, `failed`, `pending` |
| B | `transaction_id` | Unidades menores enteras | `%d/%m/%Y %H:%M`, UTC implícito | `ok`, `error`, `waiting` |
| C | `ref` | Símbolo `€` y coma decimal | ISO 8601 con zona obligatoria | `success`, `failure`, `processing` |

Los estados se transforman respectivamente a `SUCCESS`, `FAILED` y `PENDING`.
Las monedas configuradas son USD y EUR. La fuente C puede cruzar campos de
moneda opcionales y exige coherencia con el símbolo euro.
