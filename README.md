# Normalizador de transacciones

Aplicación local en Python 3.11+ y Streamlit para cargar JSON heterogéneo de las fuentes A, B y C, validar cada registro, normalizar los válidos y mostrar diagnósticos de los inválidos.

## Requisitos

- Windows, macOS o Linux.
- Python 3.11 o superior.
- Acceso a Internet únicamente durante la instalación de dependencias.
- No se necesita cuenta, base de datos ni servicio externo para usar la aplicación.

## Instalación desde cero

Abra PowerShell o una terminal y ejecute los comandos desde la carpeta raíz del repositorio, la que contiene `app.py`:

```powershell
cd C:\Users\melvi\Documents\GitHub\transaction-normalizer-kodigo
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si PowerShell impide activar el entorno virtual, ejecute una vez en esa misma ventana:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

En otra plataforma, active el entorno con `source .venv/bin/activate` y use los mismos comandos de instalación.

## Ejecutar las pruebas

Con el entorno virtual activo:

```powershell
python -m pytest -q
```

La suite verifica las tres fuentes, importes y fechas, errores de lectura, límites, duplicados, filtros de validación, configuración modificada y exportaciones. El resultado verificado de esta entrega es **42 passed**.

## Iniciar la aplicación

```powershell
python -m streamlit run app.py
```

Streamlit mostrará una dirección local, normalmente `http://localhost:8501`. Abra esa dirección en el navegador. Para detener el servidor, vuelva a la terminal y presione `Ctrl+C`.

## Guion de prueba para el docente

1. Al abrir la aplicación, deje seleccionada **Datos de ejemplo**. Deben aparecer 3 transacciones válidas, 0 inválidas, USD 201.00 y EUR 99.99.
2. Abra **Registros inválidos** y confirme que la tabla está vacía para el ejemplo.
3. Seleccione **Cargar archivo JSON** y cargue `data/transacciones_casos_borde.json`. Deben procesarse 43 filas, con 13 válidas y 30 diagnósticos.
4. En **Transacciones válidas**, pruebe filtros combinados de estado, moneda, fuente, fecha y búsqueda parcial de ID. El contador y la tabla deben cambiar.
5. Use **Descargar vista filtrada** y compruebe que el JSON contiene exactamente las filas visibles, seis campos y `amount` como número.
6. En **Registros inválidos**, filtre por código y descargue los diagnósticos. Deben incluir índice, fuente, código y motivo, sin volcar el registro original.
7. En **Reglas activas**, revise los mapas de estado, formatos, monedas y límites leídos desde `config/rules.json`.
8. Pruebe también `data/entrada_malformada.json`: debe aparecer un mensaje controlado y la pantalla debe seguir disponible para seleccionar otro archivo.

## Estructura

- `app.py`: interfaz Streamlit; no contiene lógica de parsing monetario.
- `src/transaction_normalizer/config.py`: carga y validación de reglas.
- `src/transaction_normalizer/ingest.py`: límites y lectura JSON segura.
- `src/transaction_normalizer/normalizer.py`: detección de fuente, validación y normalización con `Decimal`.
- `src/transaction_normalizer/metrics.py`: conteos y sumas por moneda.
- `src/transaction_normalizer/exports.py`: JSON de seis campos y diagnósticos.
- `config/rules.json`: fuente de verdad de mapas, formatos, monedas y políticas.
- `data/`: fixtures de demostración y casos adversariales.
- `tests/`: suite pytest y expectativas de los casos adversariales.

## Reglas principales adoptadas

Para esta entrega se adoptan las siguientes decisiones de negocio:

- El esquema contiene exactamente `id`, `amount`, `currency`, `timestamp`, `status` y `source`.
- Se admiten USD y EUR; no se realizan conversiones ni se mezclan sumas entre divisas.
- A usa unidades mayores, B usa unidades menores (céntimos) y C exige símbolo `€` con coma decimal.
- Se rechazan cero, negativos, más de dos decimales, importes ambiguos y valores mayores que 1.000.000.000,00.
- Los estados se mapean por fuente desde `config/rules.json`.
- Las fechas sin zona de A/B se interpretan como UTC; los offsets de C se convierten a UTC.
- Los registros incompletos o inconsistentes se separan como inválidos y el lote continúa.
- Solo la primera ocurrencia válida de `(source, id)` se admite.
- Se permiten campos extra no conflictivos y se rechazan discriminadores ambiguos o un `source` contradictorio.
- Las sumas de todos los válidos y de los válidos `SUCCESS` se mantienen separadas por moneda.
- Se aplican límites de 5 MiB, 10.000 registros e identificadores de máximo 128 caracteres.
- La aplicación no persiste archivos subidos ni ejecuta contenido del JSON.

El importe B se interpreta como unidades menores, C exige el símbolo `€`, las fechas se exportan en UTC y las divisas nunca se suman entre sí. Los mapas de estados y monedas se obtienen de `config/rules.json`.

## Datos de prueba

- `transacciones_ejemplo.json`: tres registros del enunciado, todos válidos.
- `transacciones_casos_borde.json`: casos válidos, incompletos, ambiguos, duplicados y adversariales.
- `entrada_malformada.json`: JSON con error de sintaxis intencional.
- `raiz_invalida.json`: documento JSON con raíz no admitida.
- `transacciones_vacias.json`: arreglo vacío.
- `contenedor_transacciones.json`: objeto admitido con `transactions` como arreglo.

El contenido de estos archivos es solamente información de prueba; nunca se ejecutan textos incluidos en los registros.

## Nota técnica resumida

La solución está separada en capas de configuración, ingestión, normalización, métricas, exportación e interfaz. Usa `Decimal` para importes, valida cada fila sin detener el lote, exporta JSON seguro y mantiene los uploads únicamente en memoria.

Se utilizó Codex para apoyar la lectura del contrato, la implementación, las pruebas y la documentación. Las decisiones de negocio anteriores fueron adoptadas para esta entrega y están reflejadas en `config/rules.json`.

Verificación realizada: `python -m pytest -q` terminó con **42 passed**; `python -m compileall -q src app.py` terminó correctamente. No hay autenticación, persistencia, servicios remotos ni pruebas automatizadas de navegador.

## Limitaciones conocidas

La aplicación es local, no autentica usuarios, no persiste cargas, no usa servicios remotos y no incluye paginación ni pruebas automatizadas de navegador. El límite contractual de 10.000 registros mantiene el procesamiento en memoria acotado.

