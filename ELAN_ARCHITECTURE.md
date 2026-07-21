# Arquitectura canónica de ELAN Quantum v1.2.2

Estado: arquitectura vigente tras la Fase 1 de estabilización. `ARCHITECTURE_CURRENT.md` conserva la fotografía anterior a la limpieza.

## Flujo de producción

```text
app.py (Streamlit)
  -> core.bootstrap.build_core_engine()
  -> core.engine.CoreEngine                         [pipeline canónico]
       -> providers.yahoo.YahooMarketDataProvider
       -> market_data.download_adjusted_close()
            -> market.cache.MarketCache (CSV inerte, TTL, escritura atómica)
       -> scoring + quant
       -> storage (solo si se solicita persistencia)
  -> risk
  -> portfolio.engine                               [Portfolio Engine canónico]
  -> institutional.optimizer
  -> backtesting.engine.BacktestEngine              [Backtesting Engine canónico]
  -> fundamental
  -> paper_trading (simulación SQLite; sin broker)
  -> dashboard/*
```

Los datos de mercado entran por el proveedor configurado, se validan con `market.interval` y `market.minimum_history`, y se convierten en un `AnalysisResult`. Yahoo usa timeout y retry/backoff acotados; los aciertos se guardan como CSV inerte con TTL y clave SHA-256. Todas las vistas reciben ese resultado común. Las pestañas costosas solo se renderizan cuando están abiertas; los cachés tienen TTL y límites de entradas.

## APIs canónicas

| Dominio | Implementación canónica | Compatibilidad temporal |
|---|---|---|
| Pipeline | `elan_ai_invest.core.CoreEngine` | `core.pipeline.InvestmentPipeline` reexporta la implementación congelada de `legacy.pipeline_v1` y avisa de deprecación al instanciarse |
| Cartera | `elan_ai_invest.portfolio.engine` | `elan_ai_invest.portfolio` reexporta la API canónica; la implementación anterior se conserva en `legacy.portfolio_package_v1` |
| Backtest | `elan_ai_invest.backtesting.engine.BacktestEngine` | `backtesting.momentum` y `backtest.py` delegan en el engine canónico; la UI usa resultados netos de costes |

## Invariantes relevantes

- El optimizador institucional nunca devuelve un peso superior a `max_weight`.
- Si `n_activos * max_weight < 1`, falla con un `ValueError` que explica la inviabilidad.
- Portfolio valida capital, posiciones, cap por posición y efectivo mínimo.
- En Portfolio, `invested_weight_pct + cash_weight_pct == 100` dentro de tolerancia numérica.
- Paper trading permanece desactivable por configuración y no tiene integración con brokers.
- El backtest calcula señales al cierre y desplaza los pesos una barra antes de aplicar retornos.
- Cada compra o venta adquiere un bloqueo `BEGIN IMMEDIATE` antes de leer saldo, posición o límite de posiciones.
- Venta y reset exigen actualizar exactamente una fila de cuenta; si la cuenta falta o está dañada, SQLite revierte posiciones, órdenes y snapshots en lugar de confirmar un estado parcial.
- Efectivo, posición y orden se confirman juntos o se revierten juntos; el update de efectivo impide saldos negativos.
- SQLite usa WAL y un timeout de escritura para permitir lecturas y serializar sesiones concurrentes.
- Valoración y snapshot comparten una única transacción y representan el mismo estado contable.
- Comisión y slippage se cargan únicamente sobre turnover ejecutado; un cambio completo de activo tiene turnover 2.0.
- El benchmark visible procede de `market.benchmark`; si falta en los datos, el backtest falla con un mensaje claro.

## Configuración conectada en esta fase

| Configuración | Consumidor |
|---|---|
| `market.period` | valor inicial de Streamlit y solicitud de análisis |
| `market.interval` | proveedor Yahoo y descarga |
| `market.minimum_history` | validación de series |
| `market.timeout_seconds`, `max_retries`, `backoff_seconds` | política de red del proveedor Yahoo |
| `market.cache_ttl_seconds`, `cache_directory` | caché CSV segura dentro del proyecto |
| `portfolio.*` | defaults y restricciones de `build_portfolio` |
| `backtest.lookback`, `top_n`, `rebalance_days`, `commission_pct`, `slippage_pct` | controles, costes y ejecución del backtest visible |
| `market.benchmark` | curva comparativa del backtest y factores cuantitativos |
| `paper_trading.enabled` | creación y renderizado del simulador |
| `app.version` | sincronizada con paquete y `pyproject.toml` en 1.2.2 |

## Módulos legacy preservados

- `src/elan_ai_invest/legacy/pipeline_v1.py`
- `src/elan_ai_invest/legacy/portfolio_package_v1.py`
- `src/elan_ai_invest/legacy/portfolio_components/`
- Árbol auxiliar del pipeline antiguo: `advisor/`, `market/`, `indicators/`, `intelligence/` y `decision/`; está marcado como legacy en sus paquetes y no alimenta `app.py`.

No se borró ninguna implementación. Su retirada requiere búsqueda de consumidores externos, un ciclo de deprecación y un commit dedicado.

## Fronteras operativas

- Fuente externa: Yahoo mediante `yfinance`; las pruebas no dependen de red.
- Persistencia: SQLite local para histórico y paper trading.
- No existe integración activa con brokers ni uso de dinero real.
- La copia activa y su editable viven en `C:\Users\elanv\Desktop\ELAN AI INVESTMENT`. Las validaciones usan `PYTHONPATH=src` sin reinstalar ni modificar `.venv`.

## Frontera de distribución

- `scripts/build_distribution.py` toma exclusivamente los blobs confirmados en `HEAD`; nunca copia el working tree ni archivos no seguidos.
- La política bloquea estado local y sensible (`.git`, `.venv`, `data`, `logs`, bases, cachés, ejecutables, claves y credenciales) en lugar de omitirlo silenciosamente.
- El ZIP añade únicamente `data/` y `logs/` vacíos para el primer arranque y un `DISTRIBUTION_MANIFEST.json` con versión, commit, tamaño y SHA-256 de cada archivo.
- El verificador exige una sola raíz portable, archivos operativos mínimos, correspondencia exacta con el manifiesto e integridad de todos los hashes.

## Frontera de pruebas

- Pytest mide líneas y ramas de `app.py` y de todo `elan_ai_invest`, incluidos módulos legacy no ejecutados; CI bloquea cualquier resultado inferior a 75 %.
- AppTest sustituye el Core Engine y los fundamentales por datos deterministas, prohíbe llamadas Yahoo y renderiza tanto el flujo inicial como todas las vistas.
- El baseline local validado es 77,5 %. El umbral debe aumentar solo junto con pruebas que cubran riesgo real, sin excluir legacy para inflar el porcentaje.

## Frontera de integración

- `scripts/check_git_flow.py` admite únicamente ramas de trabajo hacia `develop` y `develop` hacia `main`.
- CI valida la transición del pull request; Dependabot usa `develop` como destino.
- `feature/core-cleanup` desciende de `develop`, pero permanece local y sin upstream. No se ha hecho push, merge ni tag.
- Las protecciones remotas requeridas y la secuencia operativa están en `GIT_WORKFLOW.md`; su aplicación en GitHub requiere permisos y autorización externos.

## Ciclo de riesgo de paper trading

- La pestaña Paper Trading expone un evento manual: **Revisar stops y guardar snapshot**.
- El usuario debe confirmar expresamente que la acción solo afecta a la cartera simulada; abrir la pestaña o actualizar datos nunca ejecuta stops.
- `PaperTradingEngine.review_risk_and_snapshot()` adquiere `BEGIN IMMEDIATE`, valida precio actual y stop de cada posición, cierra las posiciones activadas y guarda la valoración posterior dentro de la misma transacción SQLite.
- Un precio ausente/no finito, un stop inválido o un fallo de persistencia revierte el ciclo completo. Dos revisiones concurrentes pueden guardar dos snapshots, pero no duplicar una venta por stop.
- Las órdenes simuladas muestran `reason=stop_loss` y su identificador en la trazabilidad visible. No hay llamadas a brokers ni credenciales en este flujo.

## Deuda aún fuera de Fase 1

- Tipado estático.
- Retirada de legacy tras el ciclo de compatibilidad.
