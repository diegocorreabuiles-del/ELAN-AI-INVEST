# ELAN Quantum v1.2.2 Core Cleanup

Plataforma local de análisis cuantitativo, fundamental, riesgo, cartera, paper trading y backtesting.

## Estado recuperado en este PC

- La aplicación y su suite funcional se ejecutan en Python 3.12.
- Hay 99 pruebas funcionales superadas, además de Ruff y Black para los archivos reconstruidos.
- El cierre de dependencias está verificado en una instalación limpia: 76 pins activos y `pip check` sin conflictos.
- La política Git local aplica `trabajo -> develop -> main`; la rama de recuperación todavía no se ha publicado ni integrado.
- El gate global de cobertura sigue pendiente: el código recuperado está en 61,8 %, por debajo del 75 % configurado.
- No se ha recuperado todavía `scripts/build_distribution.py`; por tanto no existe un artefacto de release verificable.

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

El segundo comando exige al menos 75 % de cobertura y actualmente debe considerarse bloqueado hasta reconstruir las pruebas de aplicación que faltan.

## Dependencias reproducibles

`pyproject.toml` define las dependencias directas y `requirements.lock` fija el cierre transitivo para Python 3.11–3.14.

```powershell
.\.venv\Scripts\python.exe scripts\check_lock.py
.\.venv\Scripts\python.exe -m pip check
```

NumPy usa 2.2.6 en Python 3.11 y 2.5.1 en Python 3.12–3.14.

## Desarrollo e integración

La política canónica está en `GIT_WORKFLOW.md`. Las ramas de trabajo y recuperación entran primero en `develop`; solo `develop` puede integrarse en `main`.

```powershell
.\.venv\Scripts\python.exe scripts\check_git_flow.py
```

Las protecciones remotas requieren configuración y autorización en GitHub. Ningún script local realiza push, merge, tag o release.

## Próximo bloque

Reconstruir el empaquetado seguro y las pruebas Streamlit/AppTest necesarias para recuperar el gate de cobertura antes de preparar una release.

ELAN Quantum es una herramienta educativa y de simulación. No constituye asesoramiento financiero ni garantiza resultados.