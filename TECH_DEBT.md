# Deuda técnica de ELAN Quantum

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
| TD-010 | P1 | Rendimiento | 11 pestañas eager ejecutan contenido oculto | Reruns lentos, red y DB innecesarios | Tabs dinámicos/condicionales o navegación; medir |
| TD-011 | P1 | Mercado | Descargas Yahoo secuenciales, sin timeout/retry/backoff ni caché persistente activa | Arranque lento y frágil | Política de cliente, caché acotada y pruebas con dobles |
| TD-012 | P1 | Config | Múltiples campos YAML son ignorados o hardcoded | El usuario cree configurar algo que no cambia | Matriz campo-consumidor y tests de configuración |
| TD-013 | P1 | Paper | Stop-loss y snapshots existen pero no se llaman desde la app | Protección e histórico anunciados no operan automáticamente | Definir evento explícito y visible; no automatizar dinero real |
| TD-014 | P1 | Paper/DB | Compra/venta lee saldo/posición antes de escribir sin condición atómica | Carrera entre sesiones y saldo inconsistente | `BEGIN IMMEDIATE`/update condicional; test concurrente |
| TD-015 | P1 | Healthcheck | “Base accesible” solo comprueba carpeta padre; además crea carpetas antes | Falso positivo operativo | Abrir DB, validar esquema y realizar transacción reversible |
| TD-016 | P1 | Reproducibilidad | No hay lockfile; rangos abiertos y `requirements.txt=-e .[dev]` | Reinstalaciones no deterministas | Elegir uv/pip-tools y bloquear por plataforma soportada |
| TD-017 | P1 | Distribución | ZIP incluye `.venv`, `.git`, logs y bases SQLite | No portable; posible fuga de estado local | Artefacto limpio con exclusiones y datos vacíos |
| TD-018 | P1 | Pruebas | Sin cobertura; dashboard, Yahoo, configuración efectiva y límites críticos poco cubiertos | 30 tests pasan sin validar el flujo visible completo | Cobertura por riesgo, AppTest y mocks de proveedor |
| TD-019 | P1 | Ramas | `main` permanece en 0.1; trabajo actual está sobre feature con cambios no consolidados | Flujo de release incoherente | Política `feature -> develop -> main`, sin saltos |
| TD-020 | P2 | Duplicación | `safe_render` existe en `layout.py` y `safe.py` con mensajes/retornos distintos | Conducta inconsistente | Una función pública con contrato tipado |
| TD-021 | P2 | Código muerto | 40 módulos no alcanzables desde `app.py`; varios son stubs | Superficie y confusión innecesarias | Inventario de consumidores, deprecación y cuarentena antes de borrar |
| TD-022 | P2 | Seguridad | `market.cache` usa `read_pickle` | Ejecución de código si el archivo es hostil | Formato seguro (Parquet) o directorio confiable validado |
| TD-023 | P2 | Seguridad/UI | `st.exception` y mensajes crudos de excepción llegan al usuario | Filtración de rutas/detalles en remoto | ID de error al usuario, detalle solo en log |
| TD-024 | P2 | Streamlit | 22 usos de `use_container_width` deprecado | Ruido y futura incompatibilidad | `width="stretch"` o default, en commit mecánico |
| TD-025 | P2 | Streamlit | CSS inyectado con `unsafe_allow_html=True` | Fragilidad frente a cambios internos | Tema `.streamlit/config.toml` versionado de forma selectiva |
| TD-026 | P2 | Tipado | 88/128 funciones totalmente anotadas; no hay mypy/pyright | Errores de contratos no detectados | Tipar primero core, cartera, riesgo, paper y dashboard público |
| TD-027 | P2 | Dependencias | `python-dotenv` declarado sin uso encontrado | Mantenimiento/superficie extra | Confirmar consumidor y retirar en cambio separado |
| TD-028 | P2 | Python | `.venv` usa 3.14.5; CI solo 3.11–3.13 | Diferencias no probadas | Añadir 3.14 o fijar máximo soportado |
| TD-029 | P2 | Git | `core.autocrlf=true`, sin `.gitattributes`, muchos avisos LF/CRLF | Diffs y estados falsamente sucios | Política EOL y renormalización aislada |
| TD-030 | P2 | Docs | README/ROADMAP/architecture/CHANGELOG no reflejan 1.2.1 real | Operación y decisiones erróneas | Docs generadas desde estado validado |
| TD-031 | P2 | Scripts | `update.bat` elimina siete scripts por nombre | Actualización destructiva y difícil de auditar | Migración con backup/confirmación o eliminación en Git |
| TD-032 | P2 | Riesgo | Retornos rellenan faltantes con 0 después de forward-fill | Correlación/VaR sesgados con historiales desiguales | Política de calendario y test de datos incompletos |
| TD-033 | P2 | Logging | `configure_logging` reutiliza handlers globales sin comprobar root/config | Tests o instancias múltiples pueden escribir al destino anterior | Configuración idempotente por handler/ruta |
| TD-034 | P2 | Versionado | `pyproject`/paquete dicen 1.2.1 y YAML 1.2.1-stability | Versiones visibles distintas | Fuente única de versión |
| TD-035 | P3 | Tests | `test_backtesting.py` y `test_backtesting_pro.py` repiten casi el mismo caso | Poco valor por mantenimiento | Convertir uno en casos de costes/benchmark |
| TD-036 | P3 | UX | `app.py` monolítico y entrada no convencional | Escalabilidad limitada | Router/páginas solo tras estabilizar dominio |
| TD-037 | P3 | Calidad | Sin pruebas de propiedades para sumas de pesos, cash y contabilidad | Casos límite reaparecen | Hypothesis o parametrización exhaustiva |

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
- Paper trading concurrente, rollback y errores SQLite.
- Configuración: cada campo cambia efectivamente el comportamiento.
- Streamlit AppTest con proveedor falso y sin red.
- Yahoo: timeout, errores parciales, columnas MultiIndex y rate limiting con mocks.
- Seguridad: no exponer detalles y no cargar pickle no confiable.

