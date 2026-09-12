# Michigan Workforce Intelligence

Private, Michigan-first workforce intelligence infrastructure for building auditable analyses of unemployment, employment, occupational demand, job and skill gaps, education pipelines, workforce flows, wages, and policy scenarios.

The distinguishing property is not another dashboard. It is an **epistemic evidence system**: exact source artifacts are immutable and content-addressed; observations are separate from claims; claims can be revised or contested without erasing history; taxonomy mappings and derived metrics retain their sources and versions; and every evidentiary write is represented in a SHA-256 hash chain.

## What is implemented

- Reviewed official-source catalog spanning Michigan MCDA, CEPI/MI School Data/STARR/MSLDS, LEO/WLDS, BLS, Census QWI/LEHD/LODES/PSEO, NCES/IPEDS, O*NET, and Registered Apprenticeship.
- Content-addressed raw artifact store.
- Append-only SQLAlchemy evidence model, local SQLite reference backend, PostgreSQL-ready models.
- Immutable/versioned observations, claims, evidence edges, challenges, taxonomy mappings, and derived metrics.
- Canonical SHA-256 event ledger plus a coverage audit that detects evidence records created outside the ledger.
- BLS Public Data API v2 connector/normalizer.
- Census QWI API connector with explicit units/dimensions.
- Official-government artifact fetcher with HTTPS and domain allow-listing.
- Michigan MCDA schema-detecting XLSX parsers for 2024-2034 occupational projections and 2025 OEWS data.
- IPEDS parsers for institutional directory, completions, fall enrollment, and 12-month unduplicated enrollment.
- Official CIP 2020 -> SOC 2018 crosswalk parser with artifact-backed mapping persistence.
- O*NET 31.0 rating and software-skill normalization while correctly retaining O*NET-SOC 2019 as the taxonomy vintage.
- Deterministic training-pipeline gap and market-tightness calculations that reject incompatible inputs.
- Deterministic low/base/high training-policy scenarios with explicit counterfactual/additionality assumptions; the system never invents causal rates.
- Evidence-linked report-context builder that refuses unledgered evidence.
- Bounded MCP read/query surface plus opt-in challenge writes.
- MCP Python SDK v2 server contract (2026-07-28 protocol line).
- Local-first CI, offline unit tests, >=90% package coverage gate, Spec Kit artifacts, and RTK/Codex operating policy.

## Architecture

```text
Official government data
        |
        v
Source connector -------> exact raw bytes
        |                       |
        |                 content SHA-256
        v                       |
SourceArtifact <----------------+
        |
        +------> Observation (reported/extracted value)
        |              |
        |              +---- EvidenceEdge ----> Claim
        |                                      |   |
        |                                      |   +--> Challenge
        |                                      +------> revision/supersession
        |
        +------> TaxonomyMapping (CIP/SOC/O*NET-SOC/etc.)
        |
        +------> DerivedMetric (formula + exact inputs + assumptions)

Every evidentiary write
        |
        v
LedgerEvent[n] --SHA-256--> LedgerEvent[n+1] --SHA-256--> ...
        |
        +--> coverage audit verifies no evidence rows bypassed the chain

Evidence database -> deterministic analytics -> MCP -> reports/visualization/policy analysis
```

## Governing rule: do not manufacture compatibility

LAUS people, payroll jobs, online job advertisements, projected openings, program completions, apprenticeship completions, and O*NET skill ratings are different measures. Definition, unit, period basis, geography, population, seasonal adjustment, release status, and taxonomy version are part of the data. Deterministic analytics return missing/incompatible rather than silently coercing them into a persuasive but invalid number.

## Setup

Requires Python 3.11+, Git, Spec Kit, and RTK.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,mcp]'
cp .env.example .env
bash scripts/bootstrap_governance.sh
make ci
mijobs init-db
mijobs verify-ledger
mijobs audit-ledger
```

`bootstrap_governance.sh` preserves an existing `.specify` tree, initializes Spec Kit for Codex when needed, and runs project-scoped `rtk init --codex`.

### Strict local CI

```bash
STRICT_TOOLS=1 make ci
```

Strict mode requires RTK, Spec Kit (`specify`), Ruff, Mypy, and pytest-cov. No GitHub Actions workflow is included intentionally: local CI is the canonical gate until the project explicitly adopts remote CI.

## MCP

Install the MCP extra and run the v2 server over stdio:

```bash
mijobs-mcp
```

The MCP layer exposes bounded source, observation, artifact, claim, taxonomy-mapping, lineage, ledger-audit, deterministic gap/policy-scenario, and report-context tools. Claim-challenge writes remain disabled until:

```bash
MIJOBS_MCP_WRITE_ENABLED=true
```

The database is the evidence authority. The LLM is allowed to reason over evidence, but it is never allowed to invent a database fact or silently repair a missing statistic.

## Data ingestion principles

1. Prefer official primary sources.
2. Save exact downloaded/API response bytes before normalization.
3. Record source URL/locator, retrieval timestamp, checksum, dataset release, parser version, and release status where available.
4. Never overwrite a published observation, mapping, derivation, or claim. Create a new version linked with `supersedes_*`.
5. Treat reported measurements, official estimates/projections, deterministic derivations, inferences, and hypotheses as different epistemic categories.
6. Keep unknown, suppressed, and incompatible values visible.
7. Keep dataset release and taxonomy vintage separate (for example O*NET Database 31.0 vs O*NET-SOC 2019).
8. Build report prose only from an auditable report-context manifest.

## Spec Kit and RTK governance

The active feature is `specs/001-michigan-workforce-intelligence/`. `AGENTS.md` requires the Spec Kit lifecycle for material changes and directs Codex to use RTK for noisy shell/test/git output. `scripts/validate_governance.py` and `scripts/verify_spec_traceability.py` are part of local CI so the implementation cannot quietly drift away from the written requirements.

## Current follow-on work

The next high-value pieces are exact-release validation for current MCDA XLSX files, LAUS/QCEW Michigan release loaders, O*NET-SOC 2019 -> SOC 2018 crosswalk ingestion, LODES/PSEO geography, signed/Merkle checkpoints, and an explicit policy-scenario/sensitivity model. These remain visible as open Spec Kit tasks rather than being represented as finished.

## Official-source starting points

- Michigan MCDA labor market information: `michigan.gov/mcda`
- CEPI / MI School Data: `michigan.gov/cepi`
- Michigan LEO WLDS: `michigan.gov/leo/.../wlds`
- BLS Public Data API: `bls.gov/developers`
- Census data APIs / LEHD QWI: `census.gov/data/developers`
- NCES IPEDS: `nces.ed.gov/ipeds/use-the-data`
- O*NET database: `onetcenter.org/database.html`
- Registered Apprenticeship: `apprenticeship.gov/data-and-statistics`

Exact reviewed URLs and methodological notes live in `config/sources.json`.
