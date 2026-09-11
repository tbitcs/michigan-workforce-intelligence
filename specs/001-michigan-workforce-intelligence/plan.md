# Implementation Plan: Michigan Workforce Intelligence Foundation

## Context
Build a Michigan-first, state-portable workforce evidence platform. Use official aggregate data, immutable artifacts, versioned facts/claims/mappings/derivations, a cryptographic event ledger, deterministic analytics, and a thin MCP v2 interface.

## Constitution check
PASS: artifact immutability, contestability, deterministic derivations, source preference, privacy minimization, local tests, reasoning economy, and portability are reflected in architecture and tasks.

## Architecture
1. `sources/`: adapters retrieve or parse official bytes/JSON/XLSX and return source envelopes/normalized inputs; adapters do not write the database.
2. `ingestion.py`: stores artifact bytes by hash, records source artifact metadata, emits ledger events, and normalizes observations/mappings.
3. `models.py`: versioned SQLAlchemy persistence for artifacts, observations, claims, evidence edges, challenges, taxonomy mappings, derived metrics, and ledger events.
4. `ledger.py`: canonical SHA-256 chain construction, verification, and evidence-row coverage audit.
5. `epistemics.py`: claim revision, evidence attachment, challenge registration, quality scoring, and lineage traversal.
6. `analytics/`: deterministic formulas only; no LLM calls.
7. `mcp_server.py`: MCP Python SDK v2 `MCPServer` with bounded tools over repositories/analytics. Writes require explicit environment opt-in.
8. `config/sources.json`: reviewed registry for official source families and access mode.
9. `.specify/`, `AGENTS.md`, `RTK.md`: requirements governance plus reasoning/output economy.

## Storage
SQLite is the reference local backend. PostgreSQL is the intended production backend. Raw artifacts live in content-addressed object/filesystem storage; the database stores their hashes and locators.

## Hash chain
`event_hash = SHA256(canonical_json(event_header_with_payload_hash_and_previous_hash))`.
The event payload is independently canonicalized and SHA-256 hashed. Ledger rows and evidence-bearing rows are append-only under SQLite triggers. A coverage audit rejects evidence rows that exist outside the event chain.

## Test strategy
- Canonical serialization/hash determinism.
- Genesis/append/verify/tamper hash-chain cases.
- SQLite update/delete protection.
- Ledger coverage bypass detection.
- Claim revision/challenge preservation and dangling-evidence rejection.
- Taxonomy mapping version/supersession behavior.
- Persisted derived metric input validation and lineage.
- BLS/Census/O*NET/IPEDS connectors with offline fixtures or `httpx.MockTransport`.
- Michigan projection/OEWS parser fixtures with schema variation/failure cases.
- Artifact-store idempotence/content addressing.
- Gap calculation compatibility/missing-data behavior.
- Policy scenario additionality, rate validation, explicit low/base/high assumptions, and JSON-safe MCP output.
- MCP public signatures, bounds, and write-default behavior independent of the optional SDK.
- Source registry, Spec Kit governance, and requirement traceability.
- >=90% statement coverage for package code.

## Expansion
Open tasks cover exact-current-release validation for Michigan XLSX schemas, LAUS/QCEW loaders, official O*NET-SOC/SOC crosswalk ingestion, LODES/PSEO, geospatial hierarchy, signed/Merkle checkpoints, and report templates/visualization. Deterministic policy scenario/sensitivity analysis is implemented; production causal inference remains explicitly out of scope.
