from __future__ import annotations

import re
from pathlib import Path

REQ = re.compile(r"\b(?:FR|ER)-\d{3}\b")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    total = 0
    for spec_path in sorted((root / 'specs').glob('*/spec.md')):
        feature = spec_path.parent
        spec = spec_path.read_text(encoding='utf-8')
        tasks = (feature / 'tasks.md').read_text(encoding='utf-8')
        requirements = set(REQ.findall(spec))
        missing = sorted(requirements - set(REQ.findall(tasks)))
        if missing:
            raise SystemExit(f"{feature.name}: requirements missing task traceability: {', '.join(missing)}")
        total += len(requirements)
    print(f'spec traceability valid: {total} FR/ER requirements mapped across all features')


if __name__ == '__main__':
    main()
