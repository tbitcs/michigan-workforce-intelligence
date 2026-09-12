# Michigan Workforce Intelligence - Codex Operating Contract

This repository is governed by Spec Kit and RTK. Intent, evidence integrity, and tests outrank implementation convenience.

## Required workflow

For material features, use the Spec Kit lifecycle in this order:

1. `/speckit.constitution` when governing principles change.
2. `/speckit.specify` before implementation.
3. `/speckit.clarify` for unresolved ambiguity.
4. `/speckit.plan` before changing architecture or dependencies.
5. `/speckit.checklist` for quality gates.
6. `/speckit.tasks` to create traceable work items.
7. `/speckit.analyze` before implementation when artifacts changed.
8. `/speckit.implement` for code changes.
9. `/speckit.converge` until the implementation converges with the spec.

The active baseline is `specs/001-michigan-workforce-intelligence/`.

## RTK is mandatory for agent shell output

Prefer RTK for supported noisy commands so raw output is not injected into model context:

- `rtk pytest -q`
- `rtk ruff check src tests scripts`
- `rtk git status`
- `rtk git diff`
- `rtk git log`
- `rtk ls`
- `rtk find ...`
- `rtk grep ...`
- `rtk read ...`

If RTK is unavailable, commands may fall back to native equivalents, but record the environment deficiency and do not weaken tests. Install/activate project-scoped Codex guidance with `rtk init --codex`.

## Reasoning economy

Use deterministic computation instead of LLM reasoning whenever SQL, schema constraints, code-system mappings, statistical functions, tests, or stored evidence can answer the question. Escalate reasoning for conflicting evidence, ontology reconciliation, statistical interpretation, causal hypotheses, policy scenarios, and architecture changes. Never use an LLM as a source of workforce facts.

## Non-negotiable epistemic invariants

- Raw source artifacts are immutable and content-addressed.
- Every source artifact records retrieval time, source identity, URL/locator, media type, checksum, and parser version.
- Observations are distinct from claims.
- Claims are versioned; revisions supersede rather than overwrite.
- Challenges/contradictions are first-class records and never delete the challenged claim.
- Derived metrics identify formulas and input observations/claims.
- No cross-dataset comparison is valid without compatible units, time bases, geographies, and code-system versions.
- Missing/unknown is a valid result and must not be silently imputed.
- Every evidentiary write emits an append-only ledger event.
- Ledger events are SHA-256 hash chained and must verify from genesis to head.
- Important reports must be traceable from conclusion to evidence to original artifact hash.

## Data policy

Prefer primary official sources: Michigan MCDA/LEO/CEPI/MDE/UIA, U.S. BLS/DOL/ETA, Census/LEHD, NCES/IPEDS, and O*NET. Secondary sources can be ingested only when clearly labeled and must not silently outrank primary sources.

Do not commit API keys, restricted student-level data, PII, confidential UI claimant data, or credentials. Public aggregate data is the default ingest class.

## Definition of done

A task is not done until tests cover happy path, boundary conditions, invalid inputs, evidence lineage, and ledger integrity where applicable. Run `make ci` locally before commit. Do not enable cloud CI without an explicit project decision; local CI is the canonical gate for now.
