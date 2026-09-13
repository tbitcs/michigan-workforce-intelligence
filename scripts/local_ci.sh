#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}:src"

compact() {
  if command -v rtk >/dev/null 2>&1; then
    rtk "$@"
  else
    "$@"
  fi
}

require_in_strict_mode() {
  local tool="$1"
  if [ "${STRICT_TOOLS:-0}" = "1" ] && ! command -v "$tool" >/dev/null 2>&1; then
    echo "$tool is required in STRICT_TOOLS mode" >&2
    exit 1
  fi
}

require_in_strict_mode rtk
require_in_strict_mode specify
require_in_strict_mode ruff
require_in_strict_mode mypy

echo "[1/7] governance"
python scripts/validate_governance.py

echo "[2/7] compile"
python -m compileall -q src tests scripts deploy

echo "[3/7] unit tests + coverage"
if python -c 'import pytest_cov' >/dev/null 2>&1; then
  # Invoke pytest directly: RTK 0.49 can misreport double-quiet pytest output.
  python -m pytest -q --cov=mijobs --cov-report=term-missing --cov-fail-under=90
elif [ "${STRICT_TOOLS:-0}" = "1" ]; then
  echo "pytest-cov is required in STRICT_TOOLS mode" >&2
  exit 1
else
  echo "pytest-cov not installed; running tests without coverage enforcement"
  python -m pytest -q
fi

echo "[4/7] source registry"
python scripts/validate_sources.py

echo "[5/7] spec traceability"
python scripts/verify_spec_traceability.py

echo "[6/7] lint"
if command -v ruff >/dev/null 2>&1; then
  compact ruff check src tests scripts deploy
else
  echo "ruff not installed; skipped (install .[dev] or set STRICT_TOOLS=1 to enforce)"
fi

echo "[7/7] typecheck"
if command -v mypy >/dev/null 2>&1; then
  mypy src/mijobs deploy
else
  echo "mypy not installed; skipped (install .[dev] or set STRICT_TOOLS=1 to enforce)"
fi

echo "local CI passed"
