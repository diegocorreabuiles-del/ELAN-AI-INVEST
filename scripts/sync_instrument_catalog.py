from __future__ import annotations

import argparse
import gzip
import hashlib
import shutil
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = (
    "https://raw.githubusercontent.com/adanos-software/"
    "free-ticker-database/main/data/tickers.csv"
)
REQUIRED_HEADER = {
    "ticker",
    "name",
    "exchange",
    "asset_type",
    "country",
    "country_code",
    "isin",
    "aliases",
}


def sync(destination: Path, source_url: str = SOURCE_URL) -> tuple[int, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(source_url, headers={"User-Agent": "ELAN-Quantum-catalog-sync/1.0"})

    with tempfile.TemporaryDirectory(prefix="elan-catalog-") as temporary_directory:
        raw_path = Path(temporary_directory) / "tickers.csv"
        with urlopen(request, timeout=60) as response, raw_path.open("wb") as output:
            shutil.copyfileobj(response, output)

        with raw_path.open("rt", encoding="utf-8-sig", newline="") as source:
            header = set(source.readline().strip().split(","))
        missing = REQUIRED_HEADER.difference(header)
        if missing:
            raise ValueError(
                "El catálogo descargado no tiene el formato esperado; faltan: "
                + ", ".join(sorted(missing))
            )

        temporary_gzip = Path(temporary_directory) / "tickers.csv.gz"
        digest = hashlib.sha256()
        row_count = 0
        with (
            raw_path.open("rb") as source,
            gzip.open(temporary_gzip, "wb", compresslevel=9) as compressed,
        ):
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
                row_count += chunk.count(b"\n")
                compressed.write(chunk)
        if row_count < 1_000:
            raise ValueError(f"Catálogo anormalmente pequeño: {row_count} filas.")

        temporary_gzip.replace(destination)
    return row_count - 1, digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Actualiza el catálogo global abierto utilizado por ELAN Quantum."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("config/catalog/adanos_tickers.csv.gz"),
    )
    parser.add_argument("--url", default=SOURCE_URL)
    args = parser.parse_args()

    rows, sha256 = sync(args.output.resolve(), args.url)
    print(f"[OK] Catálogo actualizado: {rows:,} instrumentos.")
    print(f"[OK] Destino: {args.output.resolve()}")
    print(f"[OK] SHA-256 del CSV original: {sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
