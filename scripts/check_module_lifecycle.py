from __future__ import annotations

import argparse
import ast
import json
import tomllib
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

PACKAGE_NAME = "elan_ai_invest"
VALID_NON_ACTIVE_STATES = {"compatibility", "legacy"}


class LifecycleError(ValueError):
    """Raised when module reachability and the lifecycle manifest disagree."""


@dataclass(frozen=True)
class LifecycleReport:
    total: int
    active: int
    compatibility: int
    legacy: int
    compatibility_modules: tuple[str, ...]
    legacy_modules: tuple[str, ...]


def _module_name(path: Path, src_root: Path) -> str:
    parts = list(path.relative_to(src_root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _module_inventory(root: Path) -> dict[str, Path]:
    src_root = root / "src"
    package_root = src_root / PACKAGE_NAME
    return {_module_name(path, src_root): path for path in sorted(package_root.rglob("*.py"))}


def _add_existing(name: str, inventory: Mapping[str, Path], targets: set[str]) -> None:
    parts = name.split(".")
    for index in range(1, len(parts) + 1):
        candidate = ".".join(parts[:index])
        if candidate in inventory:
            targets.add(candidate)


def _imports_for(
    path: Path,
    inventory: Mapping[str, Path],
    module: str | None = None,
) -> set[str]:
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    if module is None:
        package = ""
    elif path.name == "__init__.py":
        package = module
    else:
        package = module.rpartition(".")[0]

    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(PACKAGE_NAME):
                    _add_existing(alias.name, inventory, targets)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            package_parts = package.split(".") if package else []
            keep = len(package_parts) - (node.level - 1)
            if keep < 0:
                continue
            base_parts = package_parts[:keep]
            if node.module:
                base_parts.extend(node.module.split("."))
            base = ".".join(base_parts)
        else:
            base = node.module or ""
        if not base.startswith(PACKAGE_NAME):
            continue
        _add_existing(base, inventory, targets)
        for alias in node.names:
            if alias.name != "*":
                _add_existing(f"{base}.{alias.name}", inventory, targets)
    return targets


def _graph(inventory: Mapping[str, Path]) -> dict[str, set[str]]:
    return {module: _imports_for(path, inventory, module) for module, path in inventory.items()}


def _reachable(roots: set[str], graph: Mapping[str, set[str]]) -> set[str]:
    reached: set[str] = set()
    queue = deque(sorted(roots))
    while queue:
        module = queue.popleft()
        if module in reached:
            continue
        reached.add(module)
        queue.extend(sorted(graph.get(module, set()) - reached))
    return reached


def _matches_root(module: str, root: str) -> bool:
    return module == root or module.startswith(f"{root}.")


def analyze(root: Path) -> LifecycleReport:
    root = root.resolve()
    manifest_path = root / "config" / "module_lifecycle.toml"
    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise LifecycleError("module_lifecycle.toml usa una versión de esquema desconocida.")

    inventory = _module_inventory(root)
    graph = _graph(inventory)
    entry_point = root / str(manifest.get("entry_point", ""))
    if not entry_point.is_file():
        raise LifecycleError(f"No existe el entry point declarado: {entry_point}")
    active = _reachable(_imports_for(entry_point, inventory), graph)
    unreachable = set(inventory).difference(active)

    classifications = manifest.get("classification", [])
    roots_by_state: dict[str, list[str]] = {state: [] for state in VALID_NON_ACTIVE_STATES}
    for item in classifications:
        state = str(item.get("state", ""))
        module_root = str(item.get("root", ""))
        reason = str(item.get("reason", "")).strip()
        if state not in VALID_NON_ACTIVE_STATES:
            raise LifecycleError(f"Estado no válido para {module_root}: {state}")
        if module_root not in inventory:
            raise LifecycleError(f"La raíz clasificada no existe: {module_root}")
        if not reason:
            raise LifecycleError(f"La clasificación de {module_root} no tiene evidencia.")
        roots_by_state[state].append(module_root)

    modules_by_state: dict[str, set[str]] = {state: set() for state in VALID_NON_ACTIVE_STATES}
    for module in sorted(inventory):
        matched_states = {
            state
            for state, roots in roots_by_state.items()
            if any(_matches_root(module, module_root) for module_root in roots)
        }
        if len(matched_states) > 1:
            raise LifecycleError(f"Clasificación solapada para {module}: {sorted(matched_states)}")
        if matched_states:
            modules_by_state[matched_states.pop()].add(module)

    classified_non_active = set().union(*modules_by_state.values())
    leaked = active.intersection(classified_non_active)
    if leaked:
        raise LifecycleError(
            "Módulos no activos alcanzables desde app.py: " + ", ".join(sorted(leaked))
        )
    missing = unreachable.difference(classified_non_active)
    extra = classified_non_active.difference(unreachable)
    if missing:
        raise LifecycleError("Módulos sin clasificación: " + ", ".join(sorted(missing)))
    if extra:
        raise LifecycleError("Módulos clasificados que ya son activos: " + ", ".join(sorted(extra)))

    test_roots: set[str] = set()
    for test_path in sorted((root / "tests").rglob("*.py")):
        test_roots.update(_imports_for(test_path, inventory))
    test_reachable = _reachable(test_roots, graph)
    uncovered = modules_by_state["compatibility"].difference(test_reachable)
    if uncovered:
        raise LifecycleError(
            "Compatibilidad sin cobertura de import en tests: " + ", ".join(sorted(uncovered))
        )

    counts = {
        "total": len(inventory),
        "active": len(active),
        "compatibility": len(modules_by_state["compatibility"]),
        "legacy": len(modules_by_state["legacy"]),
    }
    for name, actual in counts.items():
        expected = manifest.get(f"expected_{name}_modules")
        if expected != actual:
            raise LifecycleError(f"Conteo {name}: esperado {expected}, observado {actual}.")

    return LifecycleReport(
        total=counts["total"],
        active=counts["active"],
        compatibility=counts["compatibility"],
        legacy=counts["legacy"],
        compatibility_modules=tuple(sorted(modules_by_state["compatibility"])),
        legacy_modules=tuple(sorted(modules_by_state["legacy"])),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida el ciclo de vida de módulos Python.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = analyze(args.root)
    except (LifecycleError, OSError, SyntaxError, tomllib.TOMLDecodeError) as exc:
        print(f"[ERROR] {exc}")
        return 1
    if args.as_json:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    else:
        print(
            "[OK] Ciclo de vida: "
            f"{report.total} módulos; {report.active} activos, "
            f"{report.compatibility} de compatibilidad y {report.legacy} legacy."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
