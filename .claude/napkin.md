# Napkin operativo

Solo conserva fallos recurrentes que no deban duplicarse en `AGENTS.md` o `PROJECT_MEMORY.md`. Máximo 10 entradas, cada una con fecha y corrección.

## Git y validación

1. **[2026-07-22] Matriz y distribución usan el `HEAD` confirmado.**
   Haz en su lugar: confirma un candidato limpio antes de ejecutar `scripts/run_ci_matrix.ps1` o construir el ZIP.
2. **[2026-07-22] Una PR verde no cubre el estado fusionado.**
   Haz en su lugar: espera también el CI de cuatro versiones posterior a la fusión en `develop`.
3. **[2026-07-28] Un rebase de promoción puede separar ascendencias.**
   Haz en su lugar: si `main` ya es ancestro del `develop` validado, usa avance rápido exacto sin `force`; cualquier realineación exige respaldo y autorización.

## Windows y herramientas

4. **[2026-07-22] El sandbox puede fallar con `CryptUnprotectData`.**
   Haz en su lugar: reintenta el mismo comando acotado con escalado; no lo trates como fallo del proyecto.
5. **[2026-07-22] Git o `gh` pueden faltar en el `PATH` escalado.**
   Haz en su lugar: usa `C:\Program Files\Git\cmd\git.exe` y `C:\Program Files\GitHub CLI\gh.exe`, añadiendo Git al `PATH` del proceso si hace falta.
6. **[2026-07-22] `apply_patch` puede heredar el fallo DPAPI.**
   Haz en su lugar: crea un diff UTF-8, valida con `git apply --check` y solo entonces aplica con `git apply`.

## Código y pruebas

7. **[2026-07-22] `with connection` no cierra SQLite.**
   Haz en su lugar: usa `contextlib.closing(...), connection` para evitar bloqueos y `ResourceWarning`.
8. **[2026-07-22] Las pruebas deben ser deterministas y sin red.**
   Haz en su lugar: simula Yahoo/Market Data y usa rutas SQLite temporales.
