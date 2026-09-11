from __future__ import annotations

import re
from pathlib import Path

REQ = re.compile(r"\b(?:FR|ER)-\d{3}\b")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    feature = root / "specs" / "001-michigan-workforce-intelligence"
    spec = (feature / "spec.md").read_text(encoding="utf-8")
    tasks = (feature / "tasks.md").read_text(encoding="utf-8")
    requirements = set(REQ.findall(spec))
    task_refs = set(REQ.findall(tasks))
    missing = sorted(requirements - task_refs)
    if missing:
        raise SystemExit(f"requirements missing task traceability: {', '.join(missing)}")
    print(f"spec traceability valid: {len(requirements)} FR/ER requirements mapped")


if __name__ == "__main__":
    main()
