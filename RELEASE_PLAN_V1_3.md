# Plan de release propuesto — ELAN Quantum v1.3

> v1.3 sigue sin crearse. Los PR #3 y #4 ya incorporaron a `develop` la renovación visual y el hardening de errores/datos. La rama actual completa compatibilidad Streamlit, type checking crítico, logging idempotente, versión canónica y tooling antes de preparar `develop -> main`.

Estado: **propuesta; v1.3 no ha sido creada**.

## Objetivo

v1.3 debe ser una release de consolidación y fiabilidad, no una expansión de funciones. Su valor será convertir la implementación 1.2.1 actual en una base reproducible, con una arquitectura canónica, restricciones financieras comprobadas y una UI que no ejecute trabajo oculto.

## Alcance recomendado

### Debe entrar

- Corrección del límite `max_weight` y tests de invariantes.
- Una única API pública de cartera, con compatibilidad temporal.
- Un único backtest usado tanto por UI como por tests, con costes y benchmark.
- CI verde: pytest, Ruff y Black.
- Configuración efectiva para mercado, riesgo, cartera, backtest y paper.
- Renderizado lazy/condicional de vistas costosas.
- Paper trading atómico, snapshots y semántica clara de stop-loss.
- Lockfile y matriz Python soportada.
- Cobertura y type checking inicial en módulos críticos.
- Documentación sincronizada; el artefacto limpio de distribución ya está resuelto como prerrequisito en v1.2.2.

### No debe entrar

- Broker real, dinero real o credenciales.
- Nuevos proveedores de mercado.
- News/sentiment/LLM advisor nuevo.
- Reescritura visual grande.
- Eliminación masiva de legacy sin ciclo de deprecación.
- Optimización matemática nueva no validada.

## Gates obligatorios

| Gate | Criterio |
|---|---|
| Git | Working tree limpio salvo artefactos ignorados; cambios 1.3 en commits temáticos |
| Unit tests | 100 % verdes en versiones Python soportadas |
| Lint/format | Ruff y Black verdes |
| Imports | Import-all sin fallo ni efectos de red |
| Restricciones | Pesos no negativos, suma+cash=100 y cap respetado o error explícito |
| Backtest | Sin look-ahead conocido; costes y benchmark presentes; supuestos documentados |
| Paper | Sin broker; transacciones atómicas; tests de concurrencia/rollback |
| Streamlit | Health OK y AppTest sin red; pestañas ocultas no ejecutan trabajo costoso |
| Dependencias | Lock reproducible y `pip check` verde |
| Seguridad | Sin secretos, pickle activo ni excepciones internas en UI |
| Datos | Artefacto no contiene DB, logs, `.venv` ni `.git` |
| Documentación | README, architecture, changelog y versión sincronizados |

## Hitos

### M1 — baseline 1.2.1 consolidado

- Clasificar el diff recibido.
- Preservar la historia y separar cambios por tema.
- CI verde sin cambiar lógica financiera.

### M2 — corrección financiera

- Cap institucional corregido.
- Cartera canónica.
- Tests de propiedades e invariantes.

### M3 — motores canónicos

- Pipeline y backtest únicos para producción.
- Costes, benchmark y configuración conectados.
- Legacy marcado, aún recuperable.

### M4 — operación robusta

- Streamlit lazy/condicional.
- Mercado con timeout/retry/cache.
- Paper trading atómico y observable.
- Healthcheck SQLite con integridad, esquema y rollback verificados. **Completado en la rama de hardening.**
- Errores internos fuera de la UI y retornos de riesgo alineados sin imputación cero. **Completado en la rama de hardening.**

### M5 — release candidate

- Lockfile reproducible. **Completado como prerrequisito en v1.2.2.**
- Tipos críticos, cobertura y seguridad. **Completado localmente; pendiente matriz CI/PR.**
- Documentación sincronizada.
- Artefacto limpio y smoke test en una máquina/entorno nuevo.

## Estrategia Git propuesta

Estado: política y protecciones implementadas; PR #1–#4 integrados en `develop`; la rama del release candidate está pendiente de PR y la transición `develop -> main` todavía no se ha ejecutado.

1. No publicar desde un working tree: la candidata debe ser un commit limpio.
2. Crear ramas pequeñas `feature/`, `fix/`, `chore/` o `docs/`.
3. Integrar ramas de trabajo en `develop` únicamente mediante PR y gates verdes.
4. Preparar el release candidate desde `develop`.
5. Integrar únicamente `develop` en `main`, tras aceptación explícita.
6. Crear cualquier tag o artefacto publicado desde `main`.

`scripts/check_git_flow.py` aplica esta secuencia en local y CI. Los comandos y las protecciones remotas verificadas el 22 de julio de 2026 están en `GIT_WORKFLOW.md`.

## Versionado

Antes del RC, `pyproject.toml` actúa como fuente canónica y su metadata alimenta:

- `pyproject.toml`
- `elan_ai_invest.__version__`
- texto visible en Streamlit
- healthcheck
- changelog

No usar simultáneamente `1.3.0` y `1.3.0-stability` en fuentes distintas. Si se necesita prerelease, usar una convención PEP 440 como `1.3.0rc1`.

## Plan de pruebas de release

- Python 3.11, 3.12, 3.13 y decisión explícita sobre 3.14.
- Windows, que es el flujo soportado por `.bat`; al menos smoke en Linux por CI.
- Instalación desde cero sin reutilizar `.venv`.
- Proveedor falso para suite determinista; smoke Yahoo separado y no bloqueante.
- Watchlists con 1, 3, 4, 10 y 12 activos; datos faltantes y símbolos inválidos.
- Base SQLite nueva, base 1.2.1 existente y migración con backup.
- Dos sesiones paper concurrentes.
- Streamlit: primera carga, rerun, refresh, guardar histórico y todas las vistas.

## Criterio de no-release

No publicar v1.3 si ocurre cualquiera de estos puntos:

- Algún cap de cartera puede violarse silenciosamente.
- UI y tests siguen usando motores distintos.
- CI no está verde.
- El artefacto incluye estado local o credenciales.
- El working tree no está limpio/explicado.
- La app depende de red para ejecutar la suite.
- La versión no coincide entre paquete, configuración, UI y changelog.

## Entregable final esperado

Un ZIP o paquete limpio con código, configuración de ejemplo, documentación, lockfile y scripts; sin `.git`, `.venv`, logs ni bases de usuario. Debe poder instalarse desde cero, ejecutar healthcheck,  tests y Streamlit con resultados reproducibles.
