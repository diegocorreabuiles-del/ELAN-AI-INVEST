# ELAN Quantum v1.3.0rc1

Plataforma local de análisis cuantitativo, fundamental, noticias, riesgo, cartera, paper trading y backtesting.

## Estado recuperado en este PC

- La aplicación local se ejecuta en Python 3.12; la suite y los gates pasan en Python 3.11–3.14 sobre Linux.
- El gate local incluye 162 pruebas; Ruff, Black y el type checking crítico con mypy también pasan.
- El cierre de dependencias está verificado: 78 pins activos y `pip check` sin conflictos.
- La política Git aplica `trabajo -> develop -> main`; la PR #10 promovió `1.3.0rc1` a `main` y su CI posterior pasó en Python 3.11–3.14.
- El gate global de cobertura pasa con 81,17 %, por encima del 75 % configurado.
- AppTest recorre las doce vistas con datos deterministas y bloquea cualquier acceso a Yahoo.
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
- una selección compatible con Yahoo de índices, materias primas, divisas,
  criptoactivos y bonos;
- entrada manual para cualquier símbolo exacto aceptado por Yahoo Finance.

El catálogo de búsqueda y el proveedor de precios son capas distintas. Un
instrumento puede estar identificado correctamente aunque Yahoo no ofrezca
histórico para esa bolsa. Los mercados compatibles se traducen automáticamente,
por ejemplo BME (`.MC`), Hong Kong (`.HK`), Shanghái (`.SS`), Shenzhen (`.SZ`),
Abu Dabi (`.AD`) y Dubái (`.DU`).

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

El comparador alinea dos instrumentos, los rebasa a 100 y muestra dispersión y
correlación móvil de sus rendimientos diarios. Para estudiar EUR/USD frente al
dólar se pueden añadir `EURUSD=X` y `DX-Y.NYB`. La correlación no implica
causalidad y puede cambiar con el tiempo.

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

Pytest exige al menos 75 % de cobertura; el baseline local de esta rama es 81,17 % con 162 pruebas superadas.

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
