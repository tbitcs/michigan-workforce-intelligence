# University report readiness

User request: retain configured credentials, load official university evidence, and make reports runnable in Docker.

FR-001: Harvest official IPEDS completion data for the four registered institutions, preserving source vintage, major number and award level without double-counting totals.
FR-002: Load official CIP/SOC mappings and verify actual PSEO institutional coverage; unavailable outcomes remain unknown.
FR-003: Provide a repeatable Docker university report from stored evidence, with artifact/observation lineage and clear limits.
ER-001: Preserve .env secrets and append-only evidence; refuse reports on unaudited data.

Clarification: academic completions and graduate employment outcomes are different. Census coverage cannot be invented. No new infrastructure or dependencies.

FR-004: Ingest official College Scorecard earnings and completion measures for all four institutions using explicit API data-year fields, preserving cohort caveats and nulls. Michigan retention stays unknown.
