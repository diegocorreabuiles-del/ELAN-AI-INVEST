# Flujo Git de ELAN Quantum

Estado verificado: 21 de julio de 2026.

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
6. Crear tags y artefactos publicados únicamente desde un commit aceptado en `main`.

## Protecciones remotas requeridas

Configurar en GitHub para `develop` y `main`:

- exigir pull request;
- exigir el job de CI;
- exigir que las conversaciones estén resueltas;
- bloquear force-push y borrado de rama;
- impedir bypass salvo recuperación administrativa documentada.

Estas protecciones deben verificarse en GitHub antes de una release. El script local valida
la transición, pero no puede demostrar la configuración remota.

## Recuperación y rollback

Un fallo del gate no modifica ramas ni archivos. Corrija la rama de destino o actualice la
rama de trabajo y vuelva a ejecutar el comando. No reescriba historia compartida para hacer
pasar el gate.
