# Feature Specification: Michigan Workforce Intelligence Foundation

**Feature:** 001-michigan-workforce-intelligence
**Status:** Baseline converged; Michigan ingestion depth in progress
**Created:** 2026-09-11

## Problem
Michigan workforce and education information is distributed across agencies, programs, taxonomies, geographies, periods, and methodologies. Decision makers need a defensible way to ask questions such as where unemployment is rising, which occupations face shortages, whether education/training supply aligns with demand, and which interventions might reduce displacement or strengthen Michigan's economy.

## Users and decisions supported
- Policy and legislative stakeholders evaluating workforce interventions.
- Economic-development organizations targeting industry/workforce investments.
- Universities/community colleges evaluating program capacity against labor demand.
- Employers and workforce agencies diagnosing occupation/skill shortages.
- Researchers auditing conclusions and introducing competing evidence.
- AI/reporting clients querying the evidence base through MCP.

## User stories and acceptance scenarios

### US1 - Trace an official statistic
Given an ingested BLS/Michigan statistic, a user can trace a normalized observation to the exact retrieved artifact and SHA-256 hash.

### US2 - Contest a conclusion
Given a derived claim, a reviewer can attach a challenge and contrary evidence without modifying or deleting the original claim.

### US3 - Verify history
A reviewer can verify the complete ledger chain. Any modification to an existing ledger event causes verification failure or is blocked by the database.

### US4 - Compare workforce demand and supply safely
A user can calculate a training-pipeline gap only when occupation, geography, unit, period basis, and taxonomy are explicitly defined. Missing inputs remain visible.

### US5 - Query through MCP
An AI client can list sources, inspect claims/evidence, trace lineage, calculate approved deterministic metrics, and (when explicitly enabled) register challenges.

## Functional requirements
- **FR-001** Maintain a registry of official source families and access requirements.
- **FR-002** Content-address every raw artifact with SHA-256.
- **FR-003** Store source artifacts separately from normalized observations.
- **FR-004** Version observations and claims without destructive update.
- **FR-005** Model evidence relationships: supports, contradicts, qualifies, derives-from.
- **FR-006** Model challenges with open/resolved/withdrawn states and rationale.
- **FR-007** Append a hash-chained ledger event for every evidentiary write.
- **FR-008** Verify ledger sequence, previous-hash links, payload hashes, and event hashes.
- **FR-009** Support BLS Public Data API v2 ingestion.
- **FR-010** Support Census API ingestion, initially QWI-compatible generic records.
- **FR-011** Support file/download ingestion for Michigan MCDA, CEPI/MI School Data, IPEDS, O*NET bulk files, apprenticeship exports, and other official artifacts.
- **FR-012** Preserve code system and version for SOC, NAICS, CIP, O*NET-SOC, and geography identifiers.
- **FR-013** Provide deterministic workforce-gap calculations with explicit formula versions and completeness flags.
- **FR-014** Expose read-oriented MCP tools; mutation tools default disabled.
- **FR-015** Generate machine-readable report context with evidence references, not unsupported prose.
- **FR-016** Verify that every persisted evidence-bearing entity is represented by a ledger event; a valid chain alone is insufficient.
- **FR-017** Persist taxonomy mappings as versioned, immutable, source-artifact-backed evidence.
- **FR-018** Persist derived metrics with formula/version, exact input references, assumptions, caveats, and supersession history.
- **FR-019** Normalize IPEDS institution, completions, fall-enrollment, and 12-month enrollment data while preserving release status and CIP vintage.
- **FR-020** Keep O*NET database release and O*NET-SOC taxonomy version as independent metadata dimensions.
- **FR-021** Parse Michigan MCDA projection/OEWS workbooks defensively and fail closed on unrecognized schemas.
- **FR-022** Evaluate workforce-policy scenarios only from explicit caller-supplied causal assumptions, including a counterfactual/additionality parameter and low/base/high sensitivity cases.

## Epistemic requirements
- **ER-001** Observation != Claim. Directly reported measurements and interpretations must never share the same semantic type.
- **ER-002** Each claim carries epistemic kind and status.
- **ER-003** Confidence is decomposable into evidence-quality dimensions rather than an unexplained scalar.
- **ER-004** Unknown/missing/incompatible are valid outputs.
- **ER-005** Source authority is metadata, not proof of correctness.
- **ER-006** Revisions/supersession remain visible and queryable.
- **ER-007** Report conclusions must be traceable to evidence and derivation steps.

## Data/source requirements
Initial catalog must cover Michigan MCDA LAUS, QCEW, OEWS, employment projections, online job advertisements/LMI; CEPI MI School Data/STARR/MSLDS; Michigan LEO WLDS; BLS; Census QWI/LEHD/LODES/PSEO where accessible; NCES IPEDS; O*NET; DOL Registered Apprenticeship; and documented expansion points for UIA aggregate data and other state sources.

## Security/privacy requirements
- Public aggregate data only in baseline.
- Secrets only through environment variables.
- MCP write operations disabled by default.
- Artifact paths are content-addressed and sanitized.
- No remote CI is required; local checks are canonical.

## Non-functional requirements
- Python 3.11+.
- SQLite for local development; SQLAlchemy models portable to PostgreSQL.
- Deterministic canonical JSON hashing.
- Unit-test-first for invariants and connectors using mocked HTTP.
- Maintain at least 90% package statement coverage in the canonical local CI gate.
- No network dependency in unit tests.

## Out of scope for baseline
- Restricted student-level data.
- UI claimant-level records.
- Production causal inference or autonomous policy optimization. Deterministic what-if scenarios with explicit assumptions are allowed.
- Scraping sites in violation of terms/access controls.
- Treating online job ads as equivalent to vacancies or unique jobs without methodological qualification.

## Success criteria
- **SC-001** 100% of ledger integrity tests pass, including tamper attempts.
- **SC-002** Every test fixture can run offline.
- **SC-003** Source registry validates unique IDs, official domains, and access modes.
- **SC-004** BLS connector normalizes sample responses reproducibly.
- **SC-005** Gap engine refuses incompatible units/time bases.
- **SC-006** Every FR/ER requirement is mapped to tasks/tests or explicitly marked future.
- **SC-007** Local test coverage remains at or above 90% for the `mijobs` package.
