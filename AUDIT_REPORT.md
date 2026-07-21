# Auditoría integral de ELAN Quantum

> **Corrección de estado tras la migración (22 de julio de 2026).** El PR #1 se integró mediante rebase en `develop` (`913ee99`) y su matriz posterior al merge pasó en Python 3.11–3.14; `main` permanece intacta. Esta rama de mantenimiento actualiza las Actions oficiales a `checkout@v7` y `setup-python@v7`, ambas con Node 24. No se ha realizado merge a `main`, tag, release ni despliegue.

> Actualización v1.2.2 Core Cleanup (18 de julio de 2026): la sección siguiente reemplaza el estado operativo del baseline; el resto del documento se conserva como evidencia “antes”.

## Estado después de la Fase 1

La rama local `feature/core-cleanup` parte del commit de respaldo `aca57e7`. El P0 financiero se corrigió en `5f0155c`, la consolidación inicial del core en `5467600`, la integridad del backtest en `fa5de16` y la atomicidad de paper trading en `71bcfe4`. No se hizo push, merge ni tag.

| Hallazgo del baseline | Antes | Después v1.2.2 |
|---|---|---|
| TD-001 Ruff | Fallaba | Pasa en todo el árbol |
| TD-002 Black | Rechazaba 36 archivos | Pasa en 117 archivos |
| TD-003 `max_weight` | Podía incumplirse silenciosamente | Cap garantizado o error de inviabilidad explícito; regresión parametrizada |
| TD-004 trazabilidad Git | Trabajo mezclado y no consolidado | Baseline preservado y commits temáticos locales |
| TD-005/006 Portfolio | Colisión `portfolio.py`/`portfolio/` | Una API canónica en `portfolio.engine`; anterior preservada en `legacy/` |
| TD-007 pipeline | Dos pipelines sin autoridad clara | `CoreEngine` canónico; `InvestmentPipeline` congelado como legacy con compatibilidad temporal |
| TD-008 backtest | UI y paquete usaban rutas distintas | UI y adaptadores delegan en `BacktestEngine` |
| TD-009 integridad del backtest | Sin costes, slippage, benchmark real ni prueba anti-look-ahead | Costes por turnover, benchmark configurado y ejecución desplazada una barra, con regresiones |
| TD-011 cliente de mercado | Sin timeout, reintentos ni caché persistente activa | Timeout y retry/backoff configurables; caché CSV con TTL, clave hash y escritura atómica; seis regresiones sin red |
| TD-012 configuración | Valores relevantes ignorados | Mercado, cartera, backtest y flag de paper conectados |
| TD-013 ciclo paper | Stop-loss y snapshots no se llamaban desde la app | Control manual confirmado; validación fail-closed, venta por stop y snapshot posterior atómicos; trazabilidad visible |
| TD-014 atomicidad paper | Lecturas previas a escrituras permitían saldo negativo, sobreventa y cambios parciales | `BEGIN IMMEDIATE`, updates condicionados, WAL, timeout y rollback; una cuenta ausente ya no permite confirmar venta o reset parcial |
| TD-016 reproducibilidad | Rangos abiertos y ninguna resolución registrada | `requirements.lock` fija 73 dependencias activas; requirements, scripts y CI usan el mismo archivo y verifican cierre/versiones |
| TD-017 distribución | ZIP histórico de 553.098.970 bytes con 12.667 entradas, incluidas `.git`, `.venv`, logs y bases | Empaquetador desde `HEAD`, exclusiones bloqueantes, carpetas de estado vacías, manifiesto SHA-256 y verificación automática en CI |
| TD-018 pruebas/cobertura | Sin medición y sin AppTest del flujo principal | 96 pruebas; cobertura de líneas y ramas 77,5 %, gate 75 % y AppTest sin red de `app.py` y todas las vistas |
| TD-019 ramas | `main` en 0.1 y ninguna ruta de integración exigible | Gate y política `trabajo → develop → main`; feature lineal, consolidada y 19 commits por delante de `develop`, sin push ni merge |
| TD-022 caché pickle | `read_pickle` aceptaba objetos ejecutables | Sustituido por CSV inerte; los `.pkl` antiguos no se leen |
| TD-024 Streamlit | API de ancho obsoleta | Reemplazada; pestañas costosas condicionales y cachés acotadas |
| TD-025 tema Streamlit | Colores sin identidad nativa y CSS como única personalización | Tema nativo versionado con navy `#141654`, oro `#D8B511` y paleta común de gráficos; el CSS restante solo ajusta espaciado/tamaño |
| TD-028/029 CI/EOL | Sin Python 3.14 ni política EOL | Matriz 3.11–3.14 y `.gitattributes` |

El inventario canónico y el flujo actualizado están en `ELAN_ARCHITECTURE.md`. Se preservan 85 submódulos importables, incluidos los adaptadores y módulos legacy; el import-all de esta rama termina con 0 fallos.

### Resultado de validación de esta rama

- `pytest`: 108 pruebas; incluye timeout, retry/backoff, caché segura, configuración efectiva, paper trading, distribución, AppTest integral y política Git.
- Cobertura: 77,5 % combinando líneas y ramas sobre `app.py` y todo `elan_ai_invest`; pytest falla por debajo de 75 %.
- `ruff check .`: correcto.
- `black --check .`: correcto.
- `python scripts/healthcheck.py`: correcto, versión 1.2.2.
- Import-all: 85 submódulos, 0 fallos.
- Dependencias: `check_lock.py` verifica 75 dependencias activas en Python 3.14; `pip check` pasa. NumPy 2.4.6 está publicado para Python 3.11 en Windows y Linux; la ejecución remota de toda la matriz queda pendiente hasta un futuro push.
- Streamlit temporal: `/_stcore/health` devuelve HTTP 200 y `ok`; navegador verificado con fondo `rgb(20, 22, 84)`, texto `rgb(216, 181, 17)`, sidebar, controles, tabla y gráficos renderizados.

La copia activa se trasladó a `C:\Users\elanv\Desktop\ELAN AI INVESTMENT`. Su `.venv` ya resuelve esa misma ruta; las validaciones siguen fijando `PYTHONPATH=src` para hacer explícito el código bajo prueba. No se reinstaló ni modificó el entorno.

### P1 que permanecen abiertos

- Incorporar type checking gradual.
- Completar la matriz de todos los campos de configuración, incluido el límite de volatilidad de cartera.
- Retirar legacy solo tras un ciclo de deprecación y verificación de consumidores externos.
- Integrar `feature/core-cleanup` en `develop` y después `develop` en `main`, únicamente tras autorización y revisión remota.

### Orden exacto de corrección restante

1. Healthcheck: validar realmente esquema y transacción reversible de las bases.
2. Configuración: cubrir cada campo con un cambio observable.
3. Calidad: tipos graduales.
4. Seguridad/UI: evitar excepciones internas.
5. Distribución: **completada para v1.2.2**; mantener la verificación del artefacto antes de retirar legacy.
6. Git: publicar la candidata y seguir los dos PR definidos en `GIT_WORKFLOW.md`; no saltar directamente a `main`.

Fecha: 16 de julio de 2026  
Proyecto auditado: contenido actual de `ELAN AI INVESTMENT.zip`, extraído sin eliminar archivos  
Rama observada: `feature/dashboard-integration`  
Commit de la rama: `a215847` (`Sprint 10 - Dashboard modular completo`)

## Resumen ejecutivo

ELAN Quantum es ejecutable y su núcleo cubierto por pruebas funciona: el paquete importa, los 79 nombres de módulo descubiertos importan, el healthcheck termina correctamente, las 30 pruebas pasan y Streamlit 1.59.2 levanta un servidor local saludable. No se encontró ninguna conexión con brokers ni código para enviar órdenes reales; el motor de operaciones es SQLite y está identificado como simulación.

El proyecto no está listo para publicar como v1.3. La CI definida por el propio repositorio está roja (`ruff` y `black` fallan), el working tree recibido ya contenía una gran cantidad de cambios sin consolidar, y el optimizador institucional incumple de forma reproducible `max_weight` cuando la restricción es matemáticamente inviable. Además, coexisten dos arquitecturas de análisis, dos backtests y dos implementaciones de cartera; la colisión `portfolio.py`/`portfolio/` hace que Python ignore silenciosamente una de ellas.

Estado general: **funcional para desarrollo local, no apto todavía para release**.

## Alcance y salvaguardas

- Se inspeccionaron `app.py`, `src/`, `tests/`, `config/`, `scripts/`, `pyproject.toml`, `requirements.txt`, los tres `.bat`, documentación, CI y Git.
- No se instaló ni actualizó ninguna dependencia.
- No se modificaron claves, credenciales, bases de datos ni `.venv`.
- No se conectó ningún broker ni se usó dinero real.
- No se hizo push, merge, cambio de rama, commit, borrado ni refactorización funcional.
- Los únicos archivos creados por la auditoría son los cinco documentos solicitados.

## Estado del repositorio recibido

- Rama local y upstream: `feature/dashboard-integration...origin/feature/dashboard-integration`, divergencia `0/0` según las referencias incluidas en el ZIP.
- Ramas locales: `main`, `develop`, `feature/backtesting-pro`, `feature/core-integration`, `feature/dashboard-integration`, `feature/intelligence-engine`, `feature/paper-trading`, `feature/portfolio-engine` y `feature/risk-engine`.
- El ZIP ya llegó sucio: 76 rutas aparecían como modificadas y 15 entradas agrupadas como no seguidas en `git status --porcelain`; no había cambios staged.
- El diff material contra `HEAD` contiene 57 archivos, 750 inserciones y 1.074 eliminaciones; ignorando espacios al final, 56 archivos, 739 inserciones y 1.063 eliminaciones.
- La versión 1.2.1 y los módulos Fundamental/Institutional/Quant están en gran parte sin commit sobre una rama cuyo último commit es Sprint 10.
- `core.autocrlf=true` y no existe `.gitattributes`; Git genera avisos LF/CRLF.
- El ZIP incluye `.git`, `.venv`, bases SQLite y logs. Es útil como copia de trabajo, pero no es un artefacto de distribución reproducible ni limpio.

## Inventario real

Hay 81 archivos Python bajo `src/`, 3.099 líneas de producción incluyendo `app.py`, 18 archivos de prueba con 468 líneas y un healthcheck de 51 líneas.

| Área | Módulos existentes | Uso real actual |
|---|---|---|
| Entrada | `app.py` | Entrada Streamlit activa |
| Núcleo | `core.bootstrap`, `core.config`, `core.engine`, `core.logging`, `core.models` | Activos en `app.py` |
| Pipeline alternativo | `core.pipeline` | Probado, pero no alcanzable desde `app.py` |
| Mercado activo | `providers.base`, `providers.yahoo`, `market_data` | Activos; Yahoo descarga símbolos secuencialmente |
| Mercado alternativo | `market.cache`, `market.loader`, `market.providers`, `market.validator` | Usado por `core.pipeline`, no por la app |
| Scoring activo | `scoring`, `quant.factors`, `quant.recommendations` | Activo |
| Scoring/decisión alternativo | `indicators.*`, `intelligence.*`, `decision.*`, `advisor.*` | Árbol paralelo, no usado por la app |
| Riesgo | `risk` | Activo |
| Cartera activa | `portfolio/__init__.py` | Gana la resolución de imports |
| Cartera sombreada | `portfolio.py` | No puede importarse como `elan_ai_invest.portfolio` |
| Submódulos de cartera | `portfolio.allocation`, `portfolio.metrics`, `portfolio.optimizer`, `portfolio.rebalance` | No alcanzables desde la app |
| Paper trading | `paper_trading` | Activo; SQLite local, sin broker |
| Backtest activo | `backtest.py` | Usado por el dashboard |
| Backtest alternativo | `backtesting.*` | Probado, pero no usado por el dashboard |
| Fundamental | `fundamental.models`, `fundamental.provider`, `fundamental.scoring` | Activo desde una pestaña |
| Institucional | `institutional.optimizer` | Activo desde una pestaña |
| Persistencia | `storage`, SQLite | Histórico manual |
| Dashboard | 13 módulos bajo `dashboard/` | Activos mediante `dashboard/__init__.py` |
| Operación | `system_status`, `scripts/healthcheck.py`, `.bat`, GitHub Actions | Activos, con limitaciones indicadas abajo |

El análisis estático de alcance encontró 39 módulos de paquete alcanzables desde `app.py` y 40 no alcanzables. “No alcanzable” no prueba por sí solo que un archivo pueda borrarse; sí demuestra que no forma parte del flujo de producción actual.

## Flujo actual de datos

1. `app.py` carga `config/settings.yaml` y `config/watchlist.csv`.
2. `build_core_engine()` elige `YahooMarketDataProvider` y configura logging.
3. `CoreEngine.run_analysis()` solicita precios a `market_data.download_adjusted_close()`.
4. `yfinance` descarga cada símbolo por separado; los fallos parciales se guardan en `DownloadResult.errors`.
5. `score_assets()` combina medias/momentum/volatilidad/drawdown con `quant.factors` y genera ranking, decisión y explicación.
6. El resultado se cachea durante una hora en Streamlit.
7. `risk.calculate_risk_report()` calcula VaR/CVaR histórico, volatilidad, drawdown, correlación y contribuciones.
8. Once pestañas consumen el mismo resultado: mercado, inteligencia, fundamentales, ranking, riesgo, cartera, institucional, paper trading, backtest, histórico y sistema.
9. El histórico se escribe en `data/elan_ai_invest.db` solo al pulsar “Guardar fotografía”.
10. Paper trading escribe en `data/paper_trading.db`; no llama a brokers.
11. Fundamental realiza otra consulta Yahoo bajo demanda lógica, aunque actualmente todas las pestañas se ejecutan en cada rerun.

Existe otro flujo separado: `core.pipeline -> market.ProviderManager -> indicators -> intelligence -> decision`. Tiene pruebas propias, pero no alimenta `app.py`.

## Resultados ejecutados

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Python del proyecto | OK | 3.14.5 |
| Importación principal | OK | `elan_ai_invest`, versión 1.2.1 |
| Importación de submódulos | OK | 79 nombres importables, 0 fallos |
| Healthcheck | OK | todas las comprobaciones devuelven OK |
| `pytest` | OK | 30 passed en 1,62 s |
| `ruff check .` | FALLO | 8 incidencias: 7 de orden de imports y 1 uso de `str, Enum` en vez de `StrEnum` |
| `black --check .` | FALLO | 36 archivos serían reformateados |
| `pip check` | OK | no hay requisitos rotos en la `.venv` recibida |
| Streamlit | OK | servidor temporal en `127.0.0.1:8513`; `/_stcore/health` respondió `ok`; proceso detenido |
| Cobertura | NO DISPONIBLE | `pytest-cov`/`coverage` no están declarados ni instalados |
| Tipado estático | NO DISPONIBLE | no hay mypy/pyright ni configuración |
| Auditor de seguridad | NO DISPONIBLE | no hay Bandit u otra herramienta declarada |

Versiones observadas: Streamlit 1.59.2, pandas 3.0.3, NumPy 2.5.1, yfinance 1.5.1, Plotly 6.9.0, Pydantic 2.13.4, pytest 9.1.1, Ruff 0.15.21 y Black 26.5.1.

## Hallazgos principales

### P0 — bloquea o rompe

1. **La CI no puede pasar.** Ruff devuelve 8 errores y Black rechaza 36 archivos. El workflow ejecuta ambos comandos antes de pytest, por lo que un PR no queda verde aunque los tests pasen.
2. **El optimizador institucional rompe `max_weight` en casos inviables.** Con tres activos y `max_weight=0.25`, devuelve 33,33 % por activo. La normalización final vuelve a superar el límite. Debe validar primero `n_activos * max_weight >= 1` o modelar efectivo.
3. **El estado Git impide una release trazable.** La implementación declarada como 1.2.1 está mezclada con 57 archivos materialmente modificados y módulos sin seguimiento sobre un commit de Sprint 10. No se puede atribuir ni revertir una v1.3 con seguridad desde este estado.

### P1 — importante

- Colisión de import `portfolio.py` frente a `portfolio/`; gana el paquete y el archivo histórico queda sombreado.
- Las dos carteras divergen: la sombreada redistribuye después del límite y calcula riesgo esperado; la activa recorta pesos sin redistribuir, puede dejar mucha más liquidez de la prevista y usa `profile` casi solo como etiqueta.
- Dos pipelines de mercado/scoring/decisión conviven con contratos diferentes.
- Dos motores de backtest conviven; el dashboard usa el simple, mientras `backtesting/` y `costs.py` quedan fuera. El backtest visible no aplica comisiones, deslizamiento, benchmark configurado ni validación fuera de muestra.
- Las once pestañas de `st.tabs` se ejecutan en cada rerun. Esto dispara cálculos, SQLite y la carga fundamental aunque la pestaña no esté visible.
- `market_data` descarga símbolos secuencialmente y no implementa timeout, reintento, backoff ni caché persistente.
- Gran parte de la configuración no gobierna el comportamiento: `market.interval`, `market.minimum_history`, `backtest.*`, `portfolio.*`, `paper_trading.enabled` y `risk.max_portfolio_volatility_pct` están ignorados o sustituidos por literales.
- Stop-loss y snapshots de paper trading existen y tienen tests, pero la app no llama `apply_stop_losses()` ni `save_snapshot()`; el histórico de patrimonio no se alimenta desde el flujo visible.
- Las operaciones paper hacen lectura y escritura en una transacción diferida; dos sesiones simultáneas podrían decidir con el mismo saldo previo. Falta una actualización condicional atómica y pruebas de concurrencia.
- El healthcheck crea previamente `data/` y `logs/` y llama “base accesible” a que exista la carpeta padre; no abre/escribe/verifica esquema.
- No hay lockfile. `requirements.txt` solo contiene `-e .[dev]`; una reinstalación futura puede resolver versiones distintas.
- El ZIP distribuye una `.venv` ligada a una ruta absoluta y Python 3.14, además de `.git`, logs y bases locales. No es portable y puede transportar estado privado.
- No hay cobertura, type checker ni auditoría de seguridad en CI; el dashboard, las rutas reales de Yahoo y varios límites financieros críticos carecen de pruebas.

### P2 — mejora

- `safe_render` está duplicado en `dashboard/layout.py` y `dashboard/safe.py`; la app usa el segundo.
- 40 módulos no son alcanzables desde la app; varios son stubs de pocas líneas. Deben clasificarse antes de moverlos o retirarlos.
- `MarketCache` usa pickle; si se reactiva con archivos no confiables puede ejecutar código al cargar.
- La interfaz muestra `st.exception()` o mensajes de excepción; en un despliegue remoto puede revelar rutas y detalles internos.
- Hay 22 usos de `use_container_width`, deprecado en Streamlit 1.59.2; debe sustituirse por `width` o el valor por defecto.
- Se inyecta CSS con `unsafe_allow_html=True` en vez de tema/configuración nativa.
- Solo 88 de 128 funciones/métodos de producción tienen argumentos y retorno completamente anotados (68,8 %); la mayor carencia está en dashboard y módulos legacy.
- `python-dotenv` está declarado pero no se importa en el código.
- Python 3.14 se usa localmente, pero CI solo prueba 3.11–3.13.
- Faltan `.gitattributes` y política única de finales de línea.
- Documentación desalineada: README dice 25 tests, se ejecutan 30; ROADMAP marca Fundamental como pendiente; `docs/architecture.md` conserva el nombre anterior y no describe la arquitectura actual; CHANGELOG duplica cabecera y mezcla orden de versiones.
- `update.bat` borra por nombre siete scripts legacy si existen; conviene convertirlo en migración explícita y reversible.

### P3 — futuro

- Adoptar navegación moderna por páginas/fragments si el producto crece más allá de las once pestañas.
- Valorar gráficos Vega/nativos para vistas simples y reservar Plotly para interacción necesaria.
- Añadir pruebas de propiedades para pesos, VaR/CVaR, invariantes contables y datos incompletos.
- Separar artefacto de desarrollo, artefacto de release y datos de usuario.

El catálogo completo y trazable está en `TECH_DEBT.md`.

## Dependencias

- Necesarias y usadas: Streamlit, pandas, NumPy, yfinance, Plotly, Pydantic y PyYAML.
- Declarada pero sin uso encontrado: `python-dotenv`.
- Desarrollo: pytest, Ruff y Black están instalados y se usan.
- No existe separación de dependencias de runtime y un entorno reproducible bloqueado.
- `pip check` es correcto en la copia actual; esto no garantiza que una reinstalación futura produzca el mismo conjunto.

## Seguridad

- No se encontraron nombres de archivos sensibles versionados ni patrones evidentes de claves privadas/tokens en el código inspeccionado.
- Todas las consultas SQLite revisadas usan parámetros para valores variables.
- No existe integración con broker real.
- Riesgos restantes: pickle en el árbol legacy, detalles técnicos expuestos en UI, empaquetado de bases/logs y ausencia de escaneo automatizado de dependencias/código.

## Orden exacto de corrección recomendado

1. Preservar el estado recibido en una rama/copia de seguridad y registrar por separado qué cambios forman realmente 1.2.1; no mezclar aún más trabajo.
2. Añadir tests de regresión para `max_weight`, casos inviables y resolución de `elan_ai_invest.portfolio`.
3. Corregir el P0 del optimizador institucional y hacer fallar explícitamente restricciones imposibles.
4. Elegir una única implementación canónica de cartera, portar comportamiento faltante y mantener adaptador temporal; no borrar ninguna variante aún.
5. Aplicar Ruff/Black en un commit puramente mecánico y dejar CI verde.
6. Elegir el pipeline canónico; marcar el alternativo como legacy, medir consumidores y congelar su API antes de moverlo.
7. Conectar todos los campos de configuración o retirarlos con deprecación documentada.
8. Unificar el backtest visible con costes, benchmark y pruebas sin look-ahead; declarar claramente sus limitaciones.
9. Hacer lazy/condicional el contenido de pestañas costosas y medir tiempo de rerun.
10. Completar el ciclo de paper trading: snapshots, stop-loss explícito, atomicidad y concurrencia.
11. Añadir cobertura, tipado y seguridad a CI; eliminar solo dependencias demostradas como innecesarias.
12. Sincronizar documentación, ramas y versionado; solo entonces preparar v1.3.

## Cambios realizados por esta auditoría

No se corrigió código ni se refactorizó. Se crearon únicamente:

- `AUDIT_REPORT.md`
- `ARCHITECTURE_CURRENT.md`
- `TECH_DEBT.md`
- `REFACTOR_PLAN.md`
- `RELEASE_PLAN_V1_3.md`

## Git status final

```text
## feature/dashboard-integration...origin/feature/dashboard-integration
76 rutas modificadas
26 archivos no seguidos con --untracked-files=all
0 cambios staged
0 archivos borrados
```

De los 26 archivos no seguidos, 21 ya venían en el ZIP y 5 son los documentos de esta auditoría. El árbol no está limpio porque se preservó intacto el trabajo previo recibido. `git diff --check` no detectó errores de whitespace, aunque sí repitió los avisos LF/CRLF causados por `core.autocrlf=true` y la ausencia de `.gitattributes`.
