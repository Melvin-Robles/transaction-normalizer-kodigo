# Esquema normalizado

Cada registro válido contiene exactamente:

```json
{
  "id": "string",
  "amount": 100.50,
  "currency": "USD",
  "timestamp": "2025-03-10T14:22:00Z",
  "status": "SUCCESS",
  "source": "A"
}
```

`amount` es `Decimal` dentro del motor y número JSON al exportar. `timestamp`
se expresa en UTC. No se combinan totales de monedas distintas.
