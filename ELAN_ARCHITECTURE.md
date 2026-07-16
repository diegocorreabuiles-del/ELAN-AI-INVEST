# Arquitectura canónica de ELAN Quantum v1.2.2

Estado: arquitectura vigente tras la Fase 1 de estabilización. `ARCHITECTURE_CURRENT.md` conserva la fotografía anterior a la limpieza.

## Flujo de producción

```text
app.py (Streamlit)
  -> core.bootstrap.build_core_engine()
  -> core.engine.CoreEngine                         [pipeline canónico]
       -> providers.yahoo.YahooMarketDataProvider
       -> market_data.download_adjusted_close()
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

Los datos de mercado entran por el proveedor configurado, se validan con `market.interval` y `market.minimum_history`, y se convierten en un `AnalysisResult`. Todas las vistas reciben ese resultado común. Las pestañas costosas solo se renderizan cuando están abiertas; los cachés tienen TTL y límites de entradas.

## APIs canónicas

| Dominio | Implementación canónica | Compatibilidad temporal |
|---|---|---|
| Pipeline | `elan_ai_invest.core.CoreEngine` | `core.pipeline.InvestmentPipeline` reexporta la implementación congelada de `legacy.pipeline_v1` y avisa de deprecación al instanciarse |
| Cartera | `elan_ai_invest.portfolio.engine` | `elan_ai_invest.portfolio` reexporta la API canónica; la implementación anterior se conserva en `legacy.portfolio_package_v1` |
| Backtest | `elan_ai_invest.backtesting.engine.BacktestEngine` | `backtesting.momentum` y `backtest.py` delegan en el engine canónico |

## Invariantes relevantes

- El optimizador institucional nunca devuelve un peso superior a `max_weight`.
- Si `n_activos * max_weight < 1`, falla con un `ValueError` que explica la inviabilidad.
- Portfolio valida capital, posiciones, cap por posición y efectivo mínimo.
- En Portfolio, `invested_weight_pct + cash_weight_pct == 100` dentro de tolerancia numérica.
- Paper trading permanece desactivable por configuración y no tiene integración con brokers.

## Configuración conectada en esta fase

| Configuración | Consumidor |
|---|---|
| `market.period` | valor inicial de Streamlit y solicitud de análisis |
| `market.interval` | proveedor Yahoo y descarga |
| `market.minimum_history` | validación de series |
| `portfolio.*` | defaults y restricciones de `build_portfolio` |
| `backtest.lookback`, `top_n`, `rebalance_days` | controles del backtest visible |
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
- El `.venv` recibido conserva un enlace editable a otra copia del proyecto. Las validaciones de esta rama usan `PYTHONPATH=src` sin modificar el entorno.

## Deuda aún fuera de Fase 1

- Costes, slippage y supuestos profesionales del backtest.
- Atomicidad y concurrencia del paper trading.
- Retry/backoff y caché persistente segura para Yahoo.
- Cobertura cuantificada, tipado estático y lockfile reproducible.
- Retirada de legacy tras el ciclo de compatibilidad.
