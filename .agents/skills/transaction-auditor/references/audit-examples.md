# Ejemplos reproducibles

Desde la raíz del repositorio:

```powershell
python .agents/skills/transaction-auditor/scripts/audit_batch.py data/transacciones_ejemplo.json
```

El ejemplo integrado debe producir un resumen equivalente a:

```json
{
  "invalid_count": 0,
  "quality_percent": 100.0,
  "total_processed": 3,
  "valid_count": 3
}
```

Y sus totales válidos deben ser `USD: 201.00` y `EUR: 99.99`.

Para un lote mixto:

```powershell
python .agents/skills/transaction-auditor/scripts/audit_batch.py data/pruebas_ui/transacciones_mixtas.json
```

El resultado esperado es 9 procesados, 3 válidos y 6 inválidos. Los detalles
de los códigos se obtienen del JSON generado, no se asumen desde el nombre del
archivo.
