# Memoria operativa de ELAN Quantum

> Fuente rápida de contexto para futuras sesiones. No es un diario. Verifica únicamente los datos dinámicos y actualiza este archivo cuando cambien decisiones, gates o el siguiente paso.

## Protocolo para ahorrar contexto

1. Leer `AGENTS.md`, `.claude/napkin.md` y este archivo.
2. Ejecutar solo `git status`, `git log -3`, estado de la PR activa y CI si son relevantes.
3. No repetir auditorías cerradas ni volver a debatir decisiones registradas sin evidencia nueva.
4. Trabajar desde “Siguiente paso autorizado” y resumir únicamente el delta.
5. Al cerrar un bloque, actualizar esta memoria con hechos validados, no planes supuestos.

## Estado validado — 29 de julio de 2026

- Repositorio: `diegocorreabuiles-del/ELAN-AI-INVEST`.
- Base publicada `1.3.0rc1` en `main`: `5cf2bca1cd98954c1c71e191368432d2b242d9ae`.
- `develop` integra el buscador global, el panel principal y la calidad/resiliencia de Market Data en `ab0686416b77fe49d113ce642f710053c91015cf`.
- La promoción se realizó como avance rápido exacto, sin `force` ni cambios de protección, para conservar el historial lineal y la misma ascendencia en ambas ramas.
- PR #5 (`feature/release-candidate-hardening -> develop`) fusionada por rebase.
- PR #6 (`develop -> main`) fusionada por rebase el 28 de julio de 2026.
- PR #8 (`chore/v1.3.0rc1-candidate -> develop`) fusionada por rebase el 28 de julio de 2026.
- PR #10 (`develop -> main`) fusionada el 28 de julio de 2026; GitHub registró como commit de fusión el propio `3c4cc72`.
- PR #14 (`develop -> main`) fusionada por avance rápido el 28 de julio de 2026 para sincronizar la documentación previa al tag.
- PR #16 (`feature/market-overview -> develop`) fusionada el 28 de julio de 2026; su CI posterior (`30381167190`) pasó en Python 3.11–3.14.
- PR #17 (`feature/market-data-quality -> develop`) fusionada por rebase el 29 de julio de 2026; su CI posterior (`30444192200`) pasó en Python 3.11–3.14.
- Respaldo previo a la realineación: `backup/develop-pre-realign-20260728-4a9010a` en `4a9010a8ddc48e057a3e6c49a6c028e4e063c47e`.
- El Bloque 21 quedó integrado en `develop` y el Bloque 22 fue autorizado y acotado como News & Events Engine v1.
- `feature/news-events-engine` contiene el Bloque 22 confirmado localmente en `76e97b710338e7b17c4132de29f24fb4ed781b46`; la rama no se ha publicado ni tiene PR.
- El cambio no funcional de metadata gzip del catálogo quedó preservado en `stash@{0}` con el mensaje `local gzip metadata before syncing develop`.
- Tag anotado `v1.3.0-rc.1` publicado sobre `5cf2bca1cd98954c1c71e191368432d2b242d9ae`; no existe GitHub Release ni despliegue.
- Producto local de análisis y paper trading; no conecta brokers ni dinero real.

Datos dinámicos: confirmar estos SHA y la PR antes de actuar; no asumir que siguen vigentes en otra fecha.

## Gate vigente

### Windows local

- Python 3.12.13.
- 162 pruebas superadas.
- Cobertura 81,17 %; umbral obligatorio 75 %.
- `requirements.lock`: 78 pins activos y 78 distribuciones locales verificadas.
- `pip check`, Ruff, Black, mypy crítico y healthcheck: verdes.

### Linux reproducible

- Docker Python 3.11, 3.12, 3.13 y 3.14: verde.
- 162 pruebas por versión en el Bloque 22.
- Lock, `pip check`, Ruff, Black, mypy, pytest y empaquetado/verificación: verdes.
- Artefacto del commit realineado `3342c65`: SHA-256 `c24a7643503b39aaf6cd329c3574b08ff5a56278aec9ad5a2ae7793787882e55`.
- Matriz local del Bloque 22 `76e97b7`: verde en Python 3.11–3.14; ZIP reproducible de 169 archivos con SHA-256 `80bfa9092c954b867577f725d05da327a9dcf9465960b8c229e7117a996f7427`.
- CI del commit realineado (runs `30352036059`, `30352343392` y `30352346829`): verde en Python 3.11–3.14.
- CI posterior a la promoción en `main` (run `30356214073`): verde en Python 3.11–3.14, incluido lock, `pip check`, Ruff, Black, mypy, pytest y empaquetado/verificación.
- CI del commit etiquetado en `main` (run `30364715816`): verde en Python 3.11–3.14.
- CI del commit funcional del Bloque 21 `50a5af0` (runs `30441977231` y `30442025065`): verde en Python 3.11–3.14, incluido lock, `pip check`, Ruff, Black, mypy, pytest y empaquetado/verificación.
- CI posterior a la fusión del Bloque 21 en `develop@87379f0` (run `30444192200`): verde en Python 3.11–3.14.
- La protección de `develop` se restauró tras la realineación: PR y checks estrictos obligatorios, historial lineal, conversaciones resueltas, force-push y borrado deshabilitados.

## Decisiones canónicas

1. **Flujo Git:** ramas `feature/`, `fix/`, `chore/` o `docs/` entran por PR a `develop`; solo `develop` puede promoverse a `main`.
2. **Release:** fusionar `main`, cambiar versión, crear tag, publicar release o desplegar son autorizaciones separadas.
3. **Seguridad financiera:** todo permanece en simulación. No añadir broker, credenciales, live mode ni automatización de órdenes sin diseño y aprobación independientes.
4. **Arquitectura:** `core.engine.CoreEngine`, `portfolio.engine` y `backtesting.engine.BacktestEngine` son canónicos; legacy se conserva congelado/deprecado.
5. **Datos de riesgo:** usar retornos consecutivos alineados; sin forward-fill ni retornos cero inventados.
6. **Paper trading:** SQLite local, transacciones `BEGIN IMMEDIATE`, mutaciones atómicas, fallos cerrados y revisión de stops manual/confirmada.
7. **Streamlit:** workspace grafito tipo plataforma de trading; 12 pestañas lazy con `tab.open`; sin CSS inyectado ni `use_container_width`.
8. **Errores:** UI neutra con referencia; detalle técnico solo en logging.
9. **Versión:** `pyproject.toml` es la fuente; `importlib.metadata` alimenta paquete, configuración, UI y healthcheck. Candidata `1.3.0rc1` promovida y validada en `main`; GitHub Release no publicada.
10. **Dependencias:** cierre exacto en `requirements.lock`; `python-dotenv` fue retirado por no tener consumidor.
11. **Catálogo global:** el descubrimiento usa una instantánea MIT de Adanos más `config/instruments.csv`; los históricos siguen en Yahoo. Catálogo disponible no equivale a histórico garantizado. No añadir el paquete `financedatabase` ni sus dependencias pesadas al runtime.
12. **Panel de mercado:** el detalle OHLCV se carga solo para el activo/horizonte visible y se cachea 15 minutos; el comparador usa rendimientos diarios consecutivos alineados, sin rellenar huecos ni correlacionar niveles de precio.
13. **Calidad de mercado:** el reporte es metadata aditiva; clasifica frescura, cobertura, huecos y disponibilidad por activo, registra proveedor/caché y nunca rellena ni altera precios.
14. **Noticias y eventos:** Yahoo se consulta solo al abrir la pestaña, con caché y límites acotados; el resultado es contexto de solo lectura y nunca alimenta scoring, señales, riesgo, cartera ni ejecución paper.

## Reglas de implementación

- Preservar cambios existentes del usuario y evitar operaciones destructivas.
- No borrar legacy, scripts ni datos como “limpieza”; retirar mediante Git y revisión explícita.
- Usar `apply_patch`; si Windows lo bloquea por DPAPI, usar un diff UTF-8 validado con `git apply --check` antes de `git apply`.
- Cerrar SQLite explícitamente con `contextlib.closing`; `with connection` por sí solo no cierra.
- Mantener pruebas sin red y bases temporales.
- Añadir regresión para cada corrección de contrato.
- Sincronizar README, arquitectura, changelog, plan de release y deuda cuando cambie el comportamiento.
- Documentos históricos conservan hechos; documentos canónicos describen solo estado verificado.
- No considerar los avisos `debconf` de Docker como fallos si el script finaliza en código 0; revisar por separado warnings de recursos, seguridad o datos.

## Comandos PowerShell canónicos

### Arrancar la web

```powershell
cd "C:\Users\Asus\Desktop\ELAN AI INVESTMENT"
.\.venv\Scripts\Activate.ps1
.\run.bat
```

### Gate local completo

```powershell
cd "C:\Users\Asus\Desktop\ELAN AI INVESTMENT"
$python = ".\.venv\Scripts\python.exe"
& $python scripts\check_lock.py
& $python -m pip check
& $python -m ruff check .
& $python -m black --check . --fast
& $python -m mypy
& $python -m pytest
& $python scripts\healthcheck.py
```

### Matriz Linux

```powershell
cd "C:\Users\Asus\Desktop\ELAN AI INVESTMENT"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_ci_matrix.ps1
```

### Actualizar catálogo global

```powershell
cd "C:\Users\Asus\Desktop\ELAN AI INVESTMENT"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync_instrument_catalog.ps1
```

### Estado Git y PR

```powershell
cd "C:\Users\Asus\Desktop\ELAN AI INVESTMENT"
git status --short --branch
git log -3 --oneline --decorate
gh pr view 6 --json state,mergeable,mergeStateStatus,statusCheckRollup,url
```

## Mapa mínimo de archivos

- Entrada web: `app.py`.
- Bootstrap/core: `src/elan_ai_invest/core/`.
- Riesgo: `src/elan_ai_invest/risk.py`.
- Cartera: `src/elan_ai_invest/portfolio/engine.py`.
- Paper trading: `src/elan_ai_invest/paper_trading.py`.
- Persistencia histórica: `src/elan_ai_invest/storage.py`.
- UI: `src/elan_ai_invest/dashboard/`; el panel principal y comparador viven en `dashboard/market.py`.
- Calidad de Market Data: `src/elan_ai_invest/market/quality.py`; contrato aditivo en `providers/base.py` y presentación en `dashboard/market.py`.
- Noticias y eventos: `src/elan_ai_invest/news/` y presentación lazy en `dashboard/news.py`.
- Configuración: `config/settings.yaml` y `pyproject.toml`.
- Instrumentos: `src/elan_ai_invest/instruments.py`, `config/instruments.csv` y `config/catalog/`.
- Gates: `.github/workflows/ci.yml`, `scripts/check_lock.py`, `scripts/run_ci_matrix.ps1` y `scripts/build_distribution.py`.
- Estado técnico: `README.md`, `ELAN_ARCHITECTURE.md`, `TECH_DEBT.md`, `RELEASE_PLAN_V1_3.md` y `CHANGELOG.md`.

## Deuda abierta relevante

- TD-012: completar matriz campo-configuración/consumidor.
- TD-021: inventariar módulos no alcanzables antes de cualquier deprecación adicional.
- TD-026: ampliar mypy gradualmente más allá de los 12 módulos críticos.
- TD-035: reducir pruebas de backtest redundantes aportando casos nuevos.
- TD-036: considerar multipágina solo cuando el tamaño real lo justifique.
- TD-037: ampliar invariantes/property tests de pesos, cash y contabilidad.

## Siguiente paso autorizado

- **Bloque 21 — calidad y resiliencia de Market Data** está integrado en `develop@ab06864`; su CI funcional y posterior a la fusión quedaron verdes.
- **Bloque 22 — News & Events Engine v1** está confirmado en `feature/news-events-engine@76e97b7`: gate Windows y matriz local Python 3.11–3.14 verdes, 162 pruebas por versión y artefacto reproducible.
- Siguiente paso pendiente de autorización explícita: publicar la rama y abrir PR hacia `develop`; después vigilar la CI remota Python 3.11–3.14.
- Sentimiento/NLP/IA, alertas, persistencia, ranking por noticias, multi-proveedor y cualquier conexión de broker permanecen fuera del Bloque 22.
- El tag `v1.3.0-rc.1` está publicado; no hay ninguna acción adicional de release autorizada.
- Publicar una GitHub Release o desplegar requieren autorizaciones explícitas independientes posteriores.
- Mantener el producto en paper trading; cualquier activación de broker o dinero real queda fuera de alcance.
