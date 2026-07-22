# Instrucciones persistentes del repositorio

Antes de explorar o modificar el proyecto:

1. Lee `.claude/napkin.md` y `PROJECT_MEMORY.md`.
2. Verifica solo los datos dinámicos necesarios: rama, working tree, PR y CI.
3. Continúa desde el último estado confirmado; no reconstruyas toda la historia.
4. Actualiza la memoria cuando cambien decisiones, gates o el siguiente paso.

Reglas obligatorias:

- Usa PowerShell para todos los comandos y ejemplos entregados al usuario.
- Aplica el flujo `trabajo -> develop -> main`; nunca trabajo directo a `main`.
- No fusiones `main`, crees tags, publiques releases ni despliegues sin autorización explícita.
- El producto permanece en simulación/paper trading: no conectar brokers ni dinero real.
- No borres módulos legacy, datos o scripts sin alcance y autorización específicos.
- Conserva cambios ajenos y evita reabrir decisiones ya registradas sin evidencia nueva.
- Antes de integrar, ejecuta los gates indicados en `PROJECT_MEMORY.md`.
