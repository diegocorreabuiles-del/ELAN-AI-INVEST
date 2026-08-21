# Fuentes de datos — Terminal de Decisión

Inventario vigente para las Fases 3–8. La interfaz muestra **N/D** cuando la fuente o el campo no existen; no se sustituyen datos ausentes por cero ni por estimaciones visuales.

| KPI / familia | Fuente | Campo o cálculo | Tipo | Disponible | Fallback |
|---|---|---|---|---|---|
| Precio y variaciones | Yahoo Finance | OHLCV ajustado al símbolo | Recibido + cálculo local | Sí | N/D |
| Indicadores técnicos | Yahoo Finance | OHLCV → SMA, EMA, RSI, MACD, ADX, ATR, RVOL | Calculado | Sí | N/D |
| Riesgo histórico | Yahoo Finance | Close → volatilidad, VaR, drawdown, Sharpe | Calculado | Sí | N/D |
| Beta/correlación benchmark | Yahoo Finance | Retornos consecutivos alineados | Calculado | Condicional | N/D si benchmark no está disponible |
| Fuerza crypto vs BTC 30D | Yahoo Finance | Retorno 21 sesiones activo menos retorno BTC | Calculado | Condicional | N/D si BTC no está en el análisis |
| Actividad de volumen 20D | Yahoo Finance | Media últimas 20 sesiones frente a 20 anteriores | Calculado | Sí, con 40 observaciones válidas | N/D |
| Volumen monetario medio | Yahoo Finance | Media 20 sesiones de Close × Volume | Calculado | Sí | N/D |
| Funding rate | Sin proveedor actual | — | No disponible | No | N/D |
| Open interest / Long-Short | Sin proveedor actual | — | No disponible | No | N/D |
| Liquidaciones | Sin proveedor actual | — | No disponible | No | N/D |
| Exchange netflow | Sin proveedor actual | — | No disponible | No | N/D |
| MVRV / SOPR | Sin proveedor actual | — | No disponible | No | N/D |
| TVL / direcciones / fees / revenue | Sin proveedor actual | — | No disponible | No | N/D |
| Liquidez DEX | Sin proveedor actual | — | No disponible | No | N/D |
| Holder growth / concentración | Sin proveedor actual | — | No disponible | No | N/D |
| Whale flows / social momentum | Sin proveedor actual | — | No disponible | No | N/D |
| Desviación del peg USD | Yahoo Finance | (Close − 1 USD) / 1 USD | Calculado | Sí para pares *-USD | N/D |
| Desviación máxima del peg | Yahoo Finance | Máximo absoluto en 30 sesiones | Calculado | Sí | N/D |
| Peg Health | Yahoo Finance | 65 % salud actual + 35 % peor desviación de 30 sesiones | Score derivado | Sí | N/D |
| Riesgo de depeg | Yahoo Finance | Umbrales deterministas sobre desviación actual/máxima | Clasificación derivada | Sí | N/D |
| Market cap / supply stablecoin | Sin proveedor actual | — | No disponible | No | N/D |
| Reservas / transparencia / emisor | Sin proveedor actual | — | No disponible | No | N/D |
| Distribución por cadenas | Sin proveedor actual | — | No disponible | No | N/D |
| Liquidez profunda en DEX/exchanges | Sin proveedor actual | — | No disponible | No | N/D |

## Criterios de depeg

- Bajo: desviación actual < 0,25 % y máxima < 0,5 %.
- Moderado: actual ≥ 0,25 % o máxima ≥ 0,5 %.
- Alto: actual ≥ 1 % o máxima ≥ 2 %.
- Crítico: actual ≥ 3 % o máxima ≥ 5 %.

El volumen de Yahoo se presenta como **actividad de mercado**. No se utiliza como sustituto de profundidad, reservas, supply, adopción ni solvencia del emisor.

Todos estos cálculos son de investigación y solo lectura. No modifican scoring productivo, cartera, Paper Trading ni ejecución de órdenes.
