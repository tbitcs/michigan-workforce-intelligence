# Data Model

## Evidence chain

`Source -> SourceArtifact -> Observation -> EvidenceEdge -> Claim -> DerivedClaim/ReportContext`

Taxonomy and derivation subgraphs are first-class:

`SourceArtifact -> TaxonomyMapping(CIP/SOC/O*NET-SOC/NAICS/geo)`

`Observation/Claim/DerivedMetric -> DerivedMetric -> Claim/ReportContext`

## Audit chain

Every evidentiary write -> `LedgerEvent[n]` -> SHA-256 -> `LedgerEvent[n+1].previous_hash`.

A second coverage audit checks that every persisted source artifact, observation, claim, evidence edge, challenge, taxonomy mapping, and derived metric has at least one corresponding ledger event. A cryptographically valid chain with missing application records is considered invalid for reporting.

## Core distinctions

- **Source**: agency/dataset family and methodology metadata.
- **SourceArtifact**: exact bytes/release retrieved from a source, identified by checksum.
- **Observation**: normalized value reported/extracted from an artifact. A published projection can be stored as an observation of what an official source projected, but remains labeled as a projection in metric/release metadata.
- **Claim**: proposition asserted from one or more observations/claims.
- **EvidenceEdge**: typed support/contradiction/qualification/derivation relationship.
- **Challenge**: explicit contestation of a claim with rationale and optional evidence.
- **TaxonomyMapping**: versioned source-backed relationship between code systems or vintages. Crosswalk edges are not probabilities unless the source actually provides a probability/weight.
- **DerivedMetricRecord**: reproducible calculation with formula name/version, exact input references, assumptions, caveats, units, scope, and supersession.
- **LedgerEvent**: immutable event describing evidentiary state change.

Claims use a stable `claim_key` plus monotonically increasing `version`; a revision creates a new claim row and `supersedes_claim_id`. Observations, taxonomy mappings, and derived metrics use the same append/supersede pattern.

## Critical version dimensions

Dataset release and taxonomy release are not interchangeable. For example, O*NET Database 31.0 currently uses O*NET-SOC 2019, which is aligned to 2018 SOC. The model stores those as separate fields/metadata so a quarterly database update cannot silently masquerade as a taxonomy revision.
