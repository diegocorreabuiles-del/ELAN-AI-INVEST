@echo off
setlocal
cd /d "%~dp0"

echo === ELAN Quantum v0.4 ===
if not exist ".venv\Scripts\python.exe" (
    py -m venv .venv
    if errorlevel 1 goto :error
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -e ".[dev]"
if errorlevel 1 goto :error
python -m pytest
if errorlevel 1 goto :error

echo.
echo ACTUALIZACION COMPLETADA CORRECTAMENTE
pause
exit /b 0

:error
echo.
echo ERROR EN ACTUALIZACION
pause
exit /b 1
