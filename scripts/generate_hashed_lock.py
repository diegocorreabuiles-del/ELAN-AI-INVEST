from __future__ import annotations

import argparse
import json
import ssl
import tomllib
import urllib.parse
import urllib.request
from collections.abc import Sequence
from pathlib import Path

from check_lock import exact_pin, read_lock_entries
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

USER_AGENT = "ELAN-Quantum-lock-generator/1.0"


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _build_requirements(root: Path) -> list[Requirement]:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return [Requirement(raw) for raw in data["build-system"]["requires"]]


def _requirements(root: Path) -> list[Requirement]:
    requirements = [
        entry.requirement
        for entry in read_lock_entries(root / "requirements.lock", require_hashes=False)
    ]
    present = {canonicalize_name(requirement.name) for requirement in requirements}
    for requirement in _build_requirements(root):
        exact_pin(requirement)
        if canonicalize_name(requirement.name) not in present:
            requirements.append(requirement)
    return sorted(
        requirements,
        key=lambda requirement: (
            canonicalize_name(requirement.name),
            str(requirement.marker or ""),
        ),
    )


def _release_hashes(requirement: Requirement) -> tuple[str, ...]:
    version = exact_pin(requirement)
    name = urllib.parse.quote(requirement.name)
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30, context=_ssl_context()) as response:
        payload = json.load(response)
    hashes = {
        item.get("digests", {}).get("sha256")
        for item in payload.get("urls", [])
        if not item.get("yanked", False) and item.get("packagetype") in {"bdist_wheel", "sdist"}
    }
    hashes.discard(None)
    if not hashes:
        raise RuntimeError(f"PyPI no publicó artefactos SHA-256 para {requirement}.")
    return tuple(sorted(hashes))


def render(root: Path) -> str:
    lines = [
        "# ELAN Quantum 1.3.0rc1 dependency lock with SHA-256 hashes.",
        "# Generated from pinned releases on 2026-08-27.",
        "# Includes every non-yanked wheel and sdist published for each pin so",
        "# Python 3.11-3.14 can select a verified artifact on Windows or Linux.",
        "# Regenerate explicitly with: python scripts/generate_hashed_lock.py",
        "",
    ]
    cache: dict[tuple[str, str], tuple[str, ...]] = {}
    for requirement in _requirements(root):
        key = (canonicalize_name(requirement.name), exact_pin(requirement))
        hashes = cache.setdefault(key, _release_hashes(requirement))
        continuation = chr(92)
        lines.append(f"{requirement} {continuation}")
        for index, digest in enumerate(hashes):
            suffix = f" {continuation}" if index < len(hashes) - 1 else ""
            lines.append(f"    --hash=sha256:{digest}{suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Genera requirements.lock con hashes de PyPI.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    lock_path = root / "requirements.lock"
    generated = render(root)
    if args.check:
        if lock_path.read_text(encoding="utf-8") != generated:
            print("[ERROR] requirements.lock no coincide con los metadatos publicados.")
            return 1
        print("[OK] requirements.lock coincide con los metadatos publicados.")
        return 0
    temporary = lock_path.with_suffix(".lock.tmp")
    temporary.write_text(generated, encoding="utf-8", newline="\n")
    temporary.replace(lock_path)
    print(f"[OK] Lock con hashes generado: {lock_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
