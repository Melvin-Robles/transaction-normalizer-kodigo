# Contratos funcionales

- Las fuentes A, B y C se detectan por sus discriminadores configurados.
- El esquema válido contiene `id`, `amount`, `currency`, `timestamp`, `status`
  y `source`.
- Los importes se procesan con `Decimal`.
- Las fechas se exportan en UTC.
- Los duplicados se identifican por `(source, id)`.
- Un registro inválido no cancela el lote.
- Las métricas monetarias permanecen separadas por moneda.
- Las exportaciones JSON conservan el esquema y no exponen cargas inválidas.
