# Memoria operativa de ELAN Quantum

> Contexto mínimo para retomar el proyecto. No es un diario: el detalle histórico vive en `CHANGELOG.md`, Git y GitHub.

## Protocolo de reanudación

1. Leer `AGENTS.md`, `.claude/napkin.md` y este archivo.
2. Verificar solo rama/working tree, últimos commits y, si aplica, PR y CI activos.
3. Continuar desde «Siguiente paso» sin reabrir decisiones cerradas salvo evidencia nueva.
4. Al cerrar un bloque, registrar únicamente estado, gates, decisiones nuevas y próximo paso.

## Estado validado — 14 de agosto de 2026

- Repositorio: `diegocorreabuiles-del/ELAN-AI-INVEST`.
- Rama activa `feature/fx-correlation-module`, abierta desde `develop@4c19d28`.
- Bloques 21 y 22 integrados; PR documental #21 fusionada y CI posterior `30698354050` verde.
- Bloque 23 integrado en `develop@765f94b` mediante PR #22; las matrices CI `31490174578` y `31490212493` pasaron en Python 3.11–3.14.
- Bloque 24 integrado en `develop@4c19d28` mediante PR #23; la lista de seguimiento se restaura y guarda en SQLite, y el CI posterior `31492357864` quedó verde.
- Bloque 25 cerrado técnicamente: nueva pestaña Divisas con normalización USD por unidad, desempeño base 100, matriz de correlaciones y correlación móvil; validación funcional y gate Windows completos.
- Bloque 26 definido y no iniciado: AI Explanation Engine v1 local, determinista y trazable; [alcance formal](docs/block_26_ai_explanation_engine.md).
- `main@5cf2bca1cd98954c1c71e191368432d2b242d9ae`, con tag anotado `v1.3.0-rc.1`; no hay GitHub Release ni despliegue.
- `stash@{0}` conserva metadata gzip local previa a la sincronización: `local gzip metadata before syncing develop`.
- Producto local de análisis y paper trading; no conecta brokers ni dinero real.
- Refactorización incremental de la Terminal de Decisión: Fases 3–9 implementadas localmente. `analysis/` ensambla clasificación, técnico/riesgo, Score Engine, Data Confidence, decisión, Trade Plan y modelos específicos Crypto/Meme Coin/Stablecoin; la UI los presenta sin alterar scoring productivo, cartera ni paper trading.
- Motor FX estructural implementado localmente: registro versionado de 36 monedas, pares virtuales `FX_BASE_QUOTE`, routing directo/inverso/sintético, históricos OHLC UTC, log returns, cobertura, KPIs, calidad, caché CSV y comparador multiactivo; sin tablas nuevas, Supabase, scoring productivo, cartera ni paper trading.

Estos datos son dinámicos: volver a comprobarlos solo cuando afecten la tarea actual.

## Gate vigente

- Windows, Python 3.12.13: gate local posterior al Motor FX certificado por segmentos equivalentes a la suite completa: 307/307 pruebas, incluidos 20 AppTests; cobertura global de ramas 80,4 % (mínimo 75 %); Ruff y Black globales, mypy de los 12 módulos FX afectados y `git diff --check` verdes. Mypy global conserva 55 errores históricos fuera de alcance. La segmentación evita el bloqueo observado en la ejecución monolítica de AppTest; no equivale a CI remoto ni integración.
- Corrección UTC posterior: 23/23 pruebas enfocadas, AppTest integral de las 13 vistas, Ruff, Black, mypy dirigido y `git diff --check` verdes; Yahoo real validado para USD/COP, USD/MXN, USD/CLP, USD/BRL, USD/PEN y Brent; app local HTTP 200 en `8501`. La inspección visual automatizada no estuvo disponible por fallo DPAPI del navegador integrado.
- Merge gate final de Terminal de Decisión y Motor FX: 308/308 pruebas, 20 AppTests, cobertura global de ramas 80,5 %, Ruff, Black, mypy configurado y dirigido a FX, lock, `pip check` y `git diff --check` verdes. La validación remota queda a cargo de la PR #24.
- Punto estable local del horizonte sincronizado de Mercado: 309/309 pruebas y cobertura global de ramas 82,7 %; Ruff, Black, mypy, lock, `pip check` y `git diff --check` verdes. El selector local actualiza el periodo global y el comparador; Yahoo real confirmó 251 sesiones para SPY `1y` frente a 1.255 para `5y`. La validación remota corresponde a la PR #24 después del push.
- Linux/Docker sobre `0a23623`, Python 3.11–3.14: 178 pruebas por versión y paquete verdes para el cierre del Bloque 23.
- Artefacto reproducible del Bloque 23 sobre `0a23623`: 171 archivos; SHA-256 `0d1275e36c945b8f3710fb42348fa91efac6a7e908b16a1f1f383e001e44eab1`.
- Última evidencia remota: PR #23 fusionada en `develop@4c19d28`; CI posterior `31492357864` verde.
- `develop` exige PR, checks estrictos, historial lineal y conversaciones resueltas; force-push y borrado deshabilitados.

## Decisiones canónicas

1. **Git:** ramas de trabajo entran por PR a `develop`; solo `develop` puede promoverse a `main`.
2. **Autorizaciones:** fusionar `main`, cambiar versión, crear tag, publicar release y desplegar son acciones separadas y requieren permiso explícito.
3. **Seguridad financiera:** simulación únicamente. Broker, credenciales, live mode y órdenes reales requieren diseño y aprobación independientes.
4. **Arquitectura:** `core.engine.CoreEngine`, `portfolio.engine` y `backtesting.engine.BacktestEngine` son canónicos; legacy permanece congelado/deprecado.
5. **Riesgo:** usar retornos consecutivos alineados; nunca inventar retornos cero ni hacer forward-fill.
6. **Paper trading:** SQLite local, `BEGIN IMMEDIATE`, mutaciones atómicas, fallo cerrado y stops manuales/confirmados.
7. **Streamlit:** workspace grafito con 13 pestañas lazy mediante `tab.open`; sin CSS inyectado ni `use_container_width`.
8. **Errores:** UI neutra con referencia; detalle técnico solo en logs.
9. **Versión y dependencias:** `pyproject.toml` es la fuente de versión; `requirements.lock` fija el entorno exacto.
10. **Instrumentos:** catálogo MIT de Adanos más `config/instruments.csv`; históricos en Yahoo. Catálogo disponible no garantiza histórico; no añadir `financedatabase` al runtime.
11. **Market Data:** detalle OHLCV solo para activo/horizonte visible, caché de 15 minutos y comparaciones con rendimientos consecutivos alineados. Calidad es metadata aditiva y no altera precios.
12. **Noticias:** Yahoo solo al abrir la pestaña, con caché y límites; contexto de solo lectura, sin efecto en scoring, señales, riesgo, cartera ni paper trading.
13. **Workspace conectado:** Mercado, Inteligencia, Fundamental, Noticias y Ranking comparten un activo global; selección de filas y fragmentos locales no eliminan la carga lazy ni cambian semántica financiera.
14. **Lista persistente:** `workspace_preferences` guarda el `Universo activo` en SQLite local; `config/watchlist.csv` solo es el valor inicial cuando no existe preferencia.
15. **Divisas:** todas las series se expresan como USD por una unidad de divisa; los pares USD/XXX se invierten antes de alinear sesiones y calcular retornos consecutivos, sin forward-fill ni retornos cero inventados. Es análisis de solo lectura.
16. **Explicabilidad v1:** el Bloque 26 será local y determinista; explicará resultados existentes sin llamar LLM/API, sin consumir tokens, sin crear nuevas señales y sin modificar scoring, riesgo, cartera ni paper trading.
17. **Score Engine de la Terminal de Decisión:** pesos centralizados por tipo de activo, ausencia como `None` con redistribución proporcional, stablecoins con componentes propios y decisión determinista limitada por riesgo, tendencia, régimen y Data Confidence. Permanece en investigación y no altera el scoring productivo ni paper trading.
18. **Trade Plan de la Terminal de Decisión:** módulo long-only de investigación; entrada desde soporte observado, invalidación bajo soporte con colchón ATR, targets únicamente en resistencias observadas y R/R desde `entry_high`. Falla cerrado y no publica niveles parciales si falta histórico, ATR, soporte, dos resistencias o coherencia OHLC; no crea órdenes ni altera paper trading.
19. **UI de Terminal de Decisión:** la cabecera separa visión global y activo seleccionado; PER permanece en Fundamental. Decisión, sub-scores, confianza, desglose técnico, plan y explicaciones estructuradas consumen `AssetAnalysis`; reutilizan el OHLCV cacheado de Mercado y fallan de forma contenida. Las 13 pestañas y `tab.open` permanecen intactas.
20. **Modelos Crypto/Meme/Stablecoin:** solo derivan de OHLCV Yahoo ya disponible la fuerza relativa frente a BTC, actividad de volumen, ADV, momentum/RVOL y salud/desviación del peg. Derivados, on-chain, DEX, holders, social, reservas, emisor, supply y liquidez profunda permanecen `N/D` hasta disponer de proveedor explícito. Stablecoins usan decisión `ESPERAR`, lenguaje de depeg y ningún plan direccional tradicional. Todo permanece en investigación y sin ejecución real.
21. **Gate adverso de la Terminal de Decisión:** la matriz cubre los 11 tipos de activo, histórico corto/incompleto, duplicados, valores no finitos, volumen cero, escalas extremas, volatilidad extrema y depeg transitorio o vigente. Scores y confianza permanecen finitos y acotados; ante evidencia insuficiente el análisis falla cerrado, no publica planes parciales, stablecoins permanecen en `ESPERAR` sin plan y meme/activos desconocidos no emiten decisiones alcistas no justificadas.
22. **Motor FX:** `config/currencies.csv` es el catálogo maestro; los pares se generan virtualmente y usan `FX_BASE_QUOTE`. La resolución prioriza directo, inverso y rutas cortas vía USD/EUR con máximo dos intermediarios; los históricos se alinean en UTC mediante inner join, las correlaciones usan log returns pareados y reportan cobertura. Yahoo es el único proveedor y falla como `N/D`; la caché es CSV inerte. No hay tablas FX/Supabase ni integración con scoring productivo, cartera o paper trading.

## Reglas de implementación

- Preservar cambios ajenos; no borrar legacy, datos ni scripts sin alcance y autorización específicos.
- Usar `apply_patch`; ante fallo DPAPI, aplicar un diff UTF-8 solo después de `git apply --check`.
- Cerrar SQLite con `contextlib.closing`; `with connection` no cierra la conexión.
- Pruebas sin red y bases temporales; toda corrección contractual necesita regresión.
- Sincronizar documentos canónicos cuando cambie comportamiento; los históricos conservan hechos de su fecha.
- Avisos `debconf` de Docker no son fallos si el proceso termina en código 0; revisar aparte warnings de recursos, seguridad o datos.

## Operación y mapa mínimo

- Arranque y uso: `README.md`; flujo Git: `GIT_WORKFLOW.md`; gates/release: `RELEASE_PLAN_V1_3.md`.
- Web: `app.py`; UI: `src/elan_ai_invest/dashboard/`.
- Core, cartera y backtest: `src/elan_ai_invest/core/`, `portfolio/engine.py`, `backtesting/engine.py`.
- Riesgo, paper y storage: `risk.py`, `paper_trading.py`, `storage.py`.
- Mercado/noticias/divisas/instrumentos: `market/`, `news/`, `forex.py`, `instruments.py`, `config/instruments.csv`, `config/catalog/`.
- Gates: `.github/workflows/ci.yml` y `scripts/`; arquitectura/estado: `ELAN_ARCHITECTURE.md`, `TECH_DEBT.md`, `CHANGELOG.md`.

## Deuda abierta relevante

- TD-012: completar matriz configuración/consumidor.
- TD-021: inventariar módulos no alcanzables antes de deprecarlos.
- TD-026: ampliar mypy más allá de los 12 módulos críticos.
- TD-035: sustituir pruebas de backtest redundantes por casos nuevos.
- TD-036: considerar multipágina solo cuando el tamaño lo justifique.
- TD-037: ampliar invariantes/property tests de pesos, cash y contabilidad.

## Siguiente paso

- Publicar el punto estable del horizonte sincronizado en `feature/fx-correlation-module` y esperar la matriz CI Python 3.11–3.14 de la PR #24; mantenerla sin fusionar hasta autorización explícita.
- Mantener las Fases 3–9 aisladas del scoring productivo, cartera y paper trading; no añadir proveedores ni APIs sin inventario de fuente, campo, disponibilidad y fallback.
- Publicar o integrar los cambios solo mediante PR hacia `develop` y con autorización explícita; mantener fuera brokers/dinero real y cualquier promoción a `main`, release o despliegue.
