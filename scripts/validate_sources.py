from __future__ import annotations

from pathlib import Path

from mijobs.config import load_source_catalog


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    catalog = load_source_catalog(root / "config" / "sources.json")
    if len(catalog.sources) < 10:
        raise SystemExit("source catalog is unexpectedly small")
    for source in catalog.sources:
        if not source.methodology_notes.strip():
            raise SystemExit(f"source lacks methodology notes: {source.id}")
    print(f"source catalog valid: {len(catalog.sources)} reviewed source families")


if __name__ == "__main__":
    main()
