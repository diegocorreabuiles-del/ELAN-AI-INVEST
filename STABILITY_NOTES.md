# ELAN Quantum v1.2.1 Stability

Esta versión se centra en robustez y mantenimiento.

## Mejoras

- Arranque protegido con mensajes claros cuando faltan archivos o dependencias.
- Cada pestaña del dashboard queda aislada: un fallo local no bloquea toda la aplicación.
- Importaciones de Yahoo Finance diferidas hasta el momento de uso.
- `healthcheck.py` comprueba dependencias esenciales.
- Tests capaces de localizar el paquete `src` incluso antes de la instalación editable.
- Versión sincronizada en paquete, configuración y `pyproject.toml`.

## Instalación

1. Copiar todos los archivos sobre la versión anterior.
2. Ejecutar `update.bat`.
3. Ejecutar `run.bat`.
