# Feature Specification: Docker terminal manager

## User scenarios and testing

### US1 (P1): Start a complete local workspace
An operator with Docker Desktop copies the documented environment example, builds the project, and opens the terminal manager. No host Python or additional database installation is required. Restarting the application preserves evidence.

Acceptance: a fresh build starts the MCP service, reports healthy status, and retains the same ledger and artifacts after a stop/start cycle.

### US2 (P1): Operate from one terminal
The operator sees service status and can start, stop, restart, inspect logs, initialize the database, audit the ledger, list official sources, and run the quality gate from a readable terminal menu. Each action reports success or failure and returns to the menu. Quitting the manager leaves the service running.

Acceptance: all menu actions have equivalent noninteractive commands; invalid choices, a stopped service, interrupted input, and an unavailable Docker engine produce useful bounded results.

### US3 (P2): Configure and maintain the workspace
The operator edits one `.env` file for runtime configuration and credentials. The manager shows which credentials are configured without displaying their contents. Documentation explains how to apply changed configuration and connect an MCP client.

Acceptance: credentials are absent from Git, image layers, and manager output; changed configuration is applied on Start/reconcile; strict local CI passes with at least 90% coverage.

## Functional requirements

- FR-001: Docker must run the application, terminal manager, CLI jobs, and local CI from one Compose definition.
- FR-002: `.env` must be the single editable runtime configuration source; ship `.env.example` with functional local defaults and empty optional credentials.
- FR-003: The Rich TUI must expose status, start/reconcile, stop, restart, bounded logs, database initialization, ledger audit, source registry, and CI actions, plus explicit quit.
- FR-004: Runtime database and immutable artifact files must persist in one named volume through service replacement. No manager action may delete volumes or evidence.
- FR-005: MCP must support the existing stdio interface and a local HTTP service. HTTP must bind to host loopback by default and MCP writes remain disabled by default.
- FR-006: Commands must preserve failure exit codes, avoid shell interpolation, redact configured credentials, and recover from absent/stopped services and unavailable Docker.
- FR-007: Install dependencies reproducibly, include required Spec Kit/RTK tools in CI, repair baseline static failures without relaxing checks, and enforce >=90% package coverage.
- FR-008: Provide a concise root README with setup, configuration, TUI, automation commands, persistence, troubleshooting, and MCP usage.

## Edge cases
Port collision; missing `.env`; daemon unavailable; health timeout; malformed configuration; missing or stopped application; repeated initialization; empty evidence store; malformed container command output; credentials containing punctuation; EOF/Ctrl-C at the menu; CI failure; restarting after configuration changes.

## Key entities
Runtime settings, service status, action result, persisted evidence volume. Evidence schemas and source semantics remain governed by baseline 001.

## Assumptions and scope
Local single-operator Docker Desktop/Linux use, SQLite reference storage, no cloud deployment or automatic live-source ingestion. Existing source adapters and analytics remain available through the Python/MCP interfaces. Docker management access is limited to the explicit manager service. The operator trusts this local manager with Docker access.

## Success criteria
- SC-001: Setup requires only copying `.env.example` and one manager-launch command after Docker is running.
- SC-002: Every action in US2 works interactively and noninteractively and reports an exit status.
- SC-003: Stop/start preserves evidence and audit validity.
- SC-004: Tests, compilation, governance, registry, traceability, lint, and strict types pass; coverage >=90%.

## Clarification review
2026-09-12: reasonable defaults resolve local deployment, SQLite persistence, loopback HTTP, read-only MCP, and Rich menu navigation. No unresolved clarification remains.

## Accepted scope update: agent connectivity
2026-09-12: user chose Compose now and Kubernetes deployment files for later, prioritizing practical operations.

- FR-009: expose stable workforce-mcp DNS on a named Docker network that a separately managed agent can join.
- FR-010: provide an optional Kubernetes manifest generator using the same .env, with ClusterIP service, single-replica persistent storage, health probes, and no automatic cluster deployment. Document image availability and agent connection.
