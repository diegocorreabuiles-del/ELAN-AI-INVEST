# Flujo Git de ELAN Quantum

Estado verificado: 28 de julio de 2026.

Esta política conserva una ruta de integración lineal y revisable. No autoriza por sí sola
ningún push, merge, tag o release.

## Ramas

- `main`: historial publicado y estable. Solo acepta cambios desde `develop`.
- `develop`: rama de integración. Solo acepta ramas de trabajo.
- Ramas de trabajo admitidas: `feature/*`, `fix/*`, `chore/*`, `docs/*`, `recovery/*`
  y `dependabot/*`.

## Transiciones permitidas

| Origen | Destino | Permitido |
|---|---|---|
| Rama de trabajo | `develop` | Sí |
| `develop` | `main` | Sí |
| Rama de trabajo | `main` | No |
| `main` | `develop` | No |
| Cualquier rama | La misma rama | No |

Los eventos `push` solo validan que el nombre de rama pertenece al esquema. La transición
se valida en cada `pull_request`, usando `GITHUB_HEAD_REF` y `GITHUB_BASE_REF`.

## Validación local

Validar la rama actual:

```powershell
python scripts/check_git_flow.py
```

Reproducir la matriz Linux completa de Python 3.11–3.14 con Docker Desktop iniciado:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_ci_matrix.ps1
```

Validar una transición y comprobar que la rama destino es ancestro de la rama de trabajo:

```powershell
python scripts/check_git_flow.py `
  --head recovery/pc-migration-20260721 `
  --base develop `
  --check-ancestry
```

Si Git no está disponible en `PATH`, defina `GIT_EXECUTABLE` con la ruta absoluta de
`git.exe` antes de ejecutar el comando.

## Secuencia operativa

1. Actualizar la rama de trabajo con el estado aceptado de `develop`.
2. Ejecutar los gates locales aplicables.
3. Publicar la rama de trabajo y abrir PR hacia `develop`.
4. Integrar únicamente con CI verde y revisión aprobada.
5. Abrir un segundo PR desde `develop` hacia `main` para preparar una release.
6. Tras la promoción, verificar que `main` sea ancestro de `develop`.
7. Crear tags y artefactos publicados únicamente desde un commit aceptado en `main`.

## Protecciones remotas verificadas

Estado verificado en GitHub el 28 de julio de 2026 para `develop` y `main`:

- exigir pull request;
- exigir el job de CI;
- exigir que las conversaciones estén resueltas;
- bloquear force-push y borrado de rama;
- impedir bypass salvo recuperación administrativa documentada.

Las cuatro variantes de CI (`test (3.11)` a `test (3.14)`) son obligatorias y usan política
estricta de rama actualizada. El historial lineal y la resolución de conversaciones también
son obligatorios; force-push y borrado están bloqueados. Como solo existe un colaborador,
se exigen cero aprobaciones externas y se conserva bypass administrativo para recuperación.
El script local valida la transición, pero la API de GitHub es la fuente de verdad remota.

## Recuperación y rollback

Un fallo del gate no modifica ramas ni archivos. Corrija la rama de destino o actualice la
rama de trabajo y vuelva a ejecutar el comando.

Una promoción `develop -> main` mediante rebase o squash puede dejar árboles equivalentes
con identidades de commit distintas. Después de cada promoción, comprobar:

```powershell
git fetch origin main develop
git merge-base --is-ancestor origin/main origin/develop
```

Si falla, no abrir otra promoción hasta realinear `develop`. La realineación requiere
autorización explícita, respaldo remoto del SHA anterior, igualdad exacta de árboles, gates
completos, `--force-with-lease` y restauración inmediata de la protección. Fuera de este
procedimiento documentado, no reescriba historia compartida para hacer pasar un gate.
