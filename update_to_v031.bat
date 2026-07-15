@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo   ELAN AI INVEST - Actualizacion v0.3.1
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    py -m venv .venv
    if errorlevel 1 goto :error
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto :error

echo Actualizando pip...
python -m pip install --upgrade pip
if errorlevel 1 goto :error

echo Instalando ELAN AI INVEST en modo editable...
python -m pip install -e ".[dev]"
if errorlevel 1 goto :error

echo Ejecutando pruebas...
python -m pytest
if errorlevel 1 goto :tests_failed

echo.
echo ============================================
echo   ACTUALIZACION COMPLETADA CORRECTAMENTE
echo ============================================
echo.
echo El paquete elan_ai_invest ya esta instalado.
echo Puedes iniciar la aplicacion con start_windows.bat
echo.
pause
exit /b 0

:tests_failed
echo.
echo ERROR: La instalacion termino, pero alguna prueba fallo.
echo Copia el resultado completo y compartelo para revisarlo.
pause
exit /b 1

:error
echo.
echo ERROR: No se pudo completar la actualizacion.
echo Copia el mensaje mostrado encima para revisarlo.
pause
exit /b 1
