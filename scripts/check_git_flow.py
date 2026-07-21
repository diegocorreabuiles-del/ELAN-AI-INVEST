from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

WORK_BRANCH_PREFIXES = (
    "feature/",
    "fix/",
    "chore/",
    "docs/",
    "recovery/",
    "dependabot/",
)
PROTECTED_BRANCHES = {"develop", "main"}


class FlowError(ValueError):
    """Raised when a branch name or transition violates the repository policy."""


def normalize_branch(ref: str) -> str:
    branch = ref.strip()
    for prefix in ("refs/heads/", "refs/remotes/origin/", "origin/"):
        if branch.startswith(prefix):
            return branch[len(prefix) :]
    return branch


def is_work_branch(branch: str) -> bool:
    normalized = normalize_branch(branch)
    return any(normalized.startswith(prefix) for prefix in WORK_BRANCH_PREFIXES)


def validate_branch(branch: str) -> None:
    normalized = normalize_branch(branch)
    if normalized in PROTECTED_BRANCHES or is_work_branch(normalized):
        return
    prefixes = ", ".join(WORK_BRANCH_PREFIXES)
    raise FlowError(
        f"Rama no admitida: {normalized!r}. Use main, develop o uno de estos prefijos: "
        f"{prefixes}."
    )


def validate_transition(head: str, base: str) -> None:
    normalized_head = normalize_branch(head)
    normalized_base = normalize_branch(base)
    validate_branch(normalized_head)
    validate_branch(normalized_base)

    if normalized_head == normalized_base:
        raise FlowError("La rama de origen y la rama de destino no pueden ser la misma.")
    if normalized_base == "develop" and is_work_branch(normalized_head):
        return
    if normalized_base == "main" and normalized_head == "develop":
        return
    raise FlowError(
        "Transición no permitida. Las ramas de trabajo solo entran en develop y "
        "únicamente develop puede entrar en main."
    )


def _git_executable(environ: Mapping[str, str]) -> str:
    configured = environ.get("GIT_EXECUTABLE")
    executable = configured or shutil.which("git")
    if not executable:
        raise FlowError("No se encontró Git. Añádalo a PATH o defina GIT_EXECUTABLE con su ruta.")
    return executable


def _git(
    root: Path,
    *arguments: str,
    environ: Mapping[str, str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [_git_executable(environ), *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "error desconocido"
        raise FlowError(f"Git falló ({' '.join(arguments)}): {detail}")
    return proc


def current_branch(root: Path, environ: Mapping[str, str]) -> str:
    proc = _git(root, "branch", "--show-current", environ=environ)
    branch = normalize_branch(proc.stdout)
    if not branch:
        raise FlowError("HEAD está separado; no se puede validar el flujo de ramas.")
    return branch


def resolve_ref(root: Path, ref: str, environ: Mapping[str, str]) -> str:
    normalized = normalize_branch(ref)
    candidates = (ref, normalized, f"origin/{normalized}")
    for candidate in candidates:
        proc = _git(
            root,
            "rev-parse",
            "--verify",
            "--quiet",
            candidate,
            environ=environ,
            check=False,
        )
        if proc.returncode == 0:
            return candidate
    raise FlowError(f"No se encontró la referencia Git {ref!r} para validar ancestros.")


def validate_ancestry(
    root: Path,
    head: str,
    base: str,
    environ: Mapping[str, str],
) -> None:
    resolved_head = resolve_ref(root, head, environ)
    resolved_base = resolve_ref(root, base, environ)
    proc = _git(
        root,
        "merge-base",
        "--is-ancestor",
        resolved_base,
        resolved_head,
        environ=environ,
        check=False,
    )
    if proc.returncode == 0:
        return
    if proc.returncode == 1:
        raise FlowError(f"{base!r} no es ancestro de {head!r}; actualice la rama de trabajo.")
    detail = proc.stderr.strip() or "error desconocido"
    raise FlowError(f"No se pudo validar la ascendencia: {detail}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida el flujo Git de ELAN Quantum.")
    parser.add_argument("--head", help="Rama de origen; por defecto se detecta del entorno.")
    parser.add_argument("--base", help="Rama de destino; obligatoria para validar un PR.")
    parser.add_argument("--event", help="Evento: local, push o pull_request.")
    parser.add_argument("--check-ancestry", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def run(
    argv: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    args = _parser().parse_args(argv)
    env = dict(os.environ if environ is None else environ)
    root = args.repo_root.resolve()
    event = (args.event or env.get("GITHUB_EVENT_NAME") or "local").lower()

    head = args.head or env.get("GITHUB_HEAD_REF")
    if not head:
        head = env.get("GITHUB_REF_NAME") or current_branch(root, env)
    base = args.base or env.get("GITHUB_BASE_REF")

    if event == "pull_request" and not base:
        raise FlowError("Un evento pull_request debe indicar la rama base.")
    if base:
        validate_transition(head, base)
        if args.check_ancestry:
            validate_ancestry(root, head, base, env)
        return f"Flujo válido: {normalize_branch(head)} -> {normalize_branch(base)}"

    validate_branch(head)
    return f"Rama válida para evento {event}: {normalize_branch(head)}"


def main(argv: Sequence[str] | None = None) -> int:
    try:
        print(f"[OK] {run(argv)}")
    except FlowError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
