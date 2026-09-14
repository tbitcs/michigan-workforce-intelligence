# Confidential employer exchange

FR-001: Deploy a separate loopback-only Docker service and persistent volume for confidential employer records; never mount this volume in public MCP/report jobs.
FR-002: Authenticate every protected request with a strong expiring bearer token. Enforce revocation and tenant isolation. Operator onboarding verifies employer identity outside the system.
FR-003: Encrypt business payloads at rest and maintain a transactional hash-chained access/change audit without recording credentials or worker identities.
FR-004: Support employer-owned surplus/hiring signals, explicit network-sharing consent, expiry and deterministic explainable matching by occupation, skills, geography, dates and wages.
FR-005: Support voluntary employer-to-employer transition requests, attested worker consent, receiving-employer offer confirmation, capacity checks and reported start outcomes. Do not label reported starts as causal jobs saved.
FR-006: Provide a browser console and portable Docker management/setup scripts, keep generated keys in .env, preserve existing API keys and fail closed on missing configuration.
FR-007: Test authorization boundaries, malformed input, encryption, tampering, workflow transitions and live deployment; run canonical local CI before commit.

Scope: local operator-managed pilot, no public Internet deployment, no real worker names/contact/health/immigration/claimant records, no automatic outreach or placements. Public hosting and real individual case records require a separate deployment/governance review. The user's deployment request authorizes implementation and local operation, not invented employer accounts or enrolling people.
