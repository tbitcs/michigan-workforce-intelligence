.PHONY: bootstrap test lint typecheck ci verify-ledger init-db

bootstrap:
	bash scripts/bootstrap_governance.sh

test:
	@if command -v rtk >/dev/null 2>&1; then rtk pytest -q; else pytest -q; fi

lint:
	@if command -v rtk >/dev/null 2>&1; then rtk ruff check src tests scripts; else ruff check src tests scripts; fi

typecheck:
	mypy src/mijobs

ci:
	bash scripts/local_ci.sh

init-db:
	PYTHONPATH=src python -m mijobs.cli init-db

verify-ledger:
	PYTHONPATH=src python -m mijobs.cli verify-ledger
