# ELAN AI INVEST v0.1

Primera version del observador de mercado. Descarga precios diarios, calcula un ranking basico y muestra un panel local.

## Lo que hace

- Analiza una lista inicial de ETF, acciones y Bitcoin.
- Calcula tendencia, momentum y volatilidad.
- Genera una puntuacion de 0 a 100.
- Muestra un ranking y un grafico.
- No envia ordenes y no utiliza dinero real.

## Instalacion en Windows 11

1. Abre PowerShell dentro de esta carpeta.
2. Crea el entorno virtual:

```powershell
py -m venv .venv
```

3. Activalo:

```powershell
.\.venv\Scripts\Activate.ps1
```

4. Instala las dependencias:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

5. Ejecuta el panel:

```powershell
python -m streamlit run app.py
```

El navegador deberia abrir el panel automaticamente.

## Avisos

Los datos de yfinance son adecuados para investigacion y prototipos, no para una futura ejecucion profesional. Antes de conectar un broker se incorporaran datos licenciados, backtesting robusto, control de riesgo y paper trading.
