# Validation

- Docker CI: 216 tests, 90.48% coverage; governance, 48 requirement mappings, Ruff and strict Mypy pass.
- App rebuilt and healthy. Existing BLS/Census keys remain configured. Scorecard uses public DEMO_KEY through .env.
- Official harvest: 461 IPEDS completion rows, 5723 CIP/SOC mappings, 8 Scorecard observations, plus PSEO coverage artifact.
- All 469 newly loaded observation values and 5723 mapping keys reconcile to immutable raw evidence. All 13 raw hashes verify; SQLite integrity is ok.
- Ledger: 6520 events/entities, full coverage, valid head fe6cba8841e75112756a36c46e077c74ee77ff53e0cc5295ac561a2b7408c15e.
- Live desktop MCP returned earnings for all four institutions and 13 mappings for CIP 11.0701.
- Docker report-universities generated source-linked JSON for all four institutions. Local university-brief.md provides a readable initial report.
- PSEO Michigan covers University of Michigan only. Scorecard institution outcomes do not provide Michigan graduate retention. API years are preserved separately from cohort/measurement dates.
- Evidence logs: .venv/security-audit/university-ci-final.log, university-harvest.json, university-ledger.json, university-raw-validation.txt.
