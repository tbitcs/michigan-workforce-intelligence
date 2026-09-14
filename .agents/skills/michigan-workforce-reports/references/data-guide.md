# Data and tool guide

The configured service is `michigan_workforce`; its tool prefix varies by client. Users do not need this guide to ask questions.

1. `ledger_audit` checks the event chain and evidence coverage. A valid audit establishes integrity, not statistical correctness or freshness.
2. `observations_search` accepts exact `metric`, `geography_code`, `taxonomy_code`, `source_artifact_id`, `latest_only`, `limit`. Limits are 1–500 with no pagination/date filter. `latest_only` means latest revision per key; ordering is ingestion time, not measurement date. Narrow queries; if limit is reached do not assume completeness.
3. `artifacts_get` gives source locator, retrieval date, hash and parser. `claims_search`, `claims_get`, `claims_trace` distinguish asserted/effective status and preserve challenges. `report_context` creates read-only, traced context for selected claim IDs, not a finished narrative.
4. `mappings_search` uses from/to systems and codes. Keep CIP 2020/SOC 2018 explicit; related edges are neither placement probabilities nor available workers.

## Known metric meanings; inspect live coverage each time

| Metric | Geography | Interpretation |
| --- | --- | --- |
| bls.cps.LNS14000000 | US | Seasonally adjusted national unemployment %, not Michigan |
| bls.cps.LNU04000000 | US | Unadjusted unemployment %, not a person count |
| bls.cps.LNS13000000 | US | Unemployed persons, thousands; not labor force |
| bls.cps.LNS11000000 | US | Civilian labor force; may be absent |
| qwi.Emp | 26 | Michigan beginning-of-quarter covered employment; historically limited |
| ipeds.completions.awards | institution UnitID | Credentials, not unique graduates. Select major_number=1, six-digit CIP rows, exclude aggregate totals; keep award levels/year explicit |
| scorecard.earnings.10_years_after_entry.median | UnitID | Federal-aid entrant cohort, working/not enrolled; not graduate salary or Michigan retention. Read api_field/data_year metadata |
| scorecard.completion.4yr_150pct | UnitID | Fraction, not percent. First-time full-time completion within 150% normal time |

Candidate institutions only: Lawrence Technological 170675; Rochester Christian 170967; Oakland 171571; Kettering 169983. Curated registry membership does not establish an institutional partnership.

The 2026-09-13 baseline includes 2024 IPEDS, Scorecard API data-year 2020 earnings and 2024 completion, official crosswalks, recent national CPS and historical Michigan QWI. Never use this note as a current coverage assertion.

`gap_training_pipeline` requires matching geography, annual basis, SOC/version/code and `people_per_year`; IPEDS awards require justified transformations before use. Other university/policy calculators consume supplied inputs, do not fetch or authenticate data, and are exploratory. University aggregate demand can double-count overlapping occupations. Retention's simplified formula does not use in_state_job_match_rate. Prefer explicit, independently checked scenario arithmetic for consequential program designs.

When working in the repository, Docker `cli report-universities --year 2024` is read-only; `cli report` appends derived records and claims, and `harvest*` writes evidence. Do not run a write command merely to answer a read-only question. Credentials stay in .env and out of reports.

The economic registry includes county/state BLS series, national benchmarks, Ohio/California/Texas/Florida comparisons and national U-6/participation/employment-population/involuntary-part-time series. The BLS state underutilization table uses `bls.underutilization.u1` through `.u6`, an 11-month window excluding October 2025; it is not county evidence. Monthly `economic_trend` output includes a reference outlook only when coverage and compatibility checks pass. Its stress ranges are not confidence intervals.

`partner_institutions_list` returns four data-covered candidates plus a separate additional-candidate research catalog. No institution is represented or committed. Homelessness figures in the narrative are outside the database unless a query establishes later ingestion. The separate authenticated employer exchange cannot be queried through the public evidence tools.
