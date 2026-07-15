# ELAN AI INVEST v0.2

Segunda versión del observador cuantitativo. Esta versión no envía órdenes reales.

## Novedades

- Dashboard con régimen de mercado, amplitud, score medio y volatilidad.
- Ranking V2: tendencia, momentum, volatilidad y drawdown.
- Explicación básica de cada activo.
- Gráficos de medias móviles.
- Backtest educativo de momentum.
- Base SQLite local para guardar fotografías del ranking.
- Interfaz organizada por pestañas.

## Instalación sencilla en Windows 11

1. Copia el contenido de esta carpeta sobre tu proyecto local.
2. Conserva la carpeta `.git` de tu proyecto; no la borres.
3. Haz doble clic en `start_windows.bat`.
4. La primera ejecución instalará o actualizará dependencias.

También puede ejecutarse desde PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m streamlit run app.py
```

## Subir la versión a la rama develop

```powershell
git add .
git commit -m "Versión 0.2 - Dashboard, histórico y backtesting"
git push -u origin develop
```

## Aviso

Los datos de yfinance son adecuados para prototipos e investigación, no para ejecución profesional. El backtest no incluye todos los costes y no garantiza resultados futuros.

## Versión 0.3 — Core Engine

La aplicación utiliza ahora un núcleo independiente de la interfaz. La configuración principal está en `config/settings.yaml`, los registros se guardan en `logs/elan_ai_invest.log` y los proveedores de datos se conectan mediante una interfaz común.

Para actualizar dependencias y ejecutar pruebas en Windows:

```text
update_to_v03.bat
```

## Actualización 0.3.1

Esta versión convierte ELAN AI INVEST en un paquete Python instalable. Después de copiar los archivos en la carpeta del proyecto, ejecuta:

```powershell
.\update_to_v031.bat
```

El instalador crea o reutiliza `.venv`, instala el proyecto en modo editable y ejecuta las pruebas. Después inicia la plataforma con:

```powershell
.\start_windows.bat
```

También puede hacerse manualmente:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m streamlit run app.py
```
