# Arquitectura actual de ELAN Quantum

> Documento histórico: fotografía anterior a v1.2.2 Core Cleanup. La arquitectura canónica vigente está en `ELAN_ARCHITECTURE.md`; las colisiones y flujos paralelos descritos abajo son el estado “antes”.

Este documento describe el sistema **tal como existe**, no la arquitectura objetivo.

## Vista general

```text
app.py (Streamlit)
  ├─ config/settings.yaml + config/watchlist.csv + config/instruments.csv
  ├─ config/catalog/adanos_tickers.csv.gz
  ├─ core.bootstrap -> core.engine
  │    ├─ providers.yahoo -> market_data -> yfinance
  │    ├─ scoring -> quant.factors + quant.recommendations
  │    └─ storage -> data/elan_ai_invest.db (solo snapshot manual)
  ├─ risk
  ├─ portfolio/__init__.py       [portfolio.py queda sombreado]
  ├─ paper_trading -> data/paper_trading.db
  ├─ backtest.py                 [backtesting/ no alimenta la UI]
  ├─ fundamental -> yfinance
  ├─ institutional.optimizer
  └─ dashboard/* (11 pestañas, evaluación eager)

Flujo paralelo no conectado a app.py:
core.pipeline
  └─ market.providers -> market.loader -> yfinance
       └─ indicators -> intelligence -> decision
```

## Capas observadas

### Presentación

- `app.py` es el único entrypoint.
- `dashboard/__init__.py` importa todas las vistas y expone sus renderers.
- `app.py` presenta 13 vistas mediante un `st.pills` superior y solo renderiza
  la vista seleccionada en cada rerun.
- Estado de usuario: widgets y claves de Streamlit; no hay inicialización central de `st.session_state`.
- Caché: análisis de mercado a una hora y fundamentales a seis horas.

### Orquestación activa

- `core.bootstrap.build_core_engine()` carga configuración, logging y proveedor.
- `core.engine.CoreEngine` normaliza símbolos, descarga, puntúa, detecta régimen y opcionalmente persiste.
- `core.models` transporta `AnalysisRequest` y `AnalysisResult` mediante dataclasses.

### Datos de mercado activos

- Contrato: `providers.base.MarketDataProvider`.
- Implementación: `providers.yahoo.YahooMarketDataProvider`.
- Función real: `market_data.download_adjusted_close()`.
- Descarga: un símbolo por llamada, periodo configurable por request, intervalo fijo `1d`.
- Validación real: dataframe no vacío y al menos 60 observaciones por símbolo.

### Análisis activo

- `scoring.score_assets()` calcula score base técnico.
- `quant.factors` añade tendencia, momentum, fuerza relativa, riesgo ajustado y calidad.
- `quant.recommendations` genera decisión y explicación.
- `risk.calculate_risk_report()` usa retornos históricos y cartera equiponderada por defecto.
- `portfolio/__init__.py` construye asignación limitada y curva histórica.
- `institutional.optimizer` ofrece cuatro heurísticas de pesos long-only.
- `fundamental` obtiene snapshot Yahoo y calcula cinco factores.

### Simulación y persistencia

- `paper_trading.PaperTradingEngine` crea cuenta, posiciones, órdenes y snapshots en SQLite.
- No hay cliente, SDK, endpoint ni credenciales de broker.
- `storage.py` mantiene `analysis_history` y la preferencia `workspace_preferences` en otra base SQLite.
- Logging usa consola y `RotatingFileHandler`.

## Inventario de paquetes

| Paquete/archivo | Componentes | Estado |
|---|---|---|
| `core/` | bootstrap, config, engine, logging, models, pipeline | Cinco activos; `pipeline` paralelo |
| `providers/` | base, yahoo | Activo |
| `market_data.py` | descarga de cierres | Activo |
| `market/` | cache, loader, providers, validator | Paralelo/legacy |
| `scoring.py` | ranking principal | Activo |
| `quant/` | factors, recommendations | Activo |
| `indicators/` | trend, momentum, volatility, engine | Solo pipeline paralelo |
| `intelligence/` | models, confidence, decision, explain, engine | Solo pipeline paralelo |
| `decision/` | filters, weights, constraints, allocator, engine | Solo pipeline paralelo |
| `advisor/` | ranking, recommendations, explanations, advisor | Sin consumidor encontrado |
| `risk.py` | informe de riesgo | Activo |
| `portfolio.py` | implementación histórica completa | Sombreada por el paquete |
| `portfolio/` | implementación en `__init__` y cuatro helpers | `__init__` activo; helpers sin consumidor |
| `paper_trading.py` | simulador SQLite | Activo |
| `backtest.py` | momentum multi-activo | Activo en UI |
| `backtesting/` | engine, strategy, metrics, costs, benchmark, report | Probado, no usado en UI |
| `fundamental/` | models, provider, scoring | Activo |
| `institutional/` | optimizer | Activo |
| `dashboard/` | 13 archivos | Activo; contiene `safe_render` duplicado |
| `storage.py` | histórico SQLite | Activo |
| `system_status.py` | estado resumido | Activo |

## Contratos y colisiones

### `elan_ai_invest.portfolio`

Existen simultáneamente:

- `src/elan_ai_invest/portfolio.py`
- `src/elan_ai_invest/portfolio/__init__.py`

Python resuelve el segundo. El primero no es accesible con el nombre público esperado. Ambos definen `PortfolioPlan`, `build_portfolio` y `portfolio_equity_curve`, pero con campos, parámetros y comportamiento distintos.

### Backtesting

- El dashboard llama `backtest.momentum_backtest()`.
- Los tests históricos y “pro” llaman `backtesting.BacktestEngine`.
- `backtesting.costs` y `backtesting.benchmark` no se conectan al engine ni a la UI.

### Pipelines

- Pipeline A, productivo: `CoreEngine -> MarketDataProvider -> scoring/quant`.
- Pipeline B, aislado: `InvestmentPipeline -> ProviderManager -> IndicatorEngine -> IntelligenceEngine -> DecisionEngine`.
- Sus modelos, scores, umbrales y estructuras de resultado son incompatibles.

## Configuración efectiva

| Campo | Estado real |
|---|---|
| `app.*` | nombre/versión parcialmente usados |
| `market.provider` | usado |
| `market.benchmark` | usado |
| `market.period` | no gobierna el valor inicial de UI |
| `market.interval` | ignorado; se usa `1d` fijo |
| `market.minimum_history` | ignorado; código usa 60 y scoring 210 |
| `scoring.*` | usado |
| `backtest.*` | ignorado por dashboard |
| `storage.database_path` | usado |
| `logging.*` | usado |
| `risk.annualisation_days` | usado |
| otros `risk.*` | algunos usados; límite de volatilidad no aplicado |
| `portfolio.*` | casi totalmente ignorado por dashboard |
| `paper_trading.enabled` | ignorado |
| otros `paper_trading.*` | usados |

## Persistencia y efectos laterales

- El arranque de `app.py` configura logging y puede crear el archivo de log.
- Construir `PaperTradingEngine` verifica/crea esquema y cuenta en cada rerun.
- Abrir histórico crea la base/tabla si no existen.
- La descarga Yahoo solo se ejecuta al crear una sesión de app, no al levantar el servidor HTTP.
- Los datos de mercado en memoria se cachean con Streamlit; no se usa `market.cache` en el flujo activo.

## Fronteras de seguridad

- Aplicación local sin autenticación propia.
- Fuente externa: Yahoo/yfinance.
- El selector global usa `instruments.py`, el catálogo curado/Adanos y las filas
  Forex habilitadas de `config/currencies.csv`; no consulta Yahoo durante la
  búsqueda. La presencia de un instrumento no garantiza disponibilidad actual.
- Datos persistentes: SQLite local y logs.
- No hay broker real.
- `market.cache` usa pickle, aunque está fuera del flujo activo.
- Las excepciones técnicas pueden mostrarse en el frontend.

## Arquitectura verificable frente a arquitectura declarada

`docs/architecture.md` documenta una versión anterior centrada en Core, providers, scoring y storage. No recoge Quant, Fundamental, Institutional, los dos pipelines, la colisión de cartera, los dos backtests ni la modularización actual del dashboard. Este archivo debe considerarse la fotografía “as-is” hasta que se ejecute el plan de refactorización.
