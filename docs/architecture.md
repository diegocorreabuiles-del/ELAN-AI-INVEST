# Arquitectura de ELAN AI INVEST

## Core Engine

El Core Engine es el coordinador central. No calcula indicadores directamente ni conoce detalles de Streamlit.

Flujo:

1. Recibe una `AnalysisRequest`.
2. Solicita precios a un proveedor mediante la interfaz `MarketDataProvider`.
3. Adjunta un reporte de calidad por activo sin modificar las series descargadas.
4. Ejecuta el motor de scoring.
5. Determina el régimen de mercado.
6. Guarda una fotografía cuando se solicita.
7. Devuelve un `AnalysisResult` tipado.
8. Registra el proceso en consola y en archivo rotatorio.

## Separación de responsabilidades

- `core/`: configuración, logging, modelos y orquestación.
- `providers/`: adaptadores de proveedores de datos.
- `market/quality.py`: frescura, cobertura, huecos y disponibilidad como metadata.
- `news/`: proveedor y modelos de noticias y calendario corporativo; queda fuera del Core Engine.
- `scoring.py`: cálculo cuantitativo.
- `storage.py`: persistencia SQLite.
- `app.py`: presentación Streamlit.

La interfaz puede cambiar en el futuro sin reescribir el núcleo.

La UI consulta noticias y eventos únicamente al abrir su pestaña. La información es contextual, tolera fallos parciales y no altera el pipeline cuantitativo ni las operaciones simuladas.
