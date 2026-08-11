# Bloque 26 — AI Explanation Engine v1 local

Estado: definido, no iniciado. Fecha de definición: 11 de agosto de 2026.

## Objetivo

Explicar de forma breve, trazable y consistente por qué ELAN muestra una señal,
score y nivel de confianza para el activo activo. La explicación transforma
resultados ya calculados; no crea una recomendación nueva.

## Alcance funcional

1. Crear un motor canónico local y determinista, separado de los módulos legacy
   de `advisor/` e `intelligence/`.
2. Consumir únicamente datos ya disponibles en el resultado canónico: señal,
   score, confianza, régimen, factores cuantitativos, volatilidad y calidad de
   Market Data.
3. Producir un informe estructurado con:
   - resumen de una frase;
   - evidencias favorables;
   - cautelas o factores débiles;
   - nota de calidad y suficiencia de datos;
   - fuentes internas de cada evidencia;
   - aviso educativo/no asesoramiento.
4. Mostrar el informe en la pestaña **Inteligencia** para el activo global, sin
   añadir una decimocuarta pestaña.
5. Mantener estados neutros cuando falten factores o la calidad de datos sea
   insuficiente.

## Contratos e invariantes

- La misma entrada produce exactamente la misma explicación.
- La señal, score, confianza y factores mostrados coinciden con el
  `AnalysisResult`; el motor no los recalcula ni modifica.
- La confianza se presenta como confianza del modelo existente, no como
  probabilidad de rentabilidad futura.
- Cada afirmación cuantitativa identifica el campo interno que la sustenta.
- No se hacen predicciones de precio, objetivos, promesas de retorno ni
  recomendaciones personalizadas.
- No hay nuevas consultas a Yahoo, escritura en SQLite ni efectos laterales.
- El fallo del explicador se aísla con UI neutra y no bloquea las demás vistas.

## Fuera de alcance

- OpenAI, otros LLM, prompts remotos, claves API o consumo de tokens.
- Chat conversacional, memoria de conversaciones o generación libre de texto.
- Nuevos indicadores, señales, umbrales de compra o cambios de scoring.
- Cambios en riesgo, cartera, backtesting, paper trading o ejecución de órdenes.
- Broker Gateway, dinero real, alertas automáticas o asesoramiento financiero.
- Persistencia histórica de explicaciones y soporte multidioma.

## Entregables previstos

- Paquete canónico `elan_ai_invest.explanation` con modelos y motor tipados.
- Integración compacta en `dashboard/intelligence.py`.
- Pruebas unitarias deterministas y AppTest sin red.
- Actualización de README, arquitectura, changelog y memoria operativa.

## Criterios de aceptación

1. La explicación del activo visible incluye al menos una evidencia o una cautela
   verificable y muestra la procedencia del dato.
2. Casos positivos, neutrales, defensivos, datos parciales e inputs inválidos
   tienen pruebas deterministas.
3. Una regresión demuestra que el motor no cambia señal, score, confianza ni
   tablas de ranking.
4. AppTest confirma que abrir Inteligencia no añade red ni mutaciones y que las
   13 pestañas siguen siendo lazy.
5. Ruff, Black, mypy, suite completa con cobertura, healthcheck, lock y
   `pip check` pasan antes del cierre.

## Riesgo, despliegue y rollback

Riesgo previsto: medio por tratarse de texto financiero visible, aunque sea de
solo lectura. No requiere migración, dependencia, credencial ni cambio de
configuración. El rollback consiste en revertir la integración del panel y el
paquete de explicación; no hay datos que restaurar. Cualquier versión con LLM o
servicio externo exigirá un bloque y una autorización independientes.
