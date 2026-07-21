# Plan de refactorización seguro y reversible

## Progreso v1.2.2 Core Cleanup

| Fase | Estado | Evidencia |
|---|---|---|
| 0 — baseline | Completada | Rama `feature/core-cleanup` y commit de respaldo `aca57e7` |
| 1 — P0 | Completada | Cap institucional corregido; pytest, Ruff y Black verdes |
| 2 — cartera | Completada para estabilización | `portfolio.engine` canónico, legacy preservado, tests de invariantes/import |
| 3 — pipeline/backtest | Completada | `CoreEngine` y `BacktestEngine`; costes por turnover, benchmark configurado, lag de ejecución y adaptadores temporales |
| 4 — configuración | Parcial | Mercado —incluidos timeout, retry/backoff y caché—, cartera, backtest, paper y versión conectados; quedan campos secundarios |
| 5 — Streamlit | Completada para estabilización | Render condicional, cachés acotadas, API de ancho, tema nativo y AppTest sin red de `app.py` y todas las vistas |
| 6 — datos/paper | Completada para estabilización | Operaciones, stops y snapshots atómicos; WAL, timeout, rollback, concurrencia y ciclo UI manual probados |
| 7 — calidad/dependencias | Parcial | Lock transitivo y cobertura de ramas con umbral 75 % conectados a CI; faltan tipos y auditoría de vulnerabilidades |
| 8 — documentación/release | Parcial | Distribución y política Git completadas; integración autorizada y retirada de legacy siguen pendientes |

No se retirará legacy en v1.2.2. La siguiente fase debe empezar por los P1 abiertos enumerados en `AUDIT_REPORT.md`, manteniendo un commit reversible por riesgo.

Este plan no autoriza una refactorización inmediata. Cada fase debe ejecutarse en un commit o PR separado, con tests antes y después. No se borra código en las primeras fases.

## Reglas de ejecución

1. Crear una copia/branch de seguridad del estado recibido antes de tocar código.
2. No mezclar formato, cambio funcional y movimiento de archivos en el mismo commit.
3. Añadir una prueba que reproduzca cada bug antes de corregirlo.
4. Mantener adaptadores y avisos de deprecación durante al menos un ciclo.
5. No conectar brokers ni añadir credenciales.
6. Las migraciones SQLite deben ser compatibles hacia atrás y con backup explícito.
7. Cada fase termina con import-all, healthcheck, pytest, Ruff, Black y arranque Streamlit.

## Fase 0 — congelar y entender el baseline

Objetivo: hacer trazable el estado 1.2.1 sin cambiar comportamiento.

- Registrar los cambios actuales por origen/versión.
- Separar archivos solo afectados por EOL de cambios reales.
- Decidir qué untracked pertenece a 1.2.1.
- Crear `.gitattributes` en un cambio aislado, sin renormalizar todavía.
- Guardar resultados de los 30 tests y un smoke de Streamlit.

Reversibilidad: no cambia código; rollback eliminando solo el commit documental/baseline.  
Criterio de salida: working tree explicado y conjunto 1.2.1 identificable.

## Fase 1 — corregir bloqueos P0

Objetivo: recuperar una base verde y correcta.

1. Añadir tests de `max_weight` para 1, 3, 4, 10 y 12 activos.
2. Hacer que restricciones imposibles fallen con mensaje claro o asignen el residual a cash de forma explícita.
3. Ejecutar Ruff con fixes seguros y revisar `StrEnum`.
4. Ejecutar Black en un commit exclusivamente mecánico.

Reversibilidad: un commit por bug, Ruff y Black.  
Criterio de salida: pytest, Ruff y Black en verde; cap siempre respetado o error explícito.

## Fase 2 — consolidar cartera sin borrar

Objetivo: una sola API pública de cartera.

- Escribir una especificación de `PortfolioPlan` y sus invariantes.
- Comparar las dos implementaciones con tests dorados.
- Elegir la variante canónica según comportamiento, no por ubicación.
- Convertir la otra en adaptador que delegue y emita deprecación.
- Conectar perfil, min score, posiciones, cap y cash a `settings.portfolio`.
- Mantener ambos archivos durante esta fase.

Reversibilidad: el adaptador permite volver a la implementación anterior con un cambio de import.  
Criterio de salida: un único resultado para una misma entrada y ningún módulo sombreado funcionalmente.

## Fase 3 — decidir pipeline y backtest canónicos

Objetivo: eliminar dobles caminos de decisión sin pérdida de funcionalidad.

- Crear ADR: CoreEngine frente a InvestmentPipeline.
- Medir qué capacidades exclusivas tiene cada árbol.
- Portar solo capacidades demostradas con tests al pipeline elegido.
- Marcar el árbol alternativo como legacy; no borrarlo aún.
- Unificar el dashboard y los tests sobre un solo backtest.
- Integrar comisiones, slippage, benchmark y señal desplazada.

Reversibilidad: feature flag/import adapter durante un ciclo.  
Criterio de salida: app y tests ejercitan exactamente el mismo motor.

## Fase 4 — hacer efectiva la configuración

Objetivo: que cada valor YAML tenga un consumidor o desaparezca de forma deprecada.

- Crear tests parametrizados campo -> cambio observable.
- Conectar `market.interval` y `minimum_history`.
- Conectar defaults de backtest y portfolio.
- Aplicar `paper_trading.enabled`.
- Definir uso de `max_portfolio_volatility_pct`.
- Unificar versión en una sola fuente.

Reversibilidad: valores por defecto conservan el comportamiento anterior.  
Criterio de salida: matriz de configuración 100 % cubierta.

## Fase 5 — rendimiento y robustez Streamlit

Objetivo: evitar trabajo oculto en cada rerun.

- Medir tiempo de primera carga y rerun.
- Cambiar pestañas costosas a renderizado dinámico/condicional o navegación.
- Cachear recursos apropiados y limitar cachés con TTL/max entries.
- Evitar recrear engines y esquemas innecesariamente.
- Reemplazar 22 usos de `use_container_width`.
- Mover tema/CSS a configuración nativa cuando sea posible. **Completado para colores, tipografía, bordes, sidebar y gráficos.**
- Añadir AppTest con proveedor falso; ninguna prueba depende de internet. **Completado para el flujo principal y todas las vistas.**

Reversibilidad: conservar selector/estructura anterior detrás de flag temporal.  
Criterio de salida: pestaña oculta no ejecuta Yahoo, backtest ni optimizador.

## Fase 6 — datos, paper trading y seguridad

Objetivo: persistencia consistente y simulación fiable.

- Transacciones atómicas para cash/posición y timeout SQLite. **Completado.**
- Definir cuándo se aplican stop-loss y snapshots; mostrarlo al usuario. **Completado: evento manual, confirmado y exclusivamente simulado.**
- Añadir backup/migración de esquema.
- Sustituir pickle legacy por formato seguro antes de reactivar caché. **Completado con CSV, TTL y escritura atómica.**
- Ocultar detalles técnicos en UI y correlacionarlos con logs.
- Separar bases/logs del artefacto de release.

Reversibilidad: migraciones aditivas; nunca modificar una DB sin backup.  
Criterio de salida: invariantes contables y concurrencia probadas. **Cumplido para compras, ventas y el ciclo atómico stop/snapshot; quedan backup/migración y endurecimiento de mensajes como trabajos separados.**

## Fase 7 — calidad, tipos y dependencias

Objetivo: prevenir regresiones estructurales.

- Añadir cobertura con umbral inicial basado en el baseline, subiendo por módulos críticos. **Completado: baseline 77,5 % y gate 75 % sobre líneas y ramas.**
- Añadir mypy o pyright empezando por core, riesgo, cartera y paper.
- Añadir auditoría de dependencias/código a CI.
- Fijar dependencias transitivas y verificar que CI/instaladores usan el lock. **Completado con `requirements.lock` y `scripts/check_lock.py`.**
- Confirmar y retirar `python-dotenv` solo si no hay consumidor externo.
- Añadir Python 3.14 a CI o fijar versión máxima soportada.
- Clasificar los 40 módulos no alcanzables: activo externo, legacy o eliminable.

Reversibilidad: herramientas empiezan en modo informativo y se endurecen por área.  
Criterio de salida: gates de CI documentados y sin excepciones globales.

## Fase 8 — documentación y limpieza final

Objetivo: alinear producto, código y release.

- Actualizar README, arquitectura, roadmap, changelog y notas operativas.
- Retirar adaptadores legacy solo después de un ciclo y búsqueda de consumidores.
- Eliminar archivos únicamente mediante commit dedicado y revisable.
- Crear artefacto limpio sin `.git`, `.venv`, bases ni logs. **Completado con empaquetado desde `HEAD`, carpetas de estado vacías y manifiesto SHA-256.**
- Aplicar `trabajo -> develop -> main` sin saltos. **Gate local/CI completado; push, PR y merge pendientes de autorización.**

Reversibilidad: cada retirada es un commit independiente recuperable desde Git.  
Criterio de salida: documentación coincide con pruebas y artefacto reproducible.

## Secuencia de validación por fase

```text
prueba de regresión -> cambio mínimo -> pytest focalizado -> pytest completo
-> import-all -> ruff -> black -> healthcheck -> Streamlit health/AppTest
-> revisión de git diff -> commit único
```

## Acciones prohibidas durante el refactor

- Borrar simultáneamente ambos lados de una duplicación.
- Renombrar paquetes y cambiar contratos en el mismo commit.
- Actualizar todas las dependencias junto con cambios de lógica.
- Usar datos de mercado en vivo como única prueba.
- Activar trading real o almacenar credenciales en el repositorio.
- Reescribir historia Git, hacer merge o push sin autorización explícita.
