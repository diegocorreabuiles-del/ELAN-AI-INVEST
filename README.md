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
