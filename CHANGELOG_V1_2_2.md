# ELAN Quantum v1.2.2 — Core Cleanup

Estado: preparado localmente en `feature/core-cleanup`; sin push, merge ni tag.

## Identidad visual

- La interfaz adopta la identidad ELAN midnight navy: fondo `#141654`, tipografía dorada `#D8B511` y superficies azul profundo.
- Sidebar, controles, tablas, bordes y jerarquía tipográfica comparten un tema nativo de Streamlit, sin acoplar colores a selectores CSS internos.
- Los gráficos usan una paleta financiera común de oro, turquesa, azul, coral y violeta; la matriz de correlación emplea una escala divergente específica para riesgo.
- La cabecera comunica una presentación más aspiracional sin alterar el flujo cuantitativo ni añadir funciones de inversión.

## Corregido

- El optimizador institucional respeta siempre `max_weight` y rechaza restricciones matemáticamente inviables con un mensaje claro.
- Ruff y Black quedan en verde en todo el proyecto.
- La colisión de import entre `portfolio.py` y `portfolio/` queda eliminada.
- Versión sincronizada a 1.2.2 en paquete, YAML y `pyproject.toml`.
- Configuración de intervalo e histórico mínimo de mercado conectada al proveedor real.

## Integridad del backtest

- Comisión y slippage configurables se aplican solo al turnover ejecutado; la UI compara estrategia neta, bruta y benchmark configurado. Las señales se ejecutan una barra después y cinco regresiones cubren costes, benchmark ausente y ausencia de look-ahead.

## Fiabilidad del mercado

- Yahoo usa timeout, reintentos acotados y backoff exponencial configurables; cada activo que agota sus intentos devuelve un error parcial claro sin inventar precios.
- La caché persistente usa CSV inerte con TTL, nombres SHA-256 y reemplazo atómico. El código ya no escribe ni lee pickle y las pruebas del cliente no dependen de internet.

## Fiabilidad de paper trading

- Compras, ventas, reset y snapshots usan transacciones explícitas. SQLite opera en WAL con timeout; escritores concurrentes se serializan antes de leer saldo o posición. Los fallos revierten efectivo, posiciones y órdenes, y la UI recibe mensajes seguros mientras el detalle queda en logs.
- Venta y reset fallan cerrados si falta la fila única de cuenta: ninguna posición u orden se modifica sin poder actualizar también el efectivo autoritativo.
- La app incorpora una revisión manual y confirmada de stops simulados. Validación de precios, cierres por `stop_loss` y snapshot posterior forman una sola transacción; faltantes, datos inválidos o errores SQLite no dejan cambios parciales.
- La trazabilidad visible lista las órdenes simuladas y el histórico de patrimonio se alimenta solo cuando el usuario ejecuta el control. No se añadió automatización ni conexión con brokers.

## Arquitectura estabilizada

- `CoreEngine` es el pipeline canónico.
- `portfolio.engine` es el Portfolio Engine canónico.
- `BacktestEngine` es el Backtesting Engine canónico y el dashboard lo usa directamente.
- Los imports históricos siguen funcionando mediante adaptadores.
- Las implementaciones desplazadas se preservan bajo `src/elan_ai_invest/legacy/`.

## Calidad y CI

- Pruebas añadidas para límites factibles e inviables, resolución de imports, pipeline, Portfolio Engine, Backtesting Engine, sincronización de versión y ciclo stop/snapshot (rollback, datos inválidos, concurrencia y confirmación Streamlit).
- GitHub Actions incluye Python 3.14 además de 3.11–3.13.
- `requirements.lock` fija las dependencias transitivas y la cadena pip/setuptools/wheel; CI, `install.bat` y `update.bat` consumen el mismo contrato y un verificador detecta drift.
- `.gitattributes` define LF para código/documentación y CRLF para `.bat`.
- Streamlit usa renderizado condicional de pestañas, cachés acotadas y `width="stretch"`.
- Pytest mide líneas y ramas de `app.py` y todo el paquete: baseline validado de 77,5 % y gate mínimo de 75 % en local y CI.
- AppTest recorre el flujo principal y todas las vistas con datos deterministas; cualquier intento de consultar Yahoo hace fallar la prueba.
- La cobertura integral detectó y corrigió una colisión de `volatility_pct` que impedía abrir Cartera; la volatilidad del Risk Engine es ahora la fuente autoritativa tras el merge.
- CI valida la secuencia `trabajo → develop → main` y rechaza integraciones directas de una feature en `main`; Dependabot propone cambios sobre `develop`.
- `GIT_WORKFLOW.md` registra el snapshot local, las protecciones remotas requeridas y los comandos de integración aún no ejecutados.

## Distribución limpia

- `scripts/build_distribution.py` construye el ZIP solo desde archivos confirmados en Git; los cambios locales, `.git`, `.venv`, bases, logs, cachés y nombres sensibles no pueden entrar.
- El artefacto contiene `data/` y `logs/` vacíos, conserva el código, configuración, documentación, tests y lockfile, y añade un manifiesto con versión, commit, tamaños y hashes SHA-256.
- El proceso es determinista, verifica el ZIP después de crearlo y forma parte del gate de GitHub Actions. El ZIP histórico no se modificó ni se eliminó.

## Compatibilidad y límites

- No se añadió funcionalidad de inversión ni conexión con brokers.
- No se eliminaron tests ni implementaciones antiguas.
- El stop-loss/snapshot de UI es deliberadamente manual; no existe ejecución automática. Sigue fuera de alcance la retirada de legacy.
- La copia activa está en `C:\Users\elanv\Desktop\ELAN AI INVESTMENT`; su entorno virtual no fue reinstalado ni modificado y las validaciones fuerzan `PYTHONPATH=src`.

## Gates de cierre

El cierre exige pytest, Ruff, Black, healthcheck, import-all, Streamlit health, `git diff --check` y working tree limpio. Los resultados exactos se registran en `AUDIT_REPORT.md`.
