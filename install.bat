@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo ELAN Quantum - Instalacion
 echo ==========================================

if not exist ".venv\Scripts\python.exe" (
    py -m venv .venv
    if errorlevel 1 goto :error
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade "pip==26.1.2"
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error
python scripts\check_lock.py
if errorlevel 1 goto :error
python -m pip check
if errorlevel 1 goto :error
if not exist data mkdir data
if not exist logs mkdir logs
python scripts\healthcheck.py
if errorlevel 1 goto :error
python -m pytest
if errorlevel 1 goto :error

echo.
echo INSTALACION COMPLETADA
pause
exit /b 0

:error
echo.
echo ERROR EN INSTALACION
pause
exit /b 1
