# Motor FX

## Alcance

El motor FX es un subsistema de análisis de solo lectura. No crea órdenes, no
participa en paper trading ni entra en la construcción de cartera. Los pares
virtuales sí pueden formar parte del universo analítico común: alimentan precios,
calidad, ranking, riesgo, gráficos, correlaciones y la Terminal de Decisión. Sus
resultados son informativos y nunca habilitan ejecución; los fundamentales
corporativos y el PER se muestran como `N/D`.

## Catálogo maestro

`config/currencies.csv` contiene una fila por moneda, no por cruce. El registro
incluye código ISO, nombre, símbolo visual, región, país, precisión, estado,
proveedor, símbolo y orientación del proveedor y fecha de actualización.

Los pares son virtuales y usan:

- identificador: `FX_BASE_QUOTE`;
- visualización: `BASE/QUOTE`;
- significado: unidades de `QUOTE` necesarias para comprar una unidad de
  `BASE`.

El buscador genera dinámicamente las combinaciones a partir de las monedas
habilitadas. La instantánea del 22 de agosto de 2026 contiene 155 monedas ISO
4217 activas: 128 con histórico mínimo utilizable en Yahoo y 27 deshabilitadas
de forma explícita. Los 16.256 pares dirigidos posibles se generan bajo demanda;
no se almacenan ni se duplican sus históricos.

La disponibilidad exige al menos dos cierres diarios durante el último mes. Un
ticker existente con una sola observación no se habilita. Esto acredita una
serie analizable, pero no garantiza libre convertibilidad, liquidez institucional
ni acceso minorista a la negociación.

El catálogo se puede volver a contrastar con la lista oficial ISO de SIX y
Yahoo desde la raíz del repositorio:

```powershell
python .\scripts\sync_currency_catalog.py --output .\config\currencies.csv
```

El script conserva los metadatos curados existentes, agrega nuevas monedas,
prueba símbolos Yahoo y deja como `enabled=false` las series no utilizables. La
escritura es atómica y se cancela si Yahoo devuelve menos de 100 monedas, para
evitar degradar el catálogo durante una caída transitoria del proveedor.

## Integración con el motor principal

El buscador global reemplaza sus filas Forex heredadas por instrumentos derivados
del mismo `config/currencies.csv`. Expone los 127 símbolos de proveedor asociados
a las 128 monedas habilitadas, con tipo `Forex`, mercado `FX` y el país o zona del
registro. USD es el pivote del routing y no aparece como un par consigo misma.
Los filtros de tipo, país, mercado y texto usan por tanto la misma fuente que la
pestaña Divisas, sin duplicar un segundo catálogo. Cuando el texto identifica un
cruce, el buscador añade bajo demanda cualquiera de los 16.256 identificadores
virtuales; por ejemplo, `NGN/XOF` resuelve a `FX_NGN_XOF`.

`FxAwareMarketDataProvider` separa símbolos Yahoo y pares `FX_BASE_QUOTE`. Los
primeros conservan el adaptador Yahoo y los segundos se resuelven mediante
`HistoricalFxService`; después normaliza sus índices y entrega una matriz de
cierres común al `CoreEngine`. Un fallo FX queda aislado por instrumento y no
elimina las series ordinarias disponibles.

## Resolución y routing

`HistoricalFxService` aplica esta prioridad:

1. par directo del proveedor;
2. par inverso, transformado matemáticamente;
3. ruta registrada más corta, con preferencia por USD y EUR;
4. máximo dos monedas intermediarias;
5. `N/D` si ninguna ruta completa dispone de datos.

Cada resultado conserva `base`, `quote`, `source_type`, proveedor, ruta de
cálculo, último timestamp de mercado y timestamp UTC de recepción. Los tipos de
origen son `DIRECT`, `INVERSE` y `SYNTHETIC`.

Al invertir OHLC se aplica:

- `open = 1 / open`;
- `high = 1 / low`;
- `low = 1 / high`;
- `close = 1 / close`.

Los cruces sintéticos multiplican las tasas orientadas de cada tramo. Ejemplo:
`EUR/COP = EUR/USD × USD/COP`. `MXN/COP` se resuelve como
`(1 / USD/MXN) × USD/COP`.

## Históricos y caché

Yahoo/yfinance es el único proveedor configurado. El adaptador prueba el par
directo y el inverso; después utiliza los símbolos ancla definidos en el
registro. No existen credenciales ni fallback de pago.

Los históricos OHLC se guardan como CSV inerte mediante `MarketCache`, con la
misma clave SHA-256 y TTL configurado para mercado. Streamlit añade una caché de
15 minutos a la resolución completa. La infraestructura actual de Yahoo basada
en `period` no permite todavía descargar únicamente un intervalo faltante; al
expirar el TTL se recarga el periodo solicitado completo.

Las series se normalizan a UTC, eliminan timestamps inválidos y duplicados y
rechazan precios no positivos o no finitos. Los cruces sintéticos usan `inner
join`; no hay forward-fill, interpolación ni mezcla silenciosa de fechas.
El comparador multiactivo normaliza igualmente a UTC las series externas antes
de concatenarlas con FX.

## Correlaciones

Las correlaciones se calculan sobre log returns de cierres positivos:

`r[t] = ln(close[t] / close[t-1])`.

Cada combinación se alinea por separado para evitar que un tercer activo reduzca
innecesariamente la muestra. Se reportan correlación, observaciones, cobertura,
fecha inicial y fecha final. Los periodos disponibles son 30D, 90D, 180D, 1Y,
3Y y 5Y; las ventanas rolling son 20, 60, 120 y 252 sesiones.

## Calidad

Los controles detectan cotizaciones no positivas/no finitas, saltos diarios por
encima del umbral, datos antiguos y cobertura inferior al 95 %. Las funciones de
consistencia verifican que un par y su inverso multipliquen aproximadamente uno
y que un directo sea coherente con su cruce triangular sintético.

La calidad es metadata: nunca rellena ni altera precios.

El adaptador compuesto del motor principal conserva además, por instrumento FX,
el tipo de resolución, el proveedor de los tramos, la ruta de cálculo, la
cobertura propia de la ruta sintética y el instante de recepción. Mercado
presenta esta procedencia junto con la cobertura temporal, la última sesión y
su antigüedad. Los campos son metadata opcional: los proveedores no FX conservan
su contrato y ninguna de estas medidas modifica precios, scoring o decisiones.

## Almacenamiento

No se añadieron tablas SQLite ni cambios Supabase. SQLite continúa reservado a
`analysis_history` y `workspace_preferences`; los datos FX reutilizan el catálogo
versionado y la caché de mercado. Si en el futuro se requiere histórico
incremental permanente, debe diseñarse una migración aditiva independiente.

## Limitaciones conocidas

- La disponibilidad real depende de Yahoo y puede variar por moneda y periodo.
- El registro ISO incluye monedas restringidas o no libremente convertibles;
  aparecer en el catálogo no demuestra que sean negociables en un broker.
- No hay proveedor secundario; una ruta incompleta falla cerrada como `N/D`.
- Los máximos y mínimos OHLC sintéticos combinan extremos diarios de los tramos;
  son envolventes conservadoras, no cotizaciones intradía simultáneas.
- La validación triangular está implementada y probada, pero comparar
  automáticamente todos los directos contra sintéticos en cada carga se reserva
  para una tarea posterior para no duplicar consultas al proveedor.
