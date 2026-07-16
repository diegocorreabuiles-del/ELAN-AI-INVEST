# ELAN Quantum v1.2.2 — Core Cleanup

Estado: preparado localmente en `feature/core-cleanup`; sin push, merge ni tag.

## Corregido

- El optimizador institucional respeta siempre `max_weight` y rechaza restricciones matemáticamente inviables con un mensaje claro.
- Ruff y Black quedan en verde en todo el proyecto.
- La colisión de import entre `portfolio.py` y `portfolio/` queda eliminada.
- Versión sincronizada a 1.2.2 en paquete, YAML y `pyproject.toml`.
- Configuración de intervalo e histórico mínimo de mercado conectada al proveedor real.

## Arquitectura estabilizada

- `CoreEngine` es el pipeline canónico.
- `portfolio.engine` es el Portfolio Engine canónico.
- `BacktestEngine` es el Backtesting Engine canónico y el dashboard lo usa directamente.
- Los imports históricos siguen funcionando mediante adaptadores.
- Las implementaciones desplazadas se preservan bajo `src/elan_ai_invest/legacy/`.

## Calidad y CI

- Pruebas añadidas para límites factibles e inviables, resolución de imports, pipeline, Portfolio Engine, Backtesting Engine y sincronización de versión.
- GitHub Actions incluye Python 3.14 además de 3.11–3.13.
- `.gitattributes` define LF para código/documentación y CRLF para `.bat`.
- Streamlit usa renderizado condicional de pestañas, cachés acotadas y `width="stretch"`.

## Compatibilidad y límites

- No se añadió funcionalidad de inversión ni conexión con brokers.
- No se eliminaron tests ni implementaciones antiguas.
- No se incluye todavía costes/slippage completos, atomicidad de paper trading, lockfile ni retirada de legacy.
- El entorno virtual no fue modificado; para validar esta copia se fuerza `PYTHONPATH=src` porque el editable recibido apunta a otra carpeta.

## Gates de cierre

El cierre exige pytest, Ruff, Black, healthcheck, import-all, Streamlit health, `git diff --check` y working tree limpio. Los resultados exactos se registran en `AUDIT_REPORT.md`.
