@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r requirements.txt
python -m pytest -q
if errorlevel 1 (
  echo.
  echo ERROR EN PRUEBAS
  pause
  exit /b 1
)
echo.
echo ACTUALIZACION V0.5 COMPLETADA CORRECTAMENTE
pause
