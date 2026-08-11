# Memoria operativa de ELAN Quantum

> Contexto mínimo para retomar el proyecto. No es un diario: el detalle histórico vive en `CHANGELOG.md`, Git y GitHub.

## Protocolo de reanudación

1. Leer `AGENTS.md`, `.claude/napkin.md` y este archivo.
2. Verificar solo rama/working tree, últimos commits y, si aplica, PR y CI activos.
3. Continuar desde «Siguiente paso» sin reabrir decisiones cerradas salvo evidencia nueva.
4. Al cerrar un bloque, registrar únicamente estado, gates, decisiones nuevas y próximo paso.

## Estado validado — 2 de agosto de 2026

- Repositorio: `diegocorreabuiles-del/ELAN-AI-INVEST`.
- Rama `feature/interactive-asset-workspace` abierta desde `develop@11f7495e470982cc6e86bbf2d7d19f2810fb37e2`.
- Bloques 21 y 22 integrados; PR documental #21 fusionada y CI posterior `30698354050` verde.
- Bloque 23 integrado en `develop@765f94b` mediante PR #22; las matrices CI `31490174578` y `31490212493` pasaron en Python 3.11–3.14.
- Bloque 24 cerrado técnicamente en la rama local `feature/persistent-watchlist`, realineada sobre `develop@765f94b`: la lista de seguimiento se restaura y guarda en SQLite; validación manual aceptada y gate Windows verde.
- `main@5cf2bca1cd98954c1c71e191368432d2b242d9ae`, con tag anotado `v1.3.0-rc.1`; no hay GitHub Release ni despliegue.
- `stash@{0}` conserva metadata gzip local previa a la sincronización: `local gzip metadata before syncing develop`.
- Producto local de análisis y paper trading; no conecta brokers ni dinero real.

Estos datos son dinámicos: volver a comprobarlos solo cuando afecten la tarea actual.

## Gate vigente

- Windows, Python 3.12.13: 183 pruebas, cobertura 81,48 % (mínimo 75 %); persistencia de la lista con pruebas SQLite/AppTest, Ruff y Black verdes. Lock, `pip check`, mypy crítico y healthcheck verdes.
- Linux/Docker sobre `0a23623`, Python 3.11–3.14: 178 pruebas por versión y paquete verdes para el cierre del Bloque 23.
- Artefacto reproducible del Bloque 23 sobre `0a23623`: 171 archivos; SHA-256 `0d1275e36c945b8f3710fb42348fa91efac6a7e908b16a1f1f383e001e44eab1`.
- Última evidencia remota: PR #22 fusionada en `develop@765f94b`; CI `31490174578` y `31490212493` verde en Python 3.11–3.14.
- `develop` exige PR, checks estrictos, historial lineal y conversaciones resueltas; force-push y borrado deshabilitados.

## Decisiones canónicas

1. **Git:** ramas de trabajo entran por PR a `develop`; solo `develop` puede promoverse a `main`.
2. **Autorizaciones:** fusionar `main`, cambiar versión, crear tag, publicar release y desplegar son acciones separadas y requieren permiso explícito.
3. **Seguridad financiera:** simulación únicamente. Broker, credenciales, live mode y órdenes reales requieren diseño y aprobación independientes.
4. **Arquitectura:** `core.engine.CoreEngine`, `portfolio.engine` y `backtesting.engine.BacktestEngine` son canónicos; legacy permanece congelado/deprecado.
5. **Riesgo:** usar retornos consecutivos alineados; nunca inventar retornos cero ni hacer forward-fill.
6. **Paper trading:** SQLite local, `BEGIN IMMEDIATE`, mutaciones atómicas, fallo cerrado y stops manuales/confirmados.
7. **Streamlit:** workspace grafito con 12 pestañas lazy mediante `tab.open`; sin CSS inyectado ni `use_container_width`.
8. **Errores:** UI neutra con referencia; detalle técnico solo en logs.
9. **Versión y dependencias:** `pyproject.toml` es la fuente de versión; `requirements.lock` fija el entorno exacto.
10. **Instrumentos:** catálogo MIT de Adanos más `config/instruments.csv`; históricos en Yahoo. Catálogo disponible no garantiza histórico; no añadir `financedatabase` al runtime.
11. **Market Data:** detalle OHLCV solo para activo/horizonte visible, caché de 15 minutos y comparaciones con rendimientos consecutivos alineados. Calidad es metadata aditiva y no altera precios.
12. **Noticias:** Yahoo solo al abrir la pestaña, con caché y límites; contexto de solo lectura, sin efecto en scoring, señales, riesgo, cartera ni paper trading.
13. **Workspace conectado:** Mercado, Inteligencia, Fundamental, Noticias y Ranking comparten un activo global; selección de filas y fragmentos locales no eliminan la carga lazy ni cambian semántica financiera.
14. **Lista persistente:** `workspace_preferences` guarda el `Universo activo` en SQLite local; `config/watchlist.csv` solo es el valor inicial cuando no existe preferencia.

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
- Mercado/noticias/instrumentos: `market/`, `news/`, `instruments.py`, `config/instruments.csv`, `config/catalog/`.
- Gates: `.github/workflows/ci.yml` y `scripts/`; arquitectura/estado: `ELAN_ARCHITECTURE.md`, `TECH_DEBT.md`, `CHANGELOG.md`.

## Deuda abierta relevante

- TD-012: completar matriz configuración/consumidor.
- TD-021: inventariar módulos no alcanzables antes de deprecarlos.
- TD-026: ampliar mypy más allá de los 12 módulos críticos.
- TD-035: sustituir pruebas de backtest redundantes por casos nuevos.
- TD-036: considerar multipágina solo cuando el tamaño lo justifique.
- TD-037: ampliar invariantes/property tests de pesos, cash y contabilidad.

## Siguiente paso

- Publicar el Bloque 24 mediante PR hacia `develop` y comprobar su matriz CI.
- Fusionar el Bloque 24 solo con autorización explícita y checks verdes.
- Mantener fuera de alcance brokers/dinero real y cualquier promoción a `main`, release o despliegue.
