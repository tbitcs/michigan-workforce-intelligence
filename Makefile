.PHONY: setup tui up stop logs test lint typecheck ci ci-local bootstrap

setup:
	docker compose --profile tools build

tui:
	docker compose run --rm tui

up:
	docker compose up -d --wait app

stop:
	docker compose stop app

logs:
	docker compose logs --tail 100 app

ci:
	docker compose run --build --rm -T ci

ci-local:
	bash scripts/local_ci.sh

test:
	docker compose run --rm ci python -m pytest -q

lint:
	docker compose run --rm ci ruff check src tests scripts deploy

typecheck:
	docker compose run --rm ci mypy src/mijobs deploy

bootstrap: setup
