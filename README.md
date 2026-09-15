# Michigan Workforce Intelligence

Evidence-backed Michigan jobs analysis and a local job-continuity pilot. The public evidence service combines official aggregate data, versioned observations, source artifacts, an audited ledger, deterministic analysis and MCP access. Reports cover Macomb, Oakland and Wayne counties and Michigan, with U.S., Ohio, California, Texas and Florida benchmarks and additional interstate earnings/price comparisons.

[Download report releases](https://github.com/AXIOVEX/michigan-workforce-intelligence/releases/latest) · [Report sources and findings](reports/2026-09-13-job-continuity/README.md) · [Data credits](THIRD_PARTY_NOTICES.md)

## Ask naturally

Use the [Michigan workforce reporting skill](.agents/skills/michigan-workforce-reports/SKILL.md) with the `michigan_workforce` MCP connection. Users do not need SQL, API names or occupation codes. The workflow audits stored evidence, researches current official sources for gaps, and separates findings, assumptions, proposals and missing evidence.

| Request | Result |
| --- | --- |
| “Give me a county jobs report compared with Michigan, the U.S., Ohio, California, Texas and Florida.” | Compatible employment/unemployment benchmarks, periods, charts and source lineage. |
| “Show past trends and a cautious 12-month outlook, including why conditions might change.” | Historical trends, transparent reference paths where supported, holdout error, stress ranges and separately labeled hypotheses. |
| “Look beyond unemployment at underemployment and housing instability.” | U-3/U-6, participation and involuntary part-time evidence; separate homelessness research and coverage gaps without double counting. |
| “Help a manufacturer avoid layoffs while keeping pay and benefits.” | Retention, internal redeployment and voluntary receiving-employer transitions with verified job requirements. |
| “Find pathways into manufacturing, engineering, aerospace or defense.” | Transferable skills, missing requirements, candidate training providers and role-specific hiring constraints. |
| “Match funding and include Job Corps, APEX and Velocity where appropriate.” | Program roles, eligibility, current availability questions, allowed costs and no duplicate funding assumptions. |
| “Which educational institutions should we consider?” | Candidate-only institutions, official program evidence and proposed fit. None is represented or committed to the pilot. |
| “Make a student retention or talent attraction plan.” | Paid work-and-learning proposals, comparable wages/prices, household constraints and missing residence/placement evidence. |
| “Build a pilot budget and measure jobs saved.” | Reproducible low/base/high scenarios, sustained outcomes and a counterfactual evaluation design. |

Use the [copy-ready prompt catalog](.agents/skills/michigan-workforce-reports/references/prompts.md) and [tool/definition guide](.agents/skills/michigan-workforce-reports/references/data-guide.md). Copy the canonical skill directory into your local Codex skills directory to install it; preserve personal edits when updating. Never put API keys or identifiable worker details in report prompts.

## Start locally

Use Docker Desktop with Linux containers, or Docker Engine with Compose. Portable report/exchange launchers additionally require Python 3.12+ on the host; application, database and PDF dependencies run inside Docker.

Copy `.env.example` to `.env` once, without overwriting an existing file. On PowerShell use `if (-not (Test-Path .env)) { Copy-Item .env.example .env }`; on Linux/macOS use `test -f .env || cp .env.example .env`. Edit settings only in `.env`.

```sh
docker compose run --build --rm tui
```

The Rich manager starts/stops the evidence service, checks health, shows redacted configuration, audits the ledger, runs CI and manages the confidential exchange. It has trusted local Docker-socket access. Quitting or stopping services preserves data. No volume-deletion action is provided.

For direct startup and validation:

```sh
docker compose up -d --build --wait app
docker compose run --rm -T cli audit-ledger
docker compose run --rm --build ci
```

The public-evidence MCP endpoint is `http://127.0.0.1:8000/mcp`. A separate agent container on the `michigan-workforce` network uses `http://workforce-mcp:8000/mcp`; it needs neither database mounts nor Docker-socket access. See [MCP connection details](docs/chatgpt.md) and [Compose/Kubernetes wiring](deploy/README.md). Compose is the supported local deployment; Kubernetes files are a later deployment option.

For the combined Docker MCP Gateway, use the companion `manufacturing-inference-advisor` repository beside this one and run its `python scripts/docker_mcp.py setup`, `test`, and `verify` commands. That profile exposes this server's evidence volume read-only alongside the manufacturing inference design server, allowing agents to move from workforce findings to private inference-infrastructure plans without giving either container the Docker socket or host filesystem.

## Configuration and persistence

`.env.example` documents the variables. Keep API credentials, `EXCHANGE_OPERATOR_TOKEN` and `EXCHANGE_ENCRYPTION_KEY` in the ignored `.env`. Existing API keys are preserved. `COMPOSE_PROJECT_NAME` selects the project and volumes; changing it does not migrate data. Defaults use `/data/mijobs.db` and `/data/artifacts` in the evidence volume. The exchange uses a separate `confidential` volume and dedicated bridge network. MCP writes remain disabled unless explicitly enabled. Secrets are excluded from image builds and releases.

## Confidential employer exchange: local pilot

```sh
python scripts/exchange.py setup
python scripts/exchange.py up
python scripts/exchange.py status
```

Open `http://localhost:8085`. Use the operator credential from your local `.env` to provision an employer after verifying its identity. Employer credentials expire and can be revoked. Browser credentials remain in memory. The interface accepts aggregate surplus/hiring signals, opt-in matching and consent-attested transition proposals with receiving offers and employer-reported starts. Do not enter names, resumes or worker identifiers. Signals require dates, headcount, geography, occupation, skills and wage/hours floors.

The exchange exposes three authenticated read-only tools at `http://127.0.0.1:8085/mcp`: `exchange_signals`, `exchange_matches`, and `exchange_transitions`. Use a separate MCP connection with a bearer credential and appropriate employer scope. It is not part of the public-evidence connection. Public GitHub visibility does not expose this local service or its records. See [exchange operation and limits](docs/employer-exchange.md).

## Evidence and queries

The latest scripted snapshot verifies **3,727 observation versions, 55 raw artifact hashes, 9,572 ledger events and 33 configured monthly series**. Exact periods, units, adjustment, nulls and observation/artifact IDs are in [analysis-snapshot.json](reports/2026-09-13-job-continuity/analysis-snapshot.json). Integrity checks establish provenance, not statistical accuracy or current employer demand.

| MCP tool / evidence | Appropriate use and limits |
| --- | --- |
| `ledger_audit`, `ledger_verify` | Verify evidence coverage and chain integrity before reporting. |
| `economic_indicators`, `economic_trend` | Discover exact metric/geography and read compatible trends. Monthly reference outlooks require sufficient history; unsupported evidence is labeled. |
| `observations_search` | Query exact source metric, geography, taxonomy or artifact. Latest revisions are selected by default. |
| `artifacts_get`, `claims_trace` | Trace reported findings to stored artifacts and claims. |
| `partner_institutions_list` | Legacy name for candidate lookup; four institutions have stored outcomes and eight additional candidates have official program research. No participation is implied. |
| `mappings_search` | Explore CIP–SOC relationships; a mapping is neither a placement nor employer demand. |
| University and scenario analytics | Analyze supplied compatible inputs; no actual Michigan retention or causal jobs-saved estimate is inferred. |

For county unemployment, use `economic_trend` with geography `26099`, `26125`, `26163` or `26` and metric `laus.unemployment_rate`. For exact series use the `bls.<series_id>` metric discovered in the registry. State U-6 is `bls.underutilization.u6`, with an 11-month window excluding October 2025; never treat it as county U-6. National participation, employment/population and involuntary part-time measures have separate definitions.

University outcomes cover IPEDS 2024 first-major awards and separate Scorecard cohorts for Lawrence Technological, Rochester Christian, Oakland and Kettering, all **candidates only**. Earnings ten years after entry use the reviewed 2020 API field; completion uses the 2024 field. Awards are not available workers, national earnings are not Michigan retention, and degree relationships do not show placements. [Eight additional candidate assessments](reports/2026-09-13-job-continuity/education-candidates.md) add no invented outcome records.

## Reproduce and publish reports

```sh
python scripts/reports.py build-image
python scripts/reports.py analyze
python scripts/reports.py build
```

Analysis reads the evidence volume and reuses university outcomes. Collection is separate: `collect`, `collect-qcew`, `collect-reference`, `collect-comparisons`, and `collect-hardship` refresh only reviewed source workflows. Vintage-specific scripts require source/date review before future collection. Do not reharvest universities just to write a report.

PDFs, charts, aggregate snapshots, manifests, hashes and ZIPs appear in `output/pdf/YYYY.MM.DD.HHMMSSZ`. Page renders in `tmp/pdfs/` support visual review. Build timestamps do not refresh evidence. The manual GitHub release workflow validates the launcher on Linux, Windows and macOS, builds in Docker and publishes allowlisted assets from committed sources. See [report operations](docs/report-operations.md).

The repository and release downloads are public. Only `tbitcs` can push branches; an active all-branch ruleset limits bypass to the `repository-maintainers` team, whose sole member is `tbitcs`. The scoped release workflow can publish tags/assets but has no branch-rule bypass. [Access policy](.github/REPOSITORY_SETUP.md) documents the settings. External users may fork and propose changes without receiving write access.

## Boundaries and credits

The reports propose a job-continuity program; they do not prove zero unemployment, available funding, employer commitments or jobs saved. Job Corps, APEX, Velocity and every educational institution are candidate components. The local exchange is an aggregate pilot, not a hosted production case-management system. Homelessness research, missing sentiment series and statistical outlook limitations are explicitly separated from ingested evidence. Review [roadmap](docs/roadmap.md), [methodology](docs/source-methodology.md) and [security validation](docs/security-validation.md).

Original software uses [MIT](LICENSE); original reports, documentation and charts use [CC BY 4.0](LICENSES/CC-BY-4.0.txt). Both allow commercial reuse and adaptation. See [license scope and attribution examples](LICENSING.md). Source data retain their own terms and attribution; the code license does not relicense third-party data. Prominent provider credits accompany the PDFs and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). [API and redistribution policy](docs/source-policy.md) records endpoint rules, conservative rate limits and collection restrictions.

[![O*NET OnLine](docs/assets/onet-online.png)](https://www.onetonline.org/)

O*NET is a trademark of the U.S. Department of Labor, Employment and Training Administration. The unmodified credit graphic links to O*NET OnLine; no endorsement is implied. See the third-party notices for the applicable attribution and license details.
