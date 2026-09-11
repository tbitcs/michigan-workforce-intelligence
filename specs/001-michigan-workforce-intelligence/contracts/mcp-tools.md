# MCP Tool Contract

Read tools:
- `sources_list()` - reviewed source catalog.
- `observations_search(...)` - bounded observation query with explicit filters/version behavior.
- `artifacts_get(artifact_id)` - exact provenance metadata for a source artifact.
- `claims_get(claim_id)` - claim plus current version metadata.
- `claims_search(...)` - bounded claim query.
- `claims_trace(claim_id)` - claim, evidence edges, challenges, source artifacts, derivations, and ledger references.
- `mappings_search(...)` - bounded versioned taxonomy-crosswalk query.
- `ledger_verify()` - verifies sequence, previous hashes, payload hashes, and event hashes.
- `ledger_audit()` - verifies that every evidence-bearing row is represented in the ledger.
- `gap_training_pipeline(...)` - deterministic annualized pipeline gap.
- `gap_market_tightness(...)` - job-ad/unemployed ratio with explicit interpretation caveat.
- `policy_training_scenario(...)` - explicit low/base/high what-if model; causal rates are caller-supplied, never inferred.
- `report_context(claim_ids)` - structured evidence bundle for a report writer; refuses unledgered evidence.

Write tools (disabled unless `MIJOBS_MCP_WRITE_ENABLED=true`):
- `claims_challenge(...)` - append a challenge to an existing claim; never edits the claim.

All query tools are bounded to avoid accidental context explosions. MCP responses must distinguish data, derivation, caveat, and epistemic status. The MCP layer does not fetch arbitrary web content, fabricate source values, or bypass repository/ledger writes.
