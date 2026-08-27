# Changelog

## Unreleased
- Cerrada la Fase 7B: mypy estricto cubre los 118 módulos del paquete y un
  manifiesto verificable clasifica 86 activos, 13 adaptadores de compatibilidad
  y 19 módulos legacy, sin borrar ni alterar sus contratos públicos.
- Endurecido `requirements.lock` con hashes SHA-256 para sus 80 pins activos;
  CI, instaladores y matriz local instalan primero el cierre verificado y luego
  el proyecto editable sin resolver dependencias.
- Añadidos el regenerador/comprobador del lock y el gate de ciclo de vida; la
  compatibilidad de artefactos se comprobó para Python 3.11–3.14 y la auditoría
  final no encontró vulnerabilidades conocidas.
- Ampliado el gate de mypy a 62 archivos del producto activo, incluidos
  dashboard, fundamental, market y backtesting, sin modificar scoring,
  cartera, riesgo ni paper trading.
- Añadida a CI una auditoría bloqueante de `requirements.lock` con
  `pip-audit` fijado por SHA; actualizados GitPython y pip a versiones sin
  vulnerabilidades conocidas en la auditoría local.
- Ampliado el catálogo principal a 54 criptoactivos con histórico verificado
  en Yahoo (30 crypto, 11 stablecoins y 13 memecoins), incluido USDT/USDC,
  y añadido el filtro agregado `Criptoactivos (todos)`. Las CBDC quedan
  explícitamente fuera al no ser instrumentos cotizados.
- Movida la navegación de las 13 vistas a un selector superior compacto y
  responsive; unificada la tipografía mediante el tema nativo de Streamlit,
  sin CSS inyectado y conservando la carga perezosa.
- Sustituido el universo FX fijo por un catálogo maestro de monedas y pares
  virtuales `FX_BASE_QUOTE`, sin almacenar combinaciones redundantes.
- Añadidos routing directo/inverso/sintético, históricos OHLC alineados en UTC,
  log returns, cobertura, KPIs, validación triangular y caché CSV persistente.
- Renovada la pestaña Divisas con búsqueda por moneda/país/par, botón invertir,
  trazabilidad de cálculo y comparador FX con acciones, índices, materias primas
  y criptomonedas.
- Sincronizado el catálogo con 155 monedas ISO 4217 activas: 128 con histórico
  mínimo utilizable en Yahoo, 27 visibles como no disponibles y 16.256 pares
  virtuales generados bajo demanda.
- Añadido un sincronizador reproducible contra SIX/Yahoo y un panel de cobertura
  que distingue disponibilidad de datos de convertibilidad o negociabilidad.
- Unificado el buscador principal con el catálogo FX maestro: los filtros de
  divisa, país, mercado y texto exponen 127 pares directos derivados de las 128
  monedas habilitadas y dejan de usar las cuatro filas Forex heredadas.
- Integrados los pares virtuales `FX_BASE_QUOTE` en el buscador y el
  `CoreEngine` mediante un proveedor compuesto Yahoo/FX: ahora participan en
  calidad, ranking, riesgo, gráficos, correlaciones y Terminal de Decisión.
- Mantenidas las divisas fuera de cartera y paper trading; Fundamental muestra
  PER y métricas corporativas como `N/D`.
- Añadida trazabilidad FX al motor principal: el panel Mercado distingue
  resolución directa, inversa o sintética y muestra proveedor, ruta de cálculo,
  cobertura de la ruta, cobertura temporal y frescura sin alterar precios,
  scoring ni decisiones.
- Añadida una decimotercera pestaña lazy para comparar entre dos y doce divisas.
- Ampliado el universo FX a 15 monedas y el máximo seleccionable a 12.
- Normalizadas las cotizaciones a USD por unidad de divisa antes de calcular
  desempeño base 100, matriz de correlaciones y correlación móvil.
- Alineadas las sesiones sin forward-fill ni retornos cero inventados, con caché
  de mercado de 15 minutos y pruebas deterministas sin red.
- Mostrado el PER histórico en el panel principal y en Fundamental para la acción seleccionada.
- Ampliado el catálogo curado con criptomonedas, stablecoins y memecoins principales compatibles con Yahoo; el PER queda limitado a acciones.
- Movido el selector buscable del activo principal por encima de los KPI, aclarando que procede del Universo activo y sincronizándolo con todas las vistas.
- Ampliado el comparador de Mercado a una selección simultánea de entre dos y
  ocho instrumentos focales, con desempeño conjunto, matriz de correlaciones y
  correlación móvil de una referencia frente a todos sus comparables.
- Sincronizados los horizontes global y local de Mercado para que cambiar entre
  un mes, uno, dos, cinco o diez años y máximo recargue tanto el histórico del
  activo como el desempeño comparable.
- Optimizada la visualización de diez años y máximo con agregación OHLCV
  semanal/mensual y selector de escala lineal o logarítmica, manteniendo las
  métricas sobre todas las sesiones diarias.

- Conectado un activo global entre Mercado, Inteligencia, Fundamental, Noticias y Ranking.
- Añadida selección por fila en Ranking e Inteligencia y una barra de contexto con precio, score, señal y volatilidad.
- Aislados los controles locales de histórico y comparador mediante fragmentos de Streamlit, preservando la carga lazy y la semántica financiera existente.
- Forzado el renderizado SVG del comparador para funcionar también en navegadores sin WebGL.
- Persistida en SQLite la lista de `Universo activo` para restaurarla tras recargas y reinicios.
- Elevado el gate local a 192 pruebas y 81,49 % de cobertura.

- Añadido News & Events Engine v1 con noticias recientes y próximos resultados, dividendos y fechas ex-dividendo desde Yahoo Finance.
- Incorporada una duodécima pestaña de carga perezosa, caché configurable de 15 minutos y límite de 50 entradas.
- Aislados los fallos de noticias y calendario sin modificar scoring, señales, riesgo, cartera ni paper trading.

- Añadido un reporte de calidad por instrumento con frescura, cobertura, huecos, disponibilidad y procedencia proveedor/caché.
- Incorporados estados saludables, degradados, obsoletos, insuficientes y no disponibles sin rellenar ni alterar precios.
- Mostrado en Mercado el estado global del proveedor, cobertura media, incidencias y detalle del OHLCV visible.
- Elevado el gate local a 162 pruebas y 81,17 % de cobertura.
- Añadido un buscador global offline por símbolo, nombre, alias, ISIN, país y bolsa.
- Añadidos filtros de tipo de activo, país y mercado, selección incremental y entrada manual Yahoo.
- Incorporada una instantánea MIT de Adanos con 63.185 acciones/ETF de 91 países.
- Separado explícitamente el catálogo de descubrimiento del proveedor Yahoo de históricos.
- Añadido al primer tab un panel OHLCV con horizontes de un mes a máximo histórico y vistas de velas, línea, rentabilidad y volumen.
- Añadido un comparador base 100 con dispersión y correlación móvil sobre rendimientos diarios alineados.

## 1.3.0rc1 — Release candidate

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
- Promovida la base validada mediante la PR #6 a `main`; la CI posterior pasó en Python 3.11–3.14.
- Preparada la metadata PEP 440 `1.3.0rc1` como candidata.
- Promovida la candidata mediante la PR #10 a `main` (`3c4cc72`), con CI posterior verde en Python 3.11–3.14.
- La publicación de una GitHub Release y cualquier despliegue permanecen fuera de este hito.

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
