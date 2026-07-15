# Arquitectura de ELAN AI INVEST

## Core Engine

El Core Engine es el coordinador central. No calcula indicadores directamente ni conoce detalles de Streamlit.

Flujo:

1. Recibe una `AnalysisRequest`.
2. Solicita precios a un proveedor mediante la interfaz `MarketDataProvider`.
3. Ejecuta el motor de scoring.
4. Determina el régimen de mercado.
5. Guarda una fotografía cuando se solicita.
6. Devuelve un `AnalysisResult` tipado.
7. Registra el proceso en consola y en archivo rotatorio.

## Separación de responsabilidades

- `core/`: configuración, logging, modelos y orquestación.
- `providers/`: adaptadores de proveedores de datos.
- `scoring.py`: cálculo cuantitativo.
- `storage.py`: persistencia SQLite.
- `app.py`: presentación Streamlit.

La interfaz puede cambiar en el futuro sin reescribir el núcleo.
