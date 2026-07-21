# Deuda técnica de ELAN Quantum

> **Revisión tras la migración de PC (21 de julio de 2026).** TD-016, TD-017 y la parte local de TD-019 vuelven a estar verificadas: el lock, el empaquetador seguro y el gate Git han sido reconstruidos. TD-018 sigue reabierta: pasan 107 pruebas funcionales, pero la cobertura es 61,8 % y faltan las pruebas Streamlit/AppTest históricas. Las afirmaciones posteriores se conservan como registro del ordenador anterior y solo coinciden con el estado actual cuando esta nota las confirma.

> Estado v1.2.2: TD-001, TD-002, TD-003, TD-004, TD-005, TD-006, TD-008, TD-009, TD-011, TD-013, TD-014, TD-016, TD-017, TD-018 y TD-022 quedan resueltos. TD-007 queda mitigado con `CoreEngine` canónico y legacy congelado; TD-019 queda mitigado con política y gate `trabajo -> develop -> main`, a la espera de integración autorizada. TD-012, TD-024, TD-025, TD-028, TD-029 y TD-034 quedan parcial o totalmente tratados según `AUDIT_REPORT.md`. El resto sigue pendiente.

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
| TD-011 | P1 | Mercado | Resuelto: Yahoo aplica timeout y retry/backoff configurables; los aciertos se sirven desde caché CSV con TTL | Seis pruebas sin red cubren éxito tras fallos, agotamiento, caché, corrupción, configuración y conexión bootstrap | Mantener métricas operativas y revisar paralelismo en otra fase |
| TD-012 | P1 | Config | Múltiples campos YAML son ignorados o hardcoded | El usuario cree configurar algo que no cambia | Matriz campo-consumidor y tests de configuración |
| TD-013 | P1 | Paper | Resuelto: la app ofrece una revisión manual y confirmada que ejecuta stops simulados y guarda el snapshot posterior en una única transacción | Sin confirmación no hay cambios; precios o stops inválidos fallan cerrados; la concurrencia no duplica ventas | Mantener el evento manual y local; no conectarlo a brokers ni automatizarlo sin un diseño y aprobación independientes |
| TD-014 | P1 | Paper/DB | Resuelto: compras, ventas y reset usan `BEGIN IMMEDIATE`; el efectivo se actualiza con condición y toda mutación exige una única fila de cuenta | Escritores concurrentes se serializan; una cuenta ausente o un fallo de orden provoca rollback sin perder posición, efectivo ni trazabilidad | Mantener regresiones concurrentes, de bloqueo, rollback SQLite y cuenta ausente |
| TD-015 | P1 | Healthcheck | “Base accesible” solo comprueba carpeta padre; además crea carpetas antes | Falso positivo operativo | Abrir DB, validar esquema y realizar transacción reversible |
| TD-016 | P1 | Reproducibilidad | Resuelto: `requirements.lock` fija el cierre transitivo y `requirements.txt`, CI e instaladores lo consumen | `check_lock.py` rechaza pins ausentes o versiones distintas; NumPy se separa para 3.11 y 3.12–3.14 | Actualizar pins solo en un cambio dedicado y validar toda la matriz CI antes de release |
| TD-017 | P1 | Distribución | Resuelto: `scripts/build_distribution.py` empaqueta exclusivamente archivos confirmados en Git y crea `data/`/`logs/` vacíos | El verificador bloquea `.git`, `.venv`, bases, logs, cachés, credenciales y rutas inseguras; el manifiesto registra hashes y commit | Mantener el gate en CI y distribuir solo artefactos que superen la verificación |
| TD-018 | P1 | Pruebas | Resuelto para v1.2.2: 96 pruebas, cobertura de líneas y ramas del producto de 77,5 % y umbral CI de 75 % | AppTest ejecuta `app.py` y todas las vistas con datos deterministas; Yahoo queda bloqueado y los módulos críticos conservan sus regresiones | Aumentar el umbral gradualmente y cubrir rutas de error/legacy solo según riesgo demostrado |
| TD-019 | P1 | Ramas | Mitigado: `check_git_flow.py`, CI y Dependabot aplican `trabajo -> develop -> main`; la historia local es lineal y la candidata está consolidada | `main` sigue en 0.1 y la feature no tiene upstream porque no se autorizan push/merge; protecciones remotas no verificadas | Publicar la feature y crear PR a `develop`; después PR `develop -> main`, solo con autorización y gates remotos verdes |
| TD-020 | P2 | Duplicación | `safe_render` existe en `layout.py` y `safe.py` con mensajes/retornos distintos | Conducta inconsistente | Una función pública con contrato tipado |
| TD-021 | P2 | Código muerto | 40 módulos no alcanzables desde `app.py`; varios son stubs | Superficie y confusión innecesarias | Inventario de consumidores, deprecación y cuarentena antes de borrar |
| TD-022 | P2 | Seguridad | Resuelto: `MarketCache` ya no escribe ni lee pickle | CSV inerte, nombres SHA-256 y reemplazo atómico; los `.pkl` anteriores se ignoran | Mantener la caché generada fuera de Git |
| TD-023 | P2 | Seguridad/UI | `st.exception` y mensajes crudos de excepción llegan al usuario | Filtración de rutas/detalles en remoto | ID de error al usuario, detalle solo en log |
| TD-024 | P2 | Streamlit | 22 usos de `use_container_width` deprecado | Ruido y futura incompatibilidad | `width="stretch"` o default, en commit mecánico |
| TD-025 | P2 | Streamlit | CSS era la única personalización visual | Mitigado: identidad, tipografía, superficies, bordes, sidebar y gráficos ya usan `.streamlit/config.toml`; solo quedan dos reglas de espaciado/tamaño | Retirar esas reglas al existir equivalentes nativos estables |
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
- Paper trading concurrente, rollback, errores SQLite y ciclo UI de stops/snapshot. **Completado con pruebas de motor y AppTest sin red.**
- Configuración: cada campo cambia efectivamente el comportamiento.
- Streamlit AppTest con proveedor falso y sin red. **Completado para `app.py`, todas las vistas y rutas de paper críticas.**
- Yahoo: timeout, errores parciales, columnas MultiIndex y rate limiting con mocks.
- Seguridad: no exponer detalles y no cargar pickle no confiable.
