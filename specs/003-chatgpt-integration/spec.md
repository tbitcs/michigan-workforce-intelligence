# ChatGPT MCP integration

## Problem and user stories
The operator wants ChatGPT to use the local workforce MCP service and an honest assessment of platform readiness. ChatGPT must distinguish the source registry from ingested evidence, and reads from writes.

## Requirements
- FR-001: Advertise explicit read-only annotations for 13 read/calculation tools and write annotations for claims_challenge.
- FR-002: Server instructions state data/coverage limits, source/evidence distinction, evidence tracing, deterministic assumptions and write opt-in.
- FR-003: Register the supported connection for the user's selected ChatGPT surface and verify discovered tools; report account-dependent blockers accurately.
- FR-004: Document that Docker operations are complete but ingestion depth, crosswalk/release validation and signed checkpoints remain unfinished. An empty evidence store cannot support current workforce findings.

## Assumptions and success criteria
The existing local HTTP service remains private. Desktop may use local host configuration; ChatGPT web requires a supported tunnel or HTTPS endpoint plus account setup. No public exposure is inferred. Tests verify truthful instructions and tool metadata; full CI must pass. Account registration is not claimed successful without verification.
