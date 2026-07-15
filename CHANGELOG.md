## v0.5.0
- Portfolio Engine.
- Cartera simulada de 100.000 EUR.
- Perfil moderado por defecto.
- Limites por posicion y liquidez minima.
- Comparacion historica con SPY.

# Changelog

## 0.3.0
- Añadido Core Engine para coordinar el análisis.
- Añadida configuración central en YAML y validación con Pydantic.
- Añadido proveedor abstracto de datos y adaptador Yahoo.
- Añadido logging en consola y archivo rotatorio.
- Integración del dashboard con el Core Engine.
- Nuevas pruebas de configuración y orquestación.

## 0.3.1

- Convertido el proyecto en paquete Python instalable mediante `pyproject.toml`.
- Añadida instalación editable con `pip install -e .[dev]`.
- Corregida la detección del paquete `elan_ai_invest` en pytest y Streamlit.
- Añadidas configuraciones de pytest, Ruff y Black.
- Mejorados los scripts de actualización e inicio para Windows.
- Eliminados archivos de caché del paquete distribuido.

## 0.4.0
- Nuevo nombre: ELAN Quantum.
- Risk Engine con VaR, CVaR, volatilidad, drawdown y correlaciones.
- Contribución al riesgo y tamaño orientativo de posición.
- Nueva pestaña de riesgo en el dashboard.
