# Quickstart

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,mcp]'
bash scripts/bootstrap_governance.sh
make ci
mijobs init-db
mijobs verify-ledger
mijobs audit-ledger
mijobs-mcp
```

For offline development after dependencies are installed, unit tests require no network. `make ci`
is intentionally local-first; it does not depend on GitHub Actions. On a fully provisioned developer
machine the strict gate requires Spec Kit, RTK, Ruff, mypy, pytest, and coverage support.
