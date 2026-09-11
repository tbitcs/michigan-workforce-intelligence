# Requirements Quality Checklist

- [x] Every baseline write operation has provenance requirements.
- [x] Observation and interpretation semantics are separated.
- [x] Revision and contestation are non-destructive.
- [x] Hash-chain verification behavior is testable.
- [x] Unknown/missing and incompatible data are explicitly handled.
- [x] Source credentials are environment-only.
- [x] Baseline excludes restricted person-level data.
- [x] MCP mutation is opt-in.
- [x] Analytics formulas are deterministic/versioned.
- [x] Local CI and unit tests are required.
- [x] Implemented source-specific parsers fail closed when required schema is absent.
- [x] IPEDS release status and enrollment basis remain explicit.
- [x] O*NET database release and O*NET-SOC taxonomy version remain separate.
- [x] Taxonomy crosswalks are versioned, immutable, and source-artifact backed.
- [x] Derived metrics persist formula version, exact inputs, assumptions, and caveats.
- [x] Ledger verification includes both chain integrity and evidence-row coverage.
- [x] Policy what-if analysis requires explicit counterfactual assumptions and exposes low/base/high sensitivity cases.
- [x] Unimplemented source-specific ingestion is tracked as open tasks rather than implied complete.
