# Roadmap

## Phase 1 - Evidence foundation (implemented)
Hash-chained evidence ledger, ledger-coverage audit, source catalog, immutable/versioned claims and observations, challenge model, source-backed taxonomy mappings, persisted derivations, BLS/Census connectors, deterministic analytics, bounded MCP facade, local CI with coverage floor, and Spec Kit/RTK governance.

## Phase 2 - Michigan ingestion depth (in progress)
Schema-detecting MCDA OEWS and 2024-2034 occupational-projection parsers are implemented with offline XLSX fixtures. Next: validate against exact current Michigan binaries, add LAUS/QCEW release-specific loaders, online-job-ad release ingestion, MI School Data exports, and Prosperity Region/county hierarchy.

## Phase 3 - Education-to-occupation graph (in progress)
IPEDS institution/completions/fall/12-month enrollment loaders, CIP 2020 -> SOC 2018 mapping, O*NET 31.0 ratings/software skills, and versioned taxonomy storage are implemented. Next: official O*NET-SOC 2019 -> SOC 2018 mapping, STARR aggregate program data where publicly accessible, apprenticeship pipeline, and workforce-outcome joins.

## Phase 4 - Worker-flow/geospatial layer
QWI, LODES commuting flows, PSEO outcomes, county/MSA/WIA/Prosperity Region mappings, migration, regional concentration, and origin-destination analysis.

## Phase 5 - Epistemic reporting/policy lab
Evidence trees, contested-claim workflows, sensitivity analysis, intervention scenarios, reproducible report manifests, signed/Merkle ledger checkpoints, visualization layer, and policy briefing outputs whose conclusions remain traceable to source artifacts.
