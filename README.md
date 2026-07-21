# ELAN Quantum v1.2.2 Core Cleanup

Plataforma local de análisis cuantitativo, fundamental, riesgo, cartera, paper trading y backtesting.

## Estado v1.2.2

- Fundamental Engine con score 0-100.
- Análisis de calidad, crecimiento, valoración, balance y flujo de caja.
- Portfolio Optimizer Institutional con cuatro métodos de asignación.
- Dashboard modular con pestañas Fundamental e Institucional.
- Arquitectura canónica para pipeline, cartera y backtest, con adaptadores legacy.
- Restricciones institucionales verificadas y CI en verde.
- Paper trading transaccional con concurrencia y rollback probados.
- 96 pruebas automáticas con cobertura de líneas y ramas.

## Instalar o actualizar en Windows

```powershell
.\update.bat
```

## Ejecutar

```powershell
.\run.bat
```

## Pruebas

```powershell
pytest
```

El mismo comando ejecuta AppTest sin red y exige al menos 75 % de cobertura sobre `app.py` y el paquete completo. El baseline actual validado es 77,5 %.

## Dependencias reproducibles

`pyproject.toml` define las dependencias directas y `requirements.lock` fija sus versiones
transitivas y la cadena de build para Python 3.11–3.14. Todos los instaladores consumen el
mismo lock mediante:

```powershell
python -m pip install -r requirements.txt
python scripts/check_lock.py
python -m pip check
```

NumPy usa un pin compatible por versión de Python: 2.4.6 en Python 3.11 y 2.5.1 en
Python 3.12–3.14.

## Crear una distribución limpia

Con el working tree limpio, el artefacto se genera únicamente desde el commit actual:

```powershell
.\.venv\Scripts\python.exe scripts\build_distribution.py --output dist\elan-quantum-1.2.2-core-cleanup.zip
.\.venv\Scripts\python.exe scripts\build_distribution.py --verify dist\elan-quantum-1.2.2-core-cleanup.zip
```

El ZIP incluye `data/` y `logs/` vacíos y excluye `.git`, `.venv`, bases, logs y cualquier estado local no versionado.

ELAN Quantum es una herramienta educativa y de simulación. No constituye asesoramiento financiero ni garantiza resultados.

## Desarrollo e integración

La política Git canónica está en `GIT_WORKFLOW.md`. Toda rama de trabajo debe pasar primero por `develop`; solo `develop` puede integrarse en `main`.

```powershell
python scripts/check_git_flow.py --head feature/core-cleanup --base develop --check-ancestry
```
