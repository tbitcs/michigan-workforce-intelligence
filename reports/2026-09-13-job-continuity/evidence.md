# Evidence appendix and database audit

Review date: September 13, 2026. **Historical baseline audit**, before the county and interstate expansion: both chain and evidence-row coverage were valid with **6,520 events and 6,520 covered entities**, no uncovered rows. Baseline head:

`fe6cba8841e75112756a36c46e077c74ee77ff53e0cc5295ac561a2b7408c15e`

The later scripted expansion added BLS county/state indicators, QCEW, BEA prices and ACS earnings/rents. The current audited snapshot has **8,193 events, 2,365 observations and 38 artifact records**; see [full reanalysis](data-reanalysis.md) and `analysis-snapshot.json` for the current head and periods. University outcomes were not reloaded. API credentials were preserved. Integrity does not establish source accuracy, timeliness, completeness or causal validity. Reviewed narrative sources remain separate from ingested evidence.

## Stored observation coverage

| Family | Loaded coverage / period | Definition and analytical limit |
|---|---|---|
| National CPS | 240 observations: three series × 80 months, January 2020–August 2026; US | Seasonally adjusted unemployment rate; unadjusted unemployment rate; unemployed persons in thousands. Not Michigan counts; raw `reported_value` needs catalog interpretation |
| Michigan QWI | 8 `qwi.Emp` rows, 2020Q1–2021Q4; state FIPS 26 | Beginning-of-quarter covered employment, not current vacancies or total available workers |
| IPEDS completions | 461 observations, C2024_A; four institutions; academic period July 2023–June 2024 | Awards include first/second-major and aggregate rows. Analytical totals use first-major six-digit CIP only; awards are not unique people |
| College Scorecard | 8 observations, two measures per institution | API data-year 2020 ten-year-after-entry median earnings; API 2024 completion within 150% normal time. Different cohorts, not contemporaneous graduate outcomes |
| Crosswalk | 5,723 CIP 2020–SOC 2018 mapping edges, separate from observations | Related pathways, not measured placements, worker availability or hiring demand |

Historical baseline observations: **717** (superseded by the expanded total above). The prior live-data validation recorded **13 hash-verified raw artifacts**. The ledger also preserves challenged historical claims; read effective claim status instead of using every old report as current evidence. See [local validation](../../docs/live-data-validation.md) and the [read-only university report](../../artifacts/reports/universities.json), which is generated locally and Git-ignored.

## Institutional baseline

| Institution / UnitID | First-major awards | Median earnings, separate entrant cohort | Completion fraction, separate cohort |
|---|---:|---:|---:|
| Lawrence Technological / 170675 | 652 | $69,151 | 0.6058 |
| Rochester Christian / 170967 | 196 | $48,707 | 0.4412 |
| Oakland / 171571 | 4,158 | $58,612 | 0.5756 |
| Kettering / 169983 | 494 | $94,823 | 0.7080 |

Earnings concern federally aided entrants working and not enrolled ten years after entry, not all graduates or a 2024 graduating class. Completion is first-time full-time completion within 150% of normal time. API field year is not asserted to be the earnings calendar year. Institution types and degree/program mixes differ; these figures do not establish causal institutional performance. No loaded Michigan-retention outcome exists for these four institutions. The retrieved PSEO Michigan institution inventory lists University of Michigan, OPEID 00232500, rather than these four; UnitIDs and OPEIDs are different identifiers.

## Reproducible stored provenance

| Evidence | Artifact ID | SHA-256 |
|---|---|---|
| [IPEDS C2024_A](https://nces.ed.gov/ipeds/datacenter/data/C2024_A.zip) | `200abf5e-5b76-439b-b8fd-97a9b8e9b4c3` | `03234cc27fe4e7eb835a66d4f37aaec11bdac8dfa278f971584e1b20d03e1159` |
| [CIP–SOC crosswalk](https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx) | `1c76c1bb-8fa1-4d8c-a351-9c5921489985` | `ba3d59a191b9d977a5c457a66b9348c4f2f7963aafacf72c0b80113b46bf0ab8` |
| [PSEO coverage](https://lehd.ces.census.gov/data/pseo/latest_release/mi/pseo_mi_institutions.csv) | `baee60f1-47fd-4cfe-9173-7c9aec0c4b23` | `cf7e4f25ec85906f93ab8637db1fbc51fab72147a53076e7fd751652431c3961` |
| Scorecard reviewed four-school API response | `e0b41d1b-c4a8-4a94-b410-864d5fa47d01` | `a71f6a423215c1d355306f0a3787c34edf041e80eb9b2c0baa82b36f11b941c3` |

The local university JSON preserves individual observation IDs, original source locator and retrieval timestamps. For example, Kettering earnings observation `536b1abe-27d2-4f2e-bc52-d5b87c0902c4` and completion `a6a744f0-eedd-4611-ba59-a0bdec3b9cb0` reference the Scorecard artifact above. Exact API fields are `2020.earnings.10_yrs_after_entry.median` and `2024.completion.completion_rate_4yr_150nt`. No API key is included in this report.

## External evidence register

Links are placed next to the claims/tables they support, rather than detached from the analysis. Research accessed on the review date is not an immutable archived snapshot; pages can change. Reverify before implementation.

| Source group | Observation/publication basis | Use and limitation | Location |
|---|---|---|---|
| Michigan MCDA July release | July 2026, published August 20 | Current state/Detroit labor-market context; not occupation vacancies | [Demand](report.md#1-demand-employment-and-early-risks) |
| MCDA Career Outlook | 2026 publication, 2024–2034 projections | Selected occupations, annual openings, growth and published wage bands; wage reference year not separately asserted | [Demand table](report.md#1-demand-employment-and-early-risks) |
| MCDA projection inventory | State 2024–2034; regional linked filenames 2022–2032 | Identifies different vintages; attempted workbook downloads returned 403 | [Demand limitations](report.md#1-demand-employment-and-early-risks) |
| O*NET/BLS local wage views | 2025 wage estimates | Occupational/metro benchmarks; not individual offers | [Wage matrix](matrices.md#wage-comparison-and-regional-matrix) |
| MEDC defense strategy | February 2026 announcement | Strategic opportunity, not jobs or contract awards | [Defense discussion](report.md#2-skills-and-practical-transitions) |
| UIA/LEO/US DOL/MiLEAP | Operative rules, dated 2026 updates and current program pages | Eligibility pathways; no administrator balance or award confirmation | [Funding](funding.md) |
| Colleges/NIST/FAA/LARA/DCSA/DOJ/DFARS | Current provider and regulatory pages | Route/role screening; no individual licensing or clearance decision | [Pathways](matrices.md), [requirements](report.md#2-skills-and-practical-transitions) |
| DOJ/FTC worker guidelines | January 2025, listed on current official policy pages | Independent employer coordination and worker mobility | [Prevention design](report.md#3-prevent-separation-before-subsidizing-reemployment) |

## Definitions that must remain separate

**Employment level** is a stock measured for a reference period; **projected annual openings** estimate growth plus occupational separations over a projection interval; **active vacancies** require current employer hiring authority; **job advertisements** may be duplicate, stale, evergreen or cover multiple positions. None is a count of available trained workers.

**Skills gap** requires observed worker capabilities and actual essential job requirements. A crosswalk or employer complaint alone does not measure its size. **Shortage** requires evidence of hiring difficulty at the offered compensation and conditions; a high growth percentage alone does not prove it. **Retained worker**, **new placement**, **training completer** and **additional job saved versus control** are different outcomes.

## Missing evidence and how to resolve it

| Missing input | Consequence now | Proposed owner / collection |
|---|---|---|
| Dated funded employer requisitions and interview outcomes | Cannot call pathways presently available | Employer lead verifies before cohort purchase |
| Consented worker skills, wages, hours and preferences | Cannot compute individual gaps/pay change | Navigators use assessments and work samples |
| Regional projections on comparable vintage; current layoff inventory | No quantitative regional shortage/risk ranking | Analyst obtains accessible official files and dated notices |
| Provider tuition, fees, next seats and paid release | Cost/duration envelopes remain assumptions | Providers give dated quotes; employers approve schedules |
| Local grant balances and case eligibility | No committed public revenue or universally cleared stack | Fiscal lead obtains written administrator decisions |
| Michigan residence and placement follow-up | Cannot claim institutional retention or actual jobs saved | Consented follow-up; authorized administrative linkage if available |
| Credible comparison outcomes | Scenario is not a causal forecast or ROI | Independent evaluator prespecifies comparison |
| Housing, transit and childcare costs by actual household/shift | Cannot price universal relocation or barrier effects | Case-specific verified quotes and service availability |

The report completes an evidence-qualified design, not a statewide census, funding approval or individualized placement assessment. Missing evidence is retained explicitly so the next report can replace assumptions rather than silently treating them as facts.
