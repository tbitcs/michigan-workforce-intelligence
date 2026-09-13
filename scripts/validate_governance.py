from __future__ import annotations

from pathlib import Path

REQUIRED_PATHS = (
    Path("AGENTS.md"),
    Path("RTK.md"),
    Path(".rtk/filters.toml"),
    Path(".specify/memory/constitution.md"),
    Path(".specify/templates/spec-template.md"),
    Path(".specify/templates/plan-template.md"),
    Path(".specify/templates/tasks-template.md"),
    Path("specs/001-michigan-workforce-intelligence/spec.md"),
    Path("specs/001-michigan-workforce-intelligence/plan.md"),
    Path("specs/001-michigan-workforce-intelligence/tasks.md"),
    Path("specs/001-michigan-workforce-intelligence/convergence.md"),
)


def main() -> None:
    missing = [str(path) for path in REQUIRED_PATHS if not path.is_file()]
    if missing:
        raise SystemExit(f"missing governance artifacts: {', '.join(missing)}")

    agents = Path("AGENTS.md").read_text(encoding="utf-8")
    constitution = Path(".specify/memory/constitution.md").read_text(encoding="utf-8")
    required_agents = ("Spec Kit", "RTK", "Reasoning economy", "hash", "make ci")
    required_constitution = ("Evidence", "ledger", "contest", "deterministic", "Local")
    if any(token not in agents for token in required_agents):
        raise SystemExit("AGENTS.md is missing required governance language")
    if any(token.casefold() not in constitution.casefold() for token in required_constitution):
        raise SystemExit("Spec Kit constitution is missing required governance principles")
    print("governance artifacts valid")


if __name__ == "__main__":
    main()
