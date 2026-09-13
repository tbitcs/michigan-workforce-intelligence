# Michigan Workforce Intelligence

A local workforce evidence platform for Michigan: official source adapters, versioned observations and claims, immutable artifacts, an audited hash-chain ledger, deterministic analytics, and MCP tools.

## Ask for reports in plain language

Use **Michigan Workforce Reports** in chat. You do not need SQL, tool names, occupation codes or knowledge of how MCP works. The reporting skill selects the relevant stored evidence, audits it, researches current official sources where needed and explains what is known versus assumed.

Start with: **“Help a Michigan manufacturer avoid layoffs and move workers into better-paid jobs nearby.”** Add a county, job types, current pay, number of workers and deadline when known. Missing details become explicit assumptions or focused questions; they do not require learning the database.

The [complete prompt catalog](.agents/skills/michigan-workforce-reports/references/prompts.md) provides 11 copy-ready requests:

| Ask for | Useful optional details | What you get |
|---|---|---|
| Full Michigan job-saving program | Scope, regions, budget, audience | Executive brief, analysis, matrices, funding, budget, roadmap and evidence appendix |
| Employer layoff prevention | Workforce count, jobs, pay/hours, likely date | Retention, paid redeployment and voluntary transfer plan |
| Worker transition and pay improvement | Current tasks/pay, location, training time, commute limit | Realistic pathways, requirements, costs and offer uncertainty |
| Manufacturing/aerospace/defense skills | Region, current experience, target work | Adjacent skills, role-specific requirements and paid bridges |
| Funding match | Employer type, worker status, training quote, dates | Eligibility, current intake, allowable costs, obligations and unresolved approvals |
| University/student outcomes | Institutions, programs, cohort, desired outcome | Awards and separate outcome cohorts; honest placement/retention gaps |
| Regional priorities | Counties, occupations, timeframe | Comparable evidence and explicitly labeled gap hypotheses |
| Early warning | Employers/industry, region, risk horizon | One-time risk review and intervention triggers; no automatic monitoring |
| Talent attraction | Verified jobs, household needs, region | Recruitment/relocation design and retention measures |
| Pilot budget and evaluation | People, funding envelope, timeframe | Reproducible scenarios and counterfactual outcome definitions |
| Update a previous report | Existing report and changed assumptions | New evidence, changed conclusions and unresolved gaps |

For explicit skill selection, begin with `$michigan-workforce-reports`, followed by the ordinary request. Automatic invocation is enabled, so a clear Michigan workforce question can also select it. The skill is a reporting workflow; the existing MCP connection provides database access and browsing supplies current external evidence. It does not add server tools or schedule background work.

Canonical source: [SKILL.md](.agents/skills/michigan-workforce-reports/SKILL.md), with [data/semantics guide](.agents/skills/michigan-workforce-reports/references/data-guide.md). The personal installation lives at `%USERPROFILE%\.codex\skills\michigan-workforce-reports`. If a running conversation has cached its skill list, start a fresh task to discover the installed skill. To install/update on another local Codex setup, copy the canonical directory into that user's `.codex/skills` directory; review and preserve any personal edits before replacing an existing copy. The repository remains the maintained source.

The skill keeps requests focused: a funding question does not automatically generate a full report. It checks source periods/geographies, distinguishes vacancies from projections and advertisements, and never treats CIP–SOC links as actual placements or national earnings as Michigan retention. Funding balances, employer commitments, course seats and individual licensing eligibility can remain unknown even when a program exists. If MCP is unavailable, it discloses that and does not claim a successful audit.

No API keys are needed in prompts. Existing credentials remain in `.env`. Reports do not authorize employer outreach, grant submission, enrollment or deployment. Use the Docker commands below for data operations; read-only report generation does not require reharvesting university outcomes. Harvesting is a separate explicit refresh that appends evidence revisions.

## Completed Michigan program design

The [September 13, 2026 report package](reports/2026-09-13-job-continuity/README.md) executes the comprehensive job-continuity request using the audited database and current official sources. Start with the [executive brief](reports/2026-09-13-job-continuity/executive-brief.md), then see the [full analysis](reports/2026-09-13-job-continuity/report.md), [occupation/region matrices](reports/2026-09-13-job-continuity/matrices.md), [funding matrix](reports/2026-09-13-job-continuity/funding.md), [budget/90-day roadmap](reports/2026-09-13-job-continuity/pilot.md) and [evidence appendix](reports/2026-09-13-job-continuity/evidence.md).

It proposes a 200-worker pilot with a $1.408 million cash envelope, separately identifying employer-paid training time and an optional student module. These are explicit scenarios, not funding awards or estimated jobs saved. [Scenario JSON](reports/2026-09-13-job-continuity/scenario-model.json) and its [Docker-run calculator](reports/2026-09-13-job-continuity/build_scenarios.py) preserve the arithmetic. Regional shortages, actual receiving jobs, individual skill gaps and committed funding remain evidence to collect before launch.

## Generate reports now

**Loaded and verified on 2026-09-13:** 461 IPEDS records, 8 Scorecard outcome observations and 5,723 official crosswalk mappings added. That university-load baseline had 717 observations, 13 hash-verified artifacts and 6,520 valid ledger events; the expanded jobs snapshot below supersedes those totals. A first [university brief](artifacts/reports/university-brief.md) and [structured report](artifacts/reports/universities.json) are generated locally (Git-ignored).

The university workflow loads **IPEDS 2024 awards**, the official **CIP 2020–SOC 2018 crosswalk**, and **College Scorecard earnings/completion measures** for Lawrence Technological, Rochester Christian, Oakland and Kettering. Report commands run entirely in Docker against the persistent evidence database.

```powershell
# Load/refresh the reviewed university sources (writes versioned evidence).
docker compose run --rm -T cli harvest-universities --year 2024

# Produce report context from the stored data (read-only).
New-Item -ItemType Directory -Force artifacts/reports | Out-Null
docker compose run --rm -T cli report-universities --year 2024 > artifacts/reports/universities.json

# Existing national / Michigan historical briefing and integrity check.
docker compose run --rm -T cli report --as-of 2026-09-13 > artifacts/reports/insights.json
docker compose run --rm -T cli audit-ledger
```

The reviewed university command accepts collection years 2020–2024; its Scorecard outcome fields remain explicitly fixed at API data-year **2020 for ten-year-after-entry median earnings** and **2024 for completion within 150% normal time**. These are separate cohort measures, not contemporaneous 2024 graduate salaries. Nulls remain unknown. Do not compare the figures as a causal university ranking or call them Michigan retention rates. See [official Scorecard definitions](https://collegescorecard.ed.gov/files/InstitutionDataDocumentation.pdf).

Your existing BLS/Census keys stay in `.env`. `SCORECARD_API_KEY=DEMO_KEY` uses the public demonstration credential for this small four-institution request; set a personal Scorecard key in `.env` if rate limits require it. No host Python or new database is needed. A failed harvest rolls back the database transaction; inspect the exit status before generating reports. Repeated harvests append revisions.

Ask in chat:

> Use michigan_workforce to draft a university outcomes brief for UnitIDs 170675, 170967, 171571 and 169983. Query IPEDS awards and Scorecard outcomes for each, cite source artifacts, separate academic awards from earnings/completion cohorts, and state that Michigan retention is unknown. Use first-major six-digit program rows only; exclude CIP aggregate totals and do not sum second majors. Show the strongest evidence-supported findings and next data needs.

Exact MCP observation arguments, substituting any of the four UnitIDs:

```json
{"metric":"ipeds.completions.awards","geography_code":"170675","limit":500}
```

```json
{"metric":"scorecard.earnings.10_years_after_entry.median","geography_code":"170675","limit":100}
```

```json
{"metric":"scorecard.completion.4yr_150pct","geography_code":"170675","limit":100}
```

Use observation metadata for `major_number`, `award_level`, `collection_year`, `api_field` and `data_year`. Scorecard fractions must be multiplied by 100 for display as percentages. `artifacts_get` supplies provenance for each observation's `source_artifact_id`. For pathways call `mappings_search` with `{"from_system":"CIP","from_code":"11.0701","to_system":"SOC","limit":500}`; a related occupation is not a verified placement or a demand estimate.

The current [Census PSEO Michigan coverage file](https://lehd.ces.census.gov/data/pseo/latest_release/mi/pseo_mi_institutions.csv) lists only University of Michigan. It does not cover these four institutions; Michigan graduate retention remains unavailable. Scorecard fills institution-level earnings/completion coverage, not state employment flows.

## Start here

Install and start **Docker Desktop** (Linux containers) or Docker Engine with Compose. No host Python, database, or build tools are required.

From this project folder, copy the settings once:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

On Linux/macOS, use `test -f .env || cp .env.example .env`. Then open the manager:

```sh
docker compose run --build --rm tui
```

Choose **1 — Start / apply configuration**. The first run builds the application and creates its data volume. Later runs reuse cached layers. Choose **q** to leave the manager; the service keeps running. Reopen with the same command.

## Terminal manager

The Rich console shows service state and health, with these actions:

| Key | Action |
| --- | --- |
| 1 | Build/start service and apply `.env` changes |
| 2 | Stop service, keeping all data |
| 3 | Reconcile and restart service |
| 4 | Show last 100 log lines |
| 5 | Initialize database (safe to repeat) |
| 6 | Audit evidence coverage and ledger integrity |
| 7 | List reviewed official source families |
| 8 | Build and run strict CI in an isolated container |
| 9 | Show credential configuration status without values |
| r | Refresh service status |
| q | Exit manager |

The manager is a trusted local administration tool: it alone mounts the Docker socket to operate this project's containers. The application runs as an unprivileged user and has no Docker socket access. There are no evidence-delete or volume-delete menu actions.

## Configuration

**Edit only `.env`** for deployment settings. It is ignored by Git and excluded from image builds. `.env.example` documents every variable.

| Variable | Default / purpose |
| --- | --- |
| `COMPOSE_PROJECT_NAME` | `michigan-workforce-intelligence`; scopes containers and the data volume |
| `MIJOBS_NETWORK_NAME` | `michigan-workforce`; shared network for agent containers |
| `MIJOBS_MCP_PORT` | `8000`; host and container HTTP port |
| `MIJOBS_DATABASE_URL` | `sqlite:////data/mijobs.db` |
| `MIJOBS_ARTIFACT_ROOT` | `/data/artifacts` |
| `MIJOBS_MCP_WRITE_ENABLED` | `false`; opt in explicitly to MCP evidence writes |
| `BLS_API_KEY`, `CENSUS_API_KEY` | Optional official API credentials |
| `ONET_USERNAME`, `ONET_PASSWORD` | Optional O*NET credentials |

Single-quote secrets containing `$` or `#`. After editing `.env`, reopen the manager and choose **Start / apply configuration**. Keep the default `/data` paths for persistent SQLite/artifacts. Changing the project name selects a different volume; it does not migrate the old data. No sources are downloaded automatically.

## ChatGPT desktop

Use the registered `michigan_workforce` MCP server in local ChatGPT desktop conversations. See [connection instructions and readiness limits](docs/chatgpt.md). The local evidence store is populated. See the verified coverage and query guide below; recent national data does not imply recent Michigan or university data.

## Agent container connection

Keep your agent in its own container and attach it to the shared `michigan-workforce` Docker network. Point its MCP client at **`http://workforce-mcp:8000/mcp`**. The network name is configured by `MIJOBS_NETWORK_NAME` in `.env`. The agent does not need database or Docker socket access.

See [agent wiring and optional Kubernetes deployment](deploy/README.md). Compose is the supported local setup; Kubernetes manifests can be generated later from the same `.env`.

## MCP

HTTP endpoint: **`http://127.0.0.1:8000/mcp`** (or the configured port). The service uses stateless Streamable HTTP and is published only on host loopback. Configure an MCP client that supports this transport with that URL. A protocol-aware Docker probe checks readiness; opening the endpoint in a browser is not a health check.

For stdio clients, set this project as the working directory and use:

```sh
docker compose run --rm -T --entrypoint mijobs-mcp cli
```

The default CLI and stdio MCP share the same persistent evidence store as HTTP. Existing MCP tools list sources, search observations/claims/mappings, trace evidence, audit the ledger, calculate compatible gaps, and evaluate explicit policy assumptions. Write tools remain opt-in. See [MCP contracts](specs/001-michigan-workforce-intelligence/contracts/mcp-tools.md).

## Data coverage and readiness

See [verification results and corrected report](docs/live-data-validation.md).

Earlier workforce-only snapshot on **2026-09-13**, before the university harvest below: SQLite integrity passed; all **9 immutable artifacts** matched their SHA-256 hashes. That baseline contained **248 observations** and **no taxonomy mappings**; the university harvest adds academic/outcome observations and official mappings. These are stored official responses, not a continuously refreshed feed.

| Stored metric | Geography | Coverage / rows | Meaning |
| --- | --- | --- | --- |
| `bls.cps.LNS14000000` | `US` | Jan 2020–Aug 2026 / 80 | Seasonally adjusted unemployment rate, percent |
| `bls.cps.LNU04000000` | `US` | Jan 2020–Aug 2026 / 80 | Unadjusted unemployment rate, percent |
| `bls.cps.LNS13000000` | `US` | Jan 2020–Aug 2026 / 80 | Seasonally adjusted unemployed persons, thousands |
| `qwi.Emp` | `26` (Michigan) | 2020 Q1–2021 Q4 / 8 | QWI beginning-of-quarter employment, persons; historical |

BLS observation units were ingested as `reported_value`; interpret them using the source series catalog, not the generic unit string. [BLS unemployment level](https://data.bls.gov/timeseries/LNS13000000) is distinct from [civilian labor force](https://data.bls.gov/timeseries/LNS11000000). Labor force (`LNS11000000`) and employment (`LNS12000000`) are in the corrected harvest plan but are not yet in this snapshot.

The verification found previously generated claims with swapped BLS meanings and a year-over-year comparison using the report month instead of the observation month. Corrections preserve prior evidence and use appended challenges/revisions. Always inspect **effective status and challenges**, even when an older claim's asserted status says supported.

**Supported now:** national unemployment trends, historical Michigan QWI comparisons, source/provenance checks, and evidence-linked structured reports. **Still unavailable:** current Michigan labor shortages, measured program-to-occupation placement, Michigan graduate retention, employer attraction forecasts and county-level comparisons. Current demand and Michigan retention analyses still need validated Michigan projections and state-linked outcome data. IPEDS, CIP–SOC and institution-level Scorecard outcomes are covered by the university workflow. A source registry entry or institution entry is not an ingested dataset.

## Ask questions through MCP

Use `michigan_workforce` in the desktop app. The service exposes **20 tools**; reconnect the client after deploying an updated server if it still shows the original 14. MCP queries use bounded application tools rather than unrestricted SQL. They do not fetch new official releases automatically.

Start with this prompt:

> Use michigan_workforce. Audit the ledger, inspect stored observations, and answer only from returned evidence. Distinguish U.S. from Michigan, state observation periods and units, and trace each factual conclusion to its artifact. Treat missing data as unknown and include contested claims and caveats.

| What you want | Tools / example request |
| --- | --- |
| Available source families | `sources_list`: “Which official sources could we ingest?” This is availability, not coverage. |
| National unemployment trend | `observations_search`: “Find the latest stored U.S. seasonally adjusted rate and compare with the same month one year earlier.” |
| Historical Michigan employment | `observations_search`: “Compare Michigan QWI Emp in 2021 Q4 and 2020 Q4; label this historical and explain coverage.” |
| Provenance and reliability | `artifacts_get`, `claims_get`, `claims_trace`: “Show the source locator, retrieval time, hash, inputs, revisions and challenges behind this claim.” |
| Existing conclusions | `claims_search`: “List latest claim versions and their effective statuses; exclude contested conclusions from the headline.” |
| Evidence integrity | `ledger_verify`, `ledger_audit`: “Verify both the chain and evidence coverage before drafting a report.” |
| Crosswalk availability | `mappings_search`: “Find CIP 11.0701 to SOC mappings and report versions.” Official CIP 2020–SOC 2018 relationships are loaded by `harvest-universities`. |
| Briefing or report | `report_context`: “Build context for these claim IDs, then draft an executive brief with evidence, dates, limitations and data gaps.” |
| Narrow annual training gap | `gap_training_pipeline`: supply compatible annual completions/openings using `people_per_year`, geography and taxonomy; no automatic data retrieval. |
| Job-ad signal | `gap_market_tightness`: supply `online_job_ads` and `available_people`; ads are not unique jobs or a measured shortage. |
| Training policy assumptions | `policy_training_scenario`: compare explicit low/base/high assumptions; not causal impact estimation. |
| Institution lookup | `partner_institutions_list`: curated institution metadata; not proof of a partnership or available outcomes. |
| Degree alignment scenario | `university_degree_relevance`: supply completions, demand and crosswalk rows. |
| Pipeline scenario | `university_pipeline_balance`: supplied counts only; see limitations below. |
| Retention scenario | `university_retention_risk`: supplied graduate count and rates; not observed retention. |
| Business attraction scenario | `business_attraction`: supplied establishment/employment projections, occupations and optional wages; heuristic score. |
| Combine institution scenarios | `university_summary`: supply prior pipeline results and optional retention results. |
| Dispute a claim | `claims_challenge`: append a rationale; disabled while `MIJOBS_MCP_WRITE_ENABLED=false`. |

Exact database query examples (tool arguments):

```json
{"metric":"bls.cps.LNS14000000","geography_code":"US","latest_only":true,"limit":500}
```

```json
{"metric":"qwi.Emp","geography_code":"26","latest_only":true,"limit":500}
```

`latest_only` selects the newest **revision of each observation key**, not the most recent month. Results are ordered by ingestion time, not observation period. Select the maximum `period_start` after fetching the relevant series; use the same month/quarter for year-over-year comparisons. Queries allow 1–500 rows, have no pagination or date-range parameters, and must not be treated as exhaustive when the limit is reached. Geography filters are exact: stored Michigan QWI uses `26`, not `MI`.

For a report, first call `claims_search` with `{"latest_only":true,"limit":100}`, inspect `effective_status`, and pass selected returned IDs to `report_context`:

```json
{"claim_ids":["<returned claim id>"]}
```

Ask the assistant to turn that context into a narrative. `report_context` is read-only; it does not create a PDF, retrieve missing datasets, or invent a conclusion.

### University and policy scenarios

The curated registry uses these NCES UnitIDs: [Lawrence Technological University 170675](https://nces.ed.gov/ipeds/reported-data/170675), [Rochester Christian University 170967](https://nces.ed.gov/ipeds/reported-data/170967), [Oakland University 171571](https://nces.ed.gov/ipeds/reported-data/171571), and [Kettering University 169983](https://nces.ed.gov/ipeds/reported-data/169983). Focus areas are curated context, not measured outcomes.

Example **hypothetical** payload for `university_degree_relevance` (also accepted by `university_pipeline_balance`):

```json
{"payload":{
  "institution_unitid":"170675",
  "completions":[{"cip_code":"11.0701","cip_version":"2020","annual_completions":"100"}],
  "demand":[{"soc_code":"15-1252","soc_version":"2018","geography_code":"MI","annual_openings":"150"}],
  "crosswalk":[{"from_code":"11.0701","to_code":"15-1252","from_version":"2020","to_version":"2018","relation":"related"}]
}}
```

These numbers and the supplied edge are an illustrative scenario, not verified university evidence. The calculators do not authenticate crosswalks or retrieve observations. Validate compatible years, geography, units and code versions before supplying real inputs.

The university models are exploratory: the pipeline implementation compares all supplied completions with matched occupational openings; unmatched programs can distort the result. Shared occupations can be counted again when institution summaries are combined. Retention uses `graduates × resident_share × (1 − out_migration_rate)`; `in_state_job_match_rate` is accepted but unused. Business attraction uses hand-set weights and openings as a supply proxy. None supports a factual ranking or a claim about actual migration/business decisions. Prefer the stricter `gap_training_pipeline` for a narrow comparison with compatible inputs.

Try:

> Run a hypothetical retention scenario for UnitID 170675 with 100 graduates, Michigan resident share 0.8, in-state job match rate 0.7 and out-migration rate 0.25. Show the formula, assumptions and unused inputs; do not call it an observed outcome.

## Harvest and generate reports

All operations run in Docker. Review the plan before requesting official data:

```sh
docker compose run --rm -T cli harvest --start-year 2020 --end-year 2026 --dry-run
docker compose run --rm -T cli harvest --start-year 2020 --end-year 2026 --no-include-qwi
```

The second command **writes evidence** and requires `BLS_API_KEY` in `.env` in this CLI implementation. Remove `--no-include-qwi` to include Michigan QWI, with `CENSUS_API_KEY` configured. Inspect the returned task statuses: missing connectors are skipped; a successful process exit alone does not prove all requested data arrived. Unavailable quarters can fail. Repeated runs can create observation revisions; ingestion is not scheduled automatically.

Generate a structured JSON insights report from stored data:

```powershell
New-Item -ItemType Directory -Force artifacts/reports | Out-Null
docker compose run --rm -T cli report --as-of 2026-09-13 > artifacts/reports/insights.json
docker compose run --rm -T cli audit-ledger
```

`report` **appends derived metrics, versioned claims and ledger events**. It verifies evidence integrity before computation. Missing series produce `insufficient_data`. The reference date limits observation periods; it does not reconstruct what was known on that date or restore older release vintages. Re-running creates new claim versions. Raw source artifacts remain unchanged. Report output is ignored by Git; keep credentials only in `.env`.

The six report sections cover national unemployment rate, same-month annual change, unemployed persons, labor force, Michigan QWI employment, and QWI annual change. They are a starting briefing, not a complete university or economic development report.

## Commands and quality checks

Every menu action also works without an interactive terminal:

```sh
docker compose run --rm -T tui status
docker compose run --rm -T tui start
docker compose run --rm -T tui audit-ledger
docker compose run --rm -T tui ci
```

Direct equivalents:

```sh
docker compose up --build -d --wait app
docker compose run --build --rm -T cli sources
docker compose run --build --rm -T cli audit-ledger
docker compose run --build --rm -T ci
docker compose stop app
```

CI enforces governance, compilation, unit tests with **at least 90% coverage**, source registry validation, spec traceability, Ruff, and strict Mypy. Runtime and CI dependencies are resolved in `uv.lock`; Docker installs with `--frozen`. CI includes official Rust Token Killer and Spec Kit. CI uses isolated temporary storage and receives no production credentials or evidence volume.

The optional Makefile wraps these Docker commands. `make ci-local` is the internal container gate; host development can use a Python virtual environment but is not needed for operations.

## Persistence and troubleshooting

The single Compose `evidence` volume holds the database and content-addressed artifacts. Stop, restart, rebuild, and manager exit preserve it. Back up the whole volume with the app stopped to keep SQLite and artifact files together. Never use `docker compose down -v` unless you intend to erase the local evidence store.

- **Docker unavailable:** start Docker Desktop and wait for `docker info` to succeed. The manager cannot repair the host engine from inside a container.
- **Desktop `sailor-ingest.sock` startup error:** first wait and recheck `docker info`; startup can recover. If it persists, fully quit/restart Docker Desktop. Do not factory-reset or delete WSL data as a routine fix.
- **Port busy:** change `MIJOBS_MCP_PORT` in `.env`, reopen the manager, and choose Start.
- **Service unhealthy:** inspect Logs. Check `.env` for valid paths and a port from 1–65535.
- **Changed code or dependencies:** reopen with `--build`; Start and CI build their current targets from the mounted source.
- **Timed-out action:** Docker may still be completing it; inspect Status and Logs before retrying.

## Project map

- `src/mijobs/`: sources, ingestion, provenance, analytics, CLI/MCP, and terminal manager.
- `config/sources.json`: reviewed registry of 30 source families (see implementation status).
- `tests/`: offline evidence, adapter, runtime, and management tests.
- `specs/001-michigan-workforce-intelligence/`: foundation requirements and evidence contracts.
- `specs/002-docker-terminal-manager/`: implementation plan, tasks, and validation for this setup.
- `.specify/`, `.agents/skills/`, `AGENTS.md`, `RTK.md`: Spec Kit/Codex governance.

See [source methodology](docs/source-methodology.md) and [roadmap](docs/roadmap.md). Model-generated prose is never source evidence.

## County jobs reports and job continuity companions

The September 13, 2026 evidence snapshot contains **2,365 observations, 38 artifact records and 8,193 audited ledger events**. This supersedes the earlier baseline counts elsewhere in historical validation notes. The added evidence includes county/state BLS series, QCEW payroll jobs and wages, BEA regional price parities and ACS earnings/rents. Catalog entries alone do not mean their datasets have been collected.

Start with the [jobs and economic analysis](reports/2026-09-13-job-continuity/jobs-context.md) and [full database reanalysis](reports/2026-09-13-job-continuity/data-reanalysis.md). The primary report covers Macomb, Oakland, Wayne and Michigan. Supplemental publications cover [job continuity](reports/2026-09-13-job-continuity/report.md), [Job Corps](reports/2026-09-13-job-continuity/job-corps.md), and [APEX, Velocity and employer advance signals](reports/2026-09-13-job-continuity/partners-and-signals.md). Candidate partners have not committed capacity or funding.

[Portable Docker build and release instructions](docs/report-operations.md) explain collection, read-only reanalysis, PDF generation, page review, timestamp versions and GitHub releases. All credentials stay in `.env`. University outcomes are reused, not reloaded by reanalysis. Released public snapshots exclude the live database and worker information.

Ask naturally using the [report prompt templates](.agents/skills/michigan-workforce-reports/references/prompts.md), for example:

- “Compare jobs, unemployment and wages in Macomb, Oakland, Wayne and Michigan; show trends and evidence gaps.”
- “Compare Michigan purchasing power with Ohio, Indiana, Wisconsin, Illinois, Texas, California and North Carolina using compatible years; identify realistic talent-attraction advantages and limitations.”
- “Design an automotive job-continuity pilot with APEX, Velocity, MMTC, Michigan Works! and Job Corps. Show how advance employer reports could support voluntary transitions before cuts.”
- “Find paid pathways for an at-risk production worker into manufacturing, engineering support or aerospace; distinguish verified jobs from potential pathways.”

The MCP exposes `economic_indicators(geography_code)` to discover stored metrics and `economic_trend(geography_code, metric, limit)` for bounded evidence-linked history. County codes are `26099`, `26125`, `26163`; Michigan is `26`. Examples include `laus.unemployment_rate`, `qcew.oty_month3_emplvl_chg`, `bea.rpp.all_items` and `acs.median_earnings`. Discovery is the authority for exact available metrics. Keep adjustment, observation period, population and units together. Other states use their two-digit FIPS codes. Missing evidence stays missing; the tools do not infer placements or predict layoffs.

The secure, multi-employer reporting and worker-referral exchange is **proposed**, not deployed. It needs identity verification, tenant permissions, consent, expiry, access audits and confirmed receiving offers. An 11-year automotive cycle is an unverified hypothesis, not a forecasting rule. Sentiment, projections, observed outcomes and scenario assumptions must remain separate.

## Data credits and source rules

[![O*NET OnLine](docs/assets/onet-online.png)](https://www.onetonline.org/)

O*NET content is developed by the U.S. Department of Labor, Employment and Training Administration, and provided through the National Center for O*NET Development. Applicable O*NET content is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The authorized graphic is unmodified. Report interpretations and transformations are this project's; no endorsement is implied. See [prominent third-party notices](THIRD_PARTY_NOTICES.md) for attribution, modifications and all other provider credits; these also appear in every PDF.

[Source/API policy](docs/source-policy.md) documents implemented shared quotas, conservative request spacing, cooldown handling, catalog-only sources and redistribution limits. A source listing is not an API implementation or a blanket redistribution license. Other machines using the same account can consume quota outside this local limiter; operators must reconcile account-wide use before raising limits.
