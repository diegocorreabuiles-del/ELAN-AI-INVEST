# ELAN Quantum — Master Plan

## Misión

Construir una plataforma profesional de análisis cuantitativo, gestión de riesgo, construcción de cartera y simulación de operaciones. Ningún módulo ejecutará dinero real hasta superar validación histórica y paper trading.

## Principios

1. Toda recomendación debe ser explicable.
2. Toda estrategia debe medirse contra un benchmark y después de costes.
3. Riesgo antes que rentabilidad.
4. El Core no depende de Streamlit.
5. Cada módulo incluye configuración, logging, pruebas y documentación.
6. `main` es estable; `develop` integra; las funciones nacen en ramas `feature/*`.

## Arquitectura objetivo

- Market Engine: proveedores, normalización, caché y calidad de datos.
- Quant Engine: factores, scoring y régimen de mercado.
- Risk Engine: VaR, CVaR, volatilidad, correlaciones y estrés.
- Portfolio Engine: pesos, liquidez, límites y rebalanceo.
- Paper Trading Engine: órdenes simuladas, comisiones, stops y P&L.
- Backtesting Engine: pruebas fuera de muestra, costes y benchmarks.
- Fundamental Engine: crecimiento, calidad, valoración y balances.
- News & Events Engine: noticias, resultados, bancos centrales y sentimiento.
- AI Explanation Engine: explicación auditable de señales y cambios.
- Broker Gateway: solo paper primero; conexión real al final.

## Versiones

- v0.7: base operativa, scripts únicos, estado del sistema y automatización GitHub.
- v0.8: Backtesting Engine profesional.
- v0.9: Market Data Engine con caché y control de calidad.
- v1.0: primera plataforma estable de análisis, riesgo, cartera y paper trading.
- v1.1+: fundamentales, noticias, IA explicativa y proveedores adicionales.

## Criterios para dinero real

- Paper trading mínimo de 3 a 6 meses.
- Resultados estables fuera de muestra.
- Costes y deslizamiento incluidos.
- Drawdown dentro de límites definidos.
- Registro completo y botón de parada.
- Revisión humana antes de automatización.
