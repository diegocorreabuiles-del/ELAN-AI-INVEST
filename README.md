# ELAN Quantum v1.3.0rc1

Plataforma local de análisis cuantitativo, fundamental, noticias, riesgo, cartera, paper trading y backtesting.

## Estado recuperado en este PC

- La aplicación local se ejecuta en Python 3.12; la suite y los gates pasan en Python 3.11–3.14 sobre Linux.
- El gate local incluye 192 pruebas; Ruff, Black y el type checking crítico con mypy también pasan.
- El cierre de dependencias está verificado: 78 pins activos y `pip check` sin conflictos.
- La política Git aplica `trabajo -> develop -> main`; la PR #10 promovió `1.3.0rc1` a `main` y su CI posterior pasó en Python 3.11–3.14.
- El gate global de cobertura pasa con 81,49 %, por encima del 75 % configurado.
- AppTest recorre las trece vistas con datos deterministas y bloquea cualquier acceso a Yahoo.
- El empaquetador seguro está reconstruido y cubierto por pruebas de integridad, rutas y reproducibilidad.

Este es un proyecto de simulación y paper trading. No se conecta a brokers ni opera con dinero real.

## Instalar o actualizar en Windows

```powershell
.\update.bat
```

El instalador usa `requirements.lock`, valida las versiones instaladas y ejecuta `pip check`.

## Ejecutar

```powershell
.\run.bat
```

## Buscador global de instrumentos

El espacio de trabajo permite buscar por símbolo, nombre, alias, ISIN, país y
bolsa, y filtrar por tipo de activo, país y mercado. La copia local combina:

- 63.185 acciones y ETF de 91 países procedentes de
  [Adanos Free Ticker Database](https://github.com/adanos-software/free-ticker-database),
  bajo licencia MIT;
- una selección compatible con Yahoo de índices, materias primas y bonos, más
  54 criptoactivos con histórico verificado: 30 criptomonedas, 11 stablecoins y
  13 memecoins;
- los 127 pares directos de Yahoo derivados de las 128 divisas habilitadas en
  `config/currencies.csv`; USD actúa como moneda de referencia y no crea un par
  consigo misma;
- entrada manual para cualquier símbolo exacto aceptado por Yahoo Finance.

El catálogo de búsqueda y el proveedor de precios son capas distintas. Un
instrumento puede estar identificado correctamente aunque Yahoo no ofrezca
histórico para esa bolsa. Los mercados compatibles se traducen automáticamente,
por ejemplo BME (`.MC`), Hong Kong (`.HK`), Shanghái (`.SS`), Shenzhen (`.SZ`),
Abu Dabi (`.AD`) y Dubái (`.DU`).

Los filtros `Divisa`, país y mercado `FX` consumen el mismo registro maestro que
la pestaña Divisas; no mantienen una lista Forex paralela.

Actualizar la instantánea abierta:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync_instrument_catalog.ps1
```

La procedencia, hash y licencia de la instantánea están documentados en
`config/catalog/README.md`.

## Panel principal y comparador

La primera pestaña permite seleccionar cualquier instrumento del universo activo
y estudiar su histórico con cuatro vistas:

- velas OHLC;
- línea de cierres;
- rentabilidad acumulada del periodo;
- volumen negociado cuando Yahoo lo publica.

El horizonte del gráfico es independiente del análisis general y admite desde un
mes hasta el máximo histórico disponible. El panel muestra último cierre,
rentabilidad del periodo, máximo, mínimo, distancia al máximo y volatilidad
anualizada.

El comparador permite seleccionar entre dos y ocho instrumentos, los alinea en
sesiones comunes, los rebasa a 100 y muestra una matriz de correlaciones. Dentro
del grupo se elige un par focal para la dispersión y la correlación móvil. Para
estudiar EUR/USD frente al dólar se pueden añadir `EURUSD=X` y `DX-Y.NYB`. La
correlación no implica causalidad y puede cambiar con el tiempo.

## Motor FX

La pestaña **Divisas** usa un catálogo maestro de 155 monedas ISO 4217 activas.
La instantánea actual habilita las 128 que tienen al menos dos sesiones
utilizables en Yahoo y construye 16.256 pares virtuales con identificadores
`FX_BASE_QUOTE`. Permite buscar por código, nombre, país o par, invertir la
orientación, consultar histórico y KPIs y conocer si la serie procede de un
dato directo, inverso o sintético.
Los cruces virtuales también se pueden buscar desde el selector principal
escribiendo, por ejemplo, `EUR/GBP` o `NGN/XOF`. Una vez añadidos al universo,
participan en precios, calidad, ranking, riesgo, gráficos y correlaciones. Se
mantienen como instrumentos de solo lectura: PER y fundamentales aparecen como
`N/D`, y quedan excluidos de la cartera propuesta y de paper trading.



El routing prioriza directo, inverso y rutas cortas mediante USD/EUR, sin
almacenar todas las combinaciones. El comparador admite pares FX junto con
acciones, índices, materias primas y criptomonedas. Las correlaciones usan log
returns alineados por combinación y muestran observaciones, cobertura y fechas;
no hay forward-fill, interpolación ni retornos cero inventados. Consulta el
[contrato del motor FX](docs/fx_engine.md).

## Espacio de trabajo conectado

Mercado, Inteligencia, Fundamental, Noticias y Ranking comparten un único activo
activo. Antes de los KPI aparece un selector buscable que explica que el activo
procede del `Universo activo`; cambiarlo actualiza el contexto del resto. La barra
superior resume precio, PER histórico, score, señal y volatilidad disponibles. Las
tablas de Inteligencia y Ranking permiten activar un instrumento seleccionando
una fila.

La lista de `Universo activo` se guarda automáticamente en la base SQLite local y
se restaura al recargar la página o reiniciar la aplicación. `config/watchlist.csv`
solo actúa como valor inicial cuando todavía no existe una preferencia guardada.

Los controles locales del gráfico histórico y del comparador usan fragmentos de
Streamlit para actualizar solo su panel. Las trece vistas usan una navegación
superior compacta y conservan su carga perezosa: solo la vista seleccionada
consulta proveedores, sin alterar scoring, señales, riesgo, cartera o paper
trading.

El filtro `Criptoactivos (todos)` reúne `Crypto`, `Stablecoin` y `Memecoin` sin
perder sus filtros especializados. La Terminal de Decisión aplica modelos
separados: crypto muestra mercado/liquidez y fuerza frente a BTC; meme coins
priorizan momentum, volumen y una advertencia especulativa; stablecoins evalúan
peg y riesgo de depeg sin emitir una señal direccional ni plan tradicional. El PER
y demás métricas corporativas no se aplican a estos activos. Las CBDC no se
presentan como instrumentos de mercado: son pasivos de bancos centrales y no
tienen un ticker público negociable en Yahoo.

Funding, derivados, on-chain, DEX, holders, supply, reservas y riesgo del emisor se
muestran como `N/D` mientras no exista una fuente verificable. Consulta el
[inventario de fuentes y fallbacks](docs/decision_terminal_data_sources.md).

## Noticias y eventos

La pestaña **Noticias y eventos** consulta bajo demanda hasta diez noticias recientes y el
calendario corporativo del activo visible. Muestra próximas fechas de resultados, dividendo y
ex-dividendo cuando Yahoo Finance las publica. La consulta se cachea durante 15 minutos, con un
máximo de 50 entradas, y puede desactivarse o ajustarse mediante `news.*` en
`config/settings.yaml`.

Esta información es contextual y de solo lectura: no modifica puntuaciones, señales, riesgo,
carteras ni operaciones paper. Los fallos de noticias y calendario se aíslan entre sí y la UI
presenta un estado neutro sin exponer detalles técnicos.

## Calidad de Market Data

Cada análisis adjunta un reporte aditivo de calidad por instrumento. El panel
Mercado muestra proveedor, estado global, cobertura media, incidencias,
procedencia (`Proveedor` o `Caché local`), última sesión y posibles huecos.

Los estados distinguen historiales saludables, degradados, obsoletos,
insuficientes y no disponibles. La frescura tolera hasta cinco días naturales y
la cobertura usa sesiones laborables esperadas con un umbral del 95 %. Es una
heurística operativa, no un calendario oficial de cada bolsa. El diagnóstico no
rellena precios ni modifica las series usadas por scoring, riesgo o comparación.

## Verificación local

Suite funcional, sin el umbral global de cobertura:

```powershell
.\.venv\Scripts\python.exe -m pytest -o addopts="-q"
```

Gate completo configurado por el proyecto:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Calidad estática reproducida también por CI:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m black --check . --fast
.\.venv\Scripts\python.exe -m mypy
```

Pytest exige al menos 75 % de cobertura; el baseline local de esta rama es 81,49 % con 192 pruebas superadas.

## Matriz Python 3.11–3.14

Con Docker Desktop iniciado, este comando reproduce en contenedores Linux los mismos gates de CI. La fuente se monta en solo lectura y cada versión trabaja sobre un clon temporal limpio de `HEAD`.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_ci_matrix.ps1
```

## Dependencias reproducibles

`pyproject.toml` define las dependencias directas y `requirements.lock` fija el cierre transitivo para Python 3.11–3.14.

```powershell
.\.venv\Scripts\python.exe scripts\check_lock.py
.\.venv\Scripts\python.exe -m pip check
```

NumPy usa 2.2.6 en Python 3.11 y 2.5.1 en Python 3.12–3.14.

## Crear y verificar una distribución

El constructor exige un working tree limpio y lee exclusivamente los blobs del commit `HEAD`.

```powershell
.\.venv\Scripts\python.exe scripts\build_distribution.py --output dist\elan-quantum-1.3.0rc1.zip
.\.venv\Scripts\python.exe scripts\build_distribution.py --verify dist\elan-quantum-1.3.0rc1.zip
```

El ZIP contiene una sola raíz, `data/` y `logs/` vacíos y un manifiesto SHA-256. El gate bloquea bases de datos, logs, ejecutables, credenciales, enlaces simbólicos, rutas no portables y cualquier contenido no confirmado en Git.

## Desarrollo e integración

La política canónica está en `GIT_WORKFLOW.md`. Las ramas de trabajo y recuperación entran primero en `develop`; solo `develop` puede integrarse en `main`.

```powershell
.\.venv\Scripts\python.exe scripts\check_git_flow.py
```

`develop` y `main` están protegidas en GitHub: PR, matriz CI, rama actualizada, conversaciones resueltas e historial lineal son obligatorios; force-push y borrado están bloqueados. El bypass administrativo se conserva solo para recuperación.

## Siguiente paso de release

`1.3.0rc1` está validada en `main` y el tag anotado `v1.3.0-rc.1` apunta a `5cf2bca`. Publicar una GitHub Release o desplegar requieren autorizaciones explícitas independientes.

ELAN Quantum es una herramienta educativa y de simulación. No constituye asesoramiento financiero ni garantiza resultados.
