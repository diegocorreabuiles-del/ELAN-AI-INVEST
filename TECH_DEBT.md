# Deuda técnica de ELAN Quantum

> **Revisión tras la migración de PC (22 de julio de 2026).** El release candidate local pasa 123 pruebas y alcanza 81,1 % de cobertura; lock, mypy crítico, Ruff, Black, healthcheck, AppTest, empaquetado y aislamiento de Yahoo/SQLite forman el gate. La matriz Linux Python 3.11–3.14 se vuelve a ejecutar antes de integrar. Las afirmaciones posteriores se conservan como registro histórico y solo coinciden con el estado actual cuando esta nota las confirma.

> Estado v1.3.0rc1: TD-001–TD-011 y TD-013–TD-038 quedan resueltos o mitigados salvo TD-012. TD-007 queda mitigado con `CoreEngine` canónico y legacy congelado; TD-021 dispone de clasificación verificable y TD-026 cubre los 118 módulos. TD-019 quedó cerrado con la promoción de la PR #6 a `main` y su CI posterior verde.

Escala: P0 bloquea/rompe; P1 importante; P2 mejora; P3 futuro.

## Registro de hallazgos

| ID | Prioridad | Área | Hallazgo y evidencia | Riesgo | Tratamiento propuesto |
|---|---|---|---|---|---|
| TD-001 | P0 | CI | Ruff falla con 8 incidencias | Ningún PR pasa el workflow actual | Commit mecánico de lint, sin cambio funcional |
| TD-002 | P0 | CI | Black rechaza 36 archivos | CI roja y diffs futuros ruidosos | Formateo aislado y revisión de diff |
| TD-003 | P0 | Cálculo | `institutional._normalise` devuelve 33,33 % con 3 activos y cap 25 % | Incumple una restricción financiera explícita | Validar factibilidad o permitir efectivo; test de propiedad |
| TD-004 | P0 | Release/Git | 57 archivos con diff material y módulos 1.2.1 sin commit sobre Sprint 10 | Release no atribuible ni reversible | Baseline preservado y commits por tema antes de v1.3 |
| TD-005 | P1 | Imports | `portfolio.py` y `portfolio/` comparten nombre importable | Implementación sombreada y API ambigua | Elegir canónica, adaptador temporal y prueba de resolución |
| TD-006 | P1 | Cartera | Las dos implementaciones de cartera divergen en campos, redistribución, riesgo y cash | Resultados distintos según la ruta elegida | Especificar invariantes y consolidar |
| TD-007 | P1 | Arquitectura | `CoreEngine` y `InvestmentPipeline` implementan pipelines incompatibles | Doble mantenimiento y decisiones contradictorias | ADR de pipeline canónico; congelar legacy |
| TD-008 | P1 | Backtest | `backtest.py` y `backtesting/` se superponen; UI y tests validan motores distintos | Falsa confianza en lo que ve el usuario | Un único motor productivo y tests sobre la misma ruta |
| TD-009 | P1 | Backtest | UI no aplica costes, slippage, benchmark configurado ni fuera de muestra | Métricas optimistas y no profesionales | Integrar costes/benchmark; declarar supuestos |
| TD-010 | P1 | Rendimiento | Resuelto: las 11 pestañas usan `on_change="rerun"` y cada vista está guardada por `tab.open` | El contenido oculto no ejecuta red, DB ni cálculos de su vista | Mantener el contrato en `test_streamlit_contracts.py`; migrar a multipágina solo si el tamaño lo justifica |
| TD-011 | P1 | Mercado | Resuelto: Yahoo aplica timeout y retry/backoff configurables; los aciertos se sirven desde caché CSV con TTL | Seis pruebas sin red cubren éxito tras fallos, agotamiento, caché, corrupción, configuración y conexión bootstrap | Mantener métricas operativas y revisar paralelismo en otra fase |
| TD-012 | P1 | Config | Múltiples campos YAML son ignorados o hardcoded | El usuario cree configurar algo que no cambia | Matriz campo-consumidor y tests de configuración |
| TD-013 | P1 | Paper | Resuelto: la app ofrece una revisión manual y confirmada que ejecuta stops simulados y guarda el snapshot posterior en una única transacción | Sin confirmación no hay cambios; precios o stops inválidos fallan cerrados; la concurrencia no duplica ventas | Mantener el evento manual y local; no conectarlo a brokers ni automatizarlo sin un diseño y aprobación independientes |
| TD-014 | P1 | Paper/DB | Resuelto: compras, ventas y reset usan `BEGIN IMMEDIATE`; el efectivo se actualiza con condición y toda mutación exige una única fila de cuenta | Escritores concurrentes se serializan; una cuenta ausente o un fallo de orden provoca rollback sin perder posición, efectivo ni trazabilidad | Mantener regresiones concurrentes, de bloqueo, rollback SQLite y cuenta ausente |
| TD-015 | P1 | Healthcheck | Resuelto: el script inicializa los esquemas canónicos y el estado abre cada SQLite, ejecuta `quick_check`, valida tablas y prueba escritura dentro de una transacción revertida | Una DB ausente, incompleta, corrupta o no escribible deja el estado en error; la tabla de prueba no persiste | Mantener regresiones de esquema, integridad y rollback |
| TD-016 | P1 | Reproducibilidad | Resuelto: `requirements.lock` fija el cierre transitivo con hashes SHA-256 y `requirements.txt`, CI e instaladores lo consumen en modo `--require-hashes` | `check_lock.py` valida 80 pins activos, hashes y entorno; `pip check` pasa | Regenerar con `scripts/generate_hashed_lock.py` y ejecutar la matriz antes de cada release |
| TD-017 | P1 | Distribución | Resuelto: `scripts/build_distribution.py` empaqueta exclusivamente archivos confirmados en Git y crea `data/`/`logs/` vacíos | El verificador bloquea `.git`, `.venv`, bases, logs, cachés, credenciales y rutas inseguras; el manifiesto registra hashes y commit | Mantener el gate en CI y distribuir solo artefactos que superen la verificación |
| TD-018 | P1 | Pruebas | Resuelto tras la recuperación: el gate local supera 123 pruebas, cubre líneas y ramas al 81,1 % y mantiene el umbral CI de 75 % | AppTest ejecuta `app.py`, las once vistas y acciones paper simuladas con datos deterministas; Yahoo queda aislado y SQLite usa rutas temporales | Aumentar el umbral gradualmente y cubrir rutas de error/legacy solo según riesgo demostrado |
| TD-019 | P1 | Ramas | Resuelto: `check_git_flow.py`, CI y protecciones aplican `trabajo -> develop -> main`; la PR #6 fue promovida a `main` y la CI posterior pasó en Python 3.11–3.14 | El bypass administrativo queda solo para recuperación | Mantener el mismo flujo y exigir autorización explícita para futuras promociones a `main` |
| TD-020 | P2 | Duplicación | Resuelto: `dashboard.safe.safe_render` es la única implementación y `layout.py` solo la reexporta | Un test de identidad fija el contrato público | Mantener la frontera tipada y los mensajes seguros en `dashboard.safe` |
| TD-021 | P2 | Código muerto | Mitigado en 7B: manifiesto y gate clasifican 118 módulos en 86 activos, 13 de compatibilidad y 19 legacy | Los módulos no activos no son alcanzables desde `app.py`; los adaptadores conservan consumidores en tests y no se borró legacy | Mantener el manifiesto sincronizado y exigir un cambio dedicado antes de cualquier retirada |
| TD-022 | P2 | Seguridad | Resuelto: `MarketCache` ya no escribe ni lee pickle | CSV inerte, nombres SHA-256 y reemplazo atómico; los `.pkl` anteriores se ignoran | Mantener la caché generada fuera de Git |
| TD-023 | P2 | Seguridad/UI | Resuelto: arranque, análisis y vistas convierten fallos en mensajes neutros con referencia aleatoria | El detalle técnico y la referencia se conservan en logging; AppTest verifica que el texto de la excepción no aparece en la UI | Mantener la frontera en `dashboard.safe.show_safe_error` |
| TD-024 | P2 | Streamlit | Resuelto: no quedan usos de `use_container_width` | Un test recorre `app.py` y todo `src/` para impedir su reintroducción | Mantener APIs compatibles con la versión Streamlit bloqueada |
| TD-025 | P2 | Streamlit | Resuelto: el tema anterior dependía de CSS residual y una paleta azul/dorada poco orientada a trading | Tema nativo grafito, acentos verde/rojo, superficies, bordes, sidebar y gráficos coordinados; el CSS inyectado se retiró | Mantener contratos de paleta y QA responsive en futuras versiones de Streamlit |
| TD-026 | P2 | Tipado | Resuelto en 7B: mypy estricto cubre los 118 módulos del paquete sin exclusiones globales | Código activo, adaptadores de compatibilidad y legacy quedan bajo el mismo gate | Mantener cobertura total y no introducir exclusiones globales |
| TD-027 | P2 | Dependencias | Resuelto: `python-dotenv` no tenía consumidor directo ni transitivo y se retiró del proyecto y del lock | Menor superficie; `check_lock.py` y `pip check` pasan con 80 distribuciones, incluidas las herramientas de build fijadas | Mantener revisión de consumidores antes de retirar otras dependencias |
| TD-028 | P2 | Python | Resuelto: CI y `run_ci_matrix.ps1` cubren Python 3.11–3.14 | Las matrices remotas de `push` y PR pasan lock, lint, formato, pruebas, cobertura y empaquetado | Mantener ambas matrices alineadas antes de cada integración y release |
| TD-029 | P2 | Git | Resuelto: `.gitattributes` define LF para código/docs, CRLF para `.bat` y binario para DB/ZIP/PNG | Git aplica una política EOL estable y auditable | Mantener renormalizaciones separadas de cambios funcionales |
| TD-030 | P2 | Docs | Resuelto para el release candidate: README, arquitectura, changelog, plan de release y deuda reflejan el estado validado | Las cifras y gates proceden de ejecución local | Actualizar números de PR/matriz tras cada integración, sin reescribir historia |
| TD-031 | P2 | Scripts | Resuelto: `update.bat` ya no elimina scripts ni archivos por nombre | La actualización instala, valida y comprueba salud sin borrado automático | Cualquier retirada futura debe hacerse en Git y con revisión explícita |
| TD-032 | P2 | Riesgo | Resuelto: riesgo no hace forward-fill ni convierte huecos en retornos cero; usa únicamente retornos con precios consecutivos y alineados para todos los activos | Correlación, volatilidad y VaR comparten la misma muestra completa; menos de 60 sesiones alineadas falla explícitamente | Mantener pruebas con huecos internos, historiales desiguales e infinitos |
| TD-033 | P2 | Logging | Resuelto: handlers propios se identifican por nombre y se reutilizan solo si ruta/rotación coinciden | Reconfigurar cambia destino y nivel sin duplicar handlers ni conservar archivos anteriores | Mantener cierre explícito de handlers reemplazados y regresiones Windows |
| TD-034 | P2 | Versionado | Resuelto: `pyproject.toml` define la versión y `importlib.metadata` alimenta paquete, configuración, UI y healthcheck | YAML ya no duplica el valor y cualquier versión externa divergente falla al validar | Cambiar versión solo en el release commit canónico |
| TD-035 | P3 | Tests | `test_backtesting.py` y `test_backtesting_pro.py` repiten casi el mismo caso | Poco valor por mantenimiento | Convertir uno en casos de costes/benchmark |
| TD-036 | P3 | UX | `app.py` monolítico y entrada no convencional | Escalabilidad limitada | Router/páginas solo tras estabilizar dominio |
| TD-037 | P3 | Calidad | Sin pruebas de propiedades para sumas de pesos, cash y contabilidad | Casos límite reaparecen | Hypothesis o parametrización exhaustiva |
| TD-038 | P2 | Cadena de suministro | Resuelto en 7B: CI ejecuta `pip-audit` fijado por SHA y el lock exige hashes SHA-256 para 80 pins activos y todos sus artefactos publicados | La auditoría local no encontró vulnerabilidades; las descargas objetivo cubren Python 3.11–3.14 y la instalación 3.14 se validó de forma aislada | Mantener regenerador, auditoría y matriz remota como gates bloqueantes |

## Duplicados y solapamientos confirmados

- Colisión de módulo: `portfolio.py` / `portfolio/__init__.py`.
- Nombres duplicados divergentes: `PortfolioPlan`, `build_portfolio`, `portfolio_equity_curve`.
- Función duplicada: `safe_render`.
- Motores superpuestos: `backtest.py` / `backtesting/`.
- Proveedores superpuestos: `providers.yahoo + market_data` / `market.loader + market.providers`.
- Decisión/scoring superpuestos: `scoring + quant` / `indicators + intelligence + decision + advisor`.
- Tests redundantes: dos smoke tests del mismo `BacktestEngine`.
- No se encontraron archivos Python exactamente idénticos; la deuda es de duplicación divergente, más peligrosa que una copia exacta.

## Código posiblemente obsoleto — no borrar todavía

1. `advisor/` completo.
2. `core/pipeline.py` y su árbol `market/`, `indicators/`, `intelligence/`, `decision/`.
3. `backtesting/` si se decide mantener `backtest.py`, o viceversa.
4. `portfolio.py` o `portfolio/`, después de escoger contrato.
5. `portfolio/allocation.py`, `metrics.py`, `optimizer.py`, `rebalance.py`.
6. `dashboard/layout.safe_render`.

Antes de retirar cualquiera: buscar consumidores externos, añadir aviso de deprecación, mantener compatibilidad durante un ciclo y conservar la historia en Git.

## Pruebas faltantes prioritarias

- Restricciones inviables y factibles del optimizador institucional.
- Invariantes de cartera: suma invertido+cash=100, límites, capital y perfiles.
- Resolución de imports de cartera.
- Backtest con costes, benchmark, señales desplazadas y datos faltantes.
- Paper trading concurrente, rollback, errores SQLite y ciclo UI de stops/snapshot. **Completado con pruebas de motor y AppTest sin red.**
- Configuración: cada campo cambia efectivamente el comportamiento.
- Streamlit AppTest con proveedor falso y sin red. **Completado para `app.py`, todas las vistas y rutas de paper críticas.**
- Yahoo: timeout, errores parciales, columnas MultiIndex y rate limiting con mocks.
- Seguridad: no exponer detalles y no cargar pickle no confiable.
