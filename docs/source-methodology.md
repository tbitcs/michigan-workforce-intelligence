# Source Methodology Guardrails

This project treats source definitions as part of the evidence. A number without its population, geography, period, unit, release, adjustment, and taxonomy is incomplete.

## Michigan labor-market families

### LAUS
Residence-based estimates of people in the labor force, employment, unemployment, and unemployment rate. Do not equate LAUS employment with payroll jobs. Preserve seasonal-adjustment status and revision/rebenchmark information when available.

### CES/QCEW/OEWS
Payroll/establishment programs answer different questions from LAUS. QCEW is largely administrative UI-covered employment and wage data; OEWS is an occupational employment/wage snapshot. Michigan MCDA specifically cautions that OEWS estimates should not be treated as a simple year-to-year time series. The parser therefore stamps the snapshot caveat into normalized OEWS observations.

### Michigan employment projections
The current statewide/regional long-term horizon is 2024-2034. Base employment, projected employment, percent/numeric change, and annual openings remain separate observations. Annual openings are a rate-like flow (`jobs_per_year`), not a stock of jobs.

### Online job advertisements
Advertisements are demand signals, not unique vacancies or hires. Deduplication, posting duration, carry-over, source coverage, and occupation-coding methodology must accompany any use in a tightness metric.

## Education pipeline

### IPEDS
IPEDS release status matters. Provisional data may later be revised; final data can therefore differ from tables built from earlier provisional releases. Store the release status with every artifact.

Completions use institution UnitID + CIP code + award level. A completion/award count is not the same as an unduplicated graduate count unless the source measure explicitly says so.

12-month enrollment is an unduplicated headcount over a 12-month period; Fall Enrollment is a fall snapshot. They are intentionally separate metrics and must not be interchanged.

### CIP -> SOC
The official CIP 2020 -> SOC 2018 crosswalk represents documented program-to-occupation relationships. One CIP can map to multiple SOC occupations and one SOC can map to multiple CIPs. The baseline stores these edges as `RELATED` with no fabricated probability weight.

## O*NET
O*NET Database release and taxonomy version are independent. Current O*NET Database 31.0 uses O*NET-SOC 2019, which is aligned to 2018 SOC. Skill/ability/knowledge ratings remain attached to O*NET-SOC occupations and retain the database release separately.

Software-skill examples are categorical evidence. `hot_technology` and `in_demand` flags are retained as published metadata; software examples are not converted into made-up numeric skill scores.

## Cross-source comparisons

Before a deterministic formula combines values, verify at minimum:

- semantic definition / population;
- unit and stock-vs-flow character;
- geography and residence-vs-workplace basis;
- period and annualization assumptions;
- taxonomy system, version, and code granularity;
- seasonal adjustment or other transformations;
- provisional/final/suppressed status;
- known source coverage limitations.

If these conditions are not satisfied, return `incompatible` or `unknown` and surface the mismatch. Policy usefulness never justifies hidden coercion.
