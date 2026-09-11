# Contributing

1. Read `AGENTS.md` and `.specify/memory/constitution.md`.
2. Update the active Spec Kit artifacts before material implementation changes.
3. Add tests before/with code.
4. Use RTK for noisy agent shell commands.
5. Run `make ci` locally. For release-quality checks use `STRICT_TOOLS=1 make ci` after installing `.[dev]`.
6. Never rewrite evidence history. Revisions and challenges are new immutable records.
