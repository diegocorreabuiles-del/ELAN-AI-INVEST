@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Entorno no encontrado. Ejecutando instalacion...
    call install.bat
    if errorlevel 1 exit /b 1
)

call .venv\Scripts\activate.bat
python scripts\healthcheck.py
if errorlevel 1 goto :error
python -m streamlit run app.py
exit /b 0

:error
echo.
echo No se pudo iniciar ELAN Quantum.
pause
exit /b 1
