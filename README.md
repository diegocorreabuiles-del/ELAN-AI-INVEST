# ELAN Quantum v1.2.2 Core Cleanup

Plataforma local de análisis cuantitativo, fundamental, riesgo, cartera, paper trading y backtesting.

## Estado recuperado en este PC

- La aplicación y su suite funcional se ejecutan en Python 3.12.
- Hay 115 pruebas automáticas superadas, además de Ruff y Black.
- El cierre de dependencias está verificado en una instalación limpia: 76 pins activos y `pip check` sin conflictos.
- La política Git local aplica `trabajo -> develop -> main`; la rama de recuperación todavía no se ha publicado ni integrado.
- El gate global de cobertura pasa con 80,6 %, por encima del 75 % configurado.
- AppTest recorre las once vistas con datos deterministas y bloquea cualquier acceso a Yahoo.
- El empaquetador seguro está reconstruido y cubierto por pruebas de integridad, rutas y reproducibilidad.

Este es un proyecto de simulación y paper trading. No se conecta a brokers ni opera con dinero real.

## Instalar o actualizar en Windows

```powershell
.\update.bat
```

El instalador usa `requirements.lock`, valida las versiones instaladas y ejecuta `pip check`.

## Ejecutar

```powershell
.\run.bat
```

## Verificación local

Suite funcional, sin el umbral global de cobertura:

```powershell
.\.venv\Scripts\python.exe -m pytest -o addopts="-q"
```

Gate completo configurado por el proyecto:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

El segundo comando exige al menos 75 % de cobertura; el baseline local validado es 80,6 %.

## Dependencias reproducibles

`pyproject.toml` define las dependencias directas y `requirements.lock` fija el cierre transitivo para Python 3.11–3.14.

```powershell
.\.venv\Scripts\python.exe scripts\check_lock.py
.\.venv\Scripts\python.exe -m pip check
```

NumPy usa 2.2.6 en Python 3.11 y 2.5.1 en Python 3.12–3.14.

## Crear y verificar una distribución

El constructor exige un working tree limpio y lee exclusivamente los blobs del commit `HEAD`.

```powershell
.\.venv\Scripts\python.exe scripts\build_distribution.py --output dist\elan-quantum-1.2.2-core-cleanup.zip
.\.venv\Scripts\python.exe scripts\build_distribution.py --verify dist\elan-quantum-1.2.2-core-cleanup.zip
```

El ZIP contiene una sola raíz, `data/` y `logs/` vacíos y un manifiesto SHA-256. El gate bloquea bases de datos, logs, ejecutables, credenciales, enlaces simbólicos, rutas no portables y cualquier contenido no confirmado en Git.

## Desarrollo e integración

La política canónica está en `GIT_WORKFLOW.md`. Las ramas de trabajo y recuperación entran primero en `develop`; solo `develop` puede integrarse en `main`.

```powershell
.\.venv\Scripts\python.exe scripts\check_git_flow.py
```

Las protecciones remotas requieren configuración y autorización en GitHub. Ningún script local realiza push, merge, tag o release.

## Próximo bloque

Ejecutar la matriz CI real en Python 3.11–3.14 y preparar la integración hacia `develop`, sin publicar nada hasta recibir autorización.

ELAN Quantum es una herramienta educativa y de simulación. No constituye asesoramiento financiero ni garantiza resultados.
