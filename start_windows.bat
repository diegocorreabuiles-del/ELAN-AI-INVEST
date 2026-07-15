@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No existe el entorno virtual.
    echo Ejecutando primero la instalacion de la version 0.3.1...
    call update_to_v031.bat
    if errorlevel 1 exit /b 1
)

call .venv\Scripts\activate.bat

python -c "import elan_ai_invest" >nul 2>&1
if errorlevel 1 (
    echo El paquete no esta instalado. Reparando instalacion...
    python -m pip install -e ".[dev]"
    if errorlevel 1 goto :error
)

python -m streamlit run app.py
exit /b 0

:error
echo.
echo No se pudo iniciar ELAN AI INVEST.
pause
exit /b 1
