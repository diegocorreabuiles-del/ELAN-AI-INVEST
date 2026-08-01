# Instrucciones persistentes del repositorio

## Reanudación

1. Lee una vez `.claude/napkin.md` y `PROJECT_MEMORY.md`.
2. Verifica solo el delta necesario: rama, working tree y, si aplica, PR/CI activos.
3. Continúa desde el último estado confirmado; no reconstruyas historia ni reabras decisiones sin evidencia nueva.
4. Actualiza la memoria únicamente cuando cambien decisiones, gates o el siguiente paso.

## Modo lean

- Responde por delta y no repitas planes, estados o resultados ya confirmados.
- Usa `rg` y rangos concretos; agrupa comprobaciones relacionadas y evita lecturas globales salvo auditoría explícita.
- Durante el trabajo ejecuta pruebas dirigidas; reserva el gate completo para cerrar o integrar el bloque.
- Actualiza al usuario solo en hitos, resultados o bloqueos, con el mínimo detalle suficiente.
- Sugiere compactar al cambiar de fase o bloque, nunca a mitad de una modificación coherente.
- Atajos: `adelante` ejecuta el siguiente paso autorizado sin recapitulación; `estado` devuelve hasta 3 puntos; `código VS` devuelve solo PowerShell; `cerrar bloque` ejecuta validación, documentación y cierre Git autorizado.

## Guardrails

- Usa PowerShell en comandos y ejemplos.
- Flujo obligatorio: rama de trabajo → `develop` → `main`; nunca trabajar directamente en `main`.
- Fusionar `main`, crear tags, publicar releases o desplegar requiere autorización explícita independiente.
- Mantén simulación/paper trading; no conectes brokers ni dinero real.
- No borres legacy, datos o scripts sin alcance y autorización específicos; conserva cambios ajenos.
- Antes de integrar, ejecuta los gates vigentes de `PROJECT_MEMORY.md`.
