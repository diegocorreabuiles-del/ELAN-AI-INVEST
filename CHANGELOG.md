# Changelog

## Unreleased — Recuperación del entorno

- Reconstruida y documentada la política Git `trabajo -> develop -> main`.
- Añadido un gate local/CI que valida nombres de rama y transiciones permitidas.
- Reconstruido el cierre reproducible de dependencias para Python 3.11–3.14.
- Los instaladores verifican el lock y ejecutan `pip check` después de instalar.
- Reconstruido el empaquetador desde `HEAD`, con manifiesto SHA-256 y verificación segura sin extracción.
- Añadidas regresiones para reproducibilidad, estado local, rutas, credenciales, enlaces y manipulación del ZIP.
- Recuperado AppTest sin red para el flujo principal, las once vistas y las acciones paper simuladas.
- Elevado el baseline local de cobertura a 81,0 % con 121 pruebas superadas, superando el gate del 75 %.
- Validada localmente en Docker la matriz Linux Python 3.11–3.14: lock, `pip check`, Ruff, Black, 116 pruebas y distribución reproducible.
- Cerradas correctamente las conexiones SQLite creadas por los tests de atomicidad.
- Publicada la rama recuperada mediante el PR #1 hacia `develop`; CI remota Python 3.11–3.14 verde.
- Protegidas `develop` y `main` con PR y checks obligatorios, historial lineal y bloqueo de force-push/borrado.
- Integrado el PR #1 en `develop` mediante rebase, con la matriz posterior al merge verde.
- Actualizadas las Actions oficiales a `checkout@v7` y `setup-python@v7`, ambas sobre Node 24.
- Integrado el PR #2 en `develop` mediante rebase, con matriz posterior al merge verde y sin avisos de Node 20.
- Renovada la interfaz Streamlit con un workspace grafito, acentos verde/rojo, tarjetas responsive y controles nativos; sin cambios en lógica financiera.
- Integrado el PR #3 en `develop` mediante rebase, con la matriz Python 3.11–3.14 verde.
- Sustituidos `st.exception` y mensajes crudos por referencias de soporte; el detalle queda solo en logging.
- El healthcheck inicializa y valida esquemas SQLite, ejecuta `quick_check` y prueba escritura con rollback.
- Riesgo calcula correlación, volatilidad y VaR únicamente con retornos consecutivos alineados, sin rellenar huecos con cero.
- Verificado por regresión que las once pestañas Streamlit solo renderizan su contenido al abrirse y que no quedan APIs de ancho deprecadas.
- Añadido mypy al entorno de desarrollo y a CI para 12 módulos críticos de core, cartera, riesgo, paper trading, sistema y UI segura.
- Endurecido paper trading para revertir la transacción si SQLite no devuelve identificador de orden.
- Hecho idempotente el logging por handler, ruta, rotación y nivel, sin reutilizar destinos obsoletos.
- Convertida la metadata instalada desde `pyproject.toml` en fuente de la versión visible; una versión YAML divergente se rechaza.
- Retirada la dependencia directa `python-dotenv`, que no tenía consumidor, y actualizado el lock a 78 pins activos.
- Eliminado del actualizador el borrado automático de siete scripts históricos.
- Elevado el baseline local a 123 pruebas y 81,1 % de cobertura.
- No se ha integrado `develop` en `main` ni publicado una release, un tag o un artefacto.

## 1.2.2 — Core Cleanup

- Corregido el cumplimiento de `max_weight` y los casos inviables del optimizador institucional.
- Seleccionados `CoreEngine`, `portfolio.engine` y `BacktestEngine` como implementaciones canónicas.
- Preservadas las implementaciones anteriores bajo `legacy/` y mediante adaptadores.
- Conectada configuración efectiva de mercado, cartera, backtest y paper trading.
- CI, Ruff, Black, Python 3.14 y política LF/CRLF estabilizados.
- Detalle completo en `CHANGELOG_V1_2_2.md`.

## 0.7.0
- Scripts únicos: `install.bat`, `update.bat` y `run.bat`.
- Añadido `MASTER_PLAN.md` como hoja de ruta principal.
- Añadido estado del sistema en el dashboard.
- Añadido health check ejecutable.
- Añadida integración continua con GitHub Actions.
- Añadido Dependabot para dependencias.
- Añadidas pruebas del estado del sistema.

## v0.5.0
- Portfolio Engine.
- Cartera simulada de 100.000 EUR.
- Perfil moderado por defecto.
- Limites por posicion y liquidez minima.
- Comparacion historica con SPY.

# Changelog

## 0.3.0
- Añadido Core Engine para coordinar el análisis.
- Añadida configuración central en YAML y validación con Pydantic.
- Añadido proveedor abstracto de datos y adaptador Yahoo.
- Añadido logging en consola y archivo rotatorio.
- Integración del dashboard con el Core Engine.
- Nuevas pruebas de configuración y orquestación.

## 0.3.1

- Convertido el proyecto en paquete Python instalable mediante `pyproject.toml`.
- Añadida instalación editable con `pip install -e .[dev]`.
- Corregida la detección del paquete `elan_ai_invest` en pytest y Streamlit.
- Añadidas configuraciones de pytest, Ruff y Black.
- Mejorados los scripts de actualización e inicio para Windows.
- Eliminados archivos de caché del paquete distribuido.

## 0.4.0
- Nuevo nombre: ELAN Quantum.
- Risk Engine con VaR, CVaR, volatilidad, drawdown y correlaciones.
- Contribución al riesgo y tamaño orientativo de posición.
- Nueva pestaña de riesgo en el dashboard.

## 0.6.0
- Añadido Paper Trading Engine persistente en SQLite.
- Compras y ventas simuladas con comisión.
- Stop-loss automático y límite de posiciones.
- Valoración, P&L e historial de operaciones.
- Nueva pestaña Paper Trading y pruebas automáticas.

## 1.0.0-alpha
- Dashboard modular.
- Intelligence, indicators, decision and backtesting packages.
- Stable portfolio compatibility layer.
- Integrated test suite.

## 1.1.0 Professional
- Nuevo Quant Factor Engine.
- Fuerza relativa frente al benchmark.
- Rentabilidad ajustada por riesgo y calidad de tendencia.
- Decisiones COMPRAR/VIGILAR/NEUTRAL/EVITAR.
- Explicaciones automáticas y pestaña Inteligencia.

## 1.2.0 Institutional

- Fundamental Engine con scoring de calidad, crecimiento, valoración, balance y caja.
- Proveedor fundamental Yahoo con carga bajo demanda y caché de Streamlit.
- Portfolio Optimizer Institutional: paridad de riesgo, mínima varianza, máxima diversificación y pesos iguales.
- Nuevas pestañas Fundamental e Institucional.
- Pruebas unitarias del motor fundamental y del optimizador institucional.

## 1.2.1 Stability

- Protección de arranque y análisis.
- Aislamiento de errores por pestaña.
- Healthcheck ampliado.
- Importaciones opcionales más robustas.
- Configuración de tests independiente de la instalación editable.
- Sincronización de versión.
