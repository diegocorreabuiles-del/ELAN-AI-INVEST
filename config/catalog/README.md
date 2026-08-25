# Catálogo global de instrumentos

`adanos_tickers.csv.gz` es una instantánea comprimida de
[Adanos Free Ticker Database](https://github.com/adanos-software/free-ticker-database),
publicada con licencia MIT. La copia local se descargó el 28 de julio de 2026:

- versión declarada por la fuente: `3.32.00`;
- filas del CSV original: 63.185;
- SHA-256 del CSV original:
  `50c099e755e5f57e4d5744c045f50e548f11b8960a1b24fb8e2bb81cda32d38d`;
- licencia preservada en `ADANOS_LICENSE.txt`.

La instantánea aporta acciones y ETF con ticker, nombre, bolsa, país e ISIN.
`config/instruments.csv` añade índices, materias primas, divisas y bonos, además
de 30 criptomonedas, 11 stablecoins y 13 memecoins con símbolos Yahoo y
histórico mensual comprobado el 26 de agosto de 2026. Las CBDC se excluyen
porque no son instrumentos públicos cotizados.

El catálogo sirve para descubrir instrumentos. Los precios siguen procediendo
del proveedor Yahoo configurado por la aplicación: que un valor aparezca en el
catálogo no garantiza que Yahoo publique histórico para esa plaza o símbolo.

## Actualizar

Desde la raíz del proyecto:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync_instrument_catalog.ps1
```

La actualización valida la cabecera y rechaza descargas anormalmente pequeñas
antes de reemplazar la copia local.
