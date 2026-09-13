# Implementation Plan: Docker terminal manager

## Context
Deliver user-requested Docker-only operations, one `.env`, and a Rich terminal manager. Preserve the baseline evidence model and make the existing strict gate pass.

## Constitution check
All ten principles reviewed: PASS. No new source evidence or semantics, no destructive management commands, unchanged append-only storage and write opt-in. Local quality gate remains required.

## Architecture
One multi-stage Dockerfile builds app, CI, and manager targets using a checked-in uv.lock. Runtime uses Python 3.12 and the existing package plus Rich; CI adds locked dev tools, Spec Kit, and official checksum-verified RTK. Manager adds Docker CLI/Compose and uses the same application code. Compose defines app, cli, ci, and tui services. Only app starts by default; others use a tools profile.

The TUI runs Compose through explicit argv lists with timeout and output redaction. It operates only this Compose project. The project source mounts read-only into the manager at /workspace, while data uses a named volume to avoid Docker Desktop nested bind-path problems. The host launch builds the manager; Start and CI build their images from the read-only mounted source context when needed. `.env` is read by Compose from /workspace, never copied into images. Manager credentials are loaded only for redaction/configuration summaries. Status and logs are bounded; EOF exits; interrupt returns to the menu. No volume deletion action exists.

MCP serves stateless streamable HTTP inside the container, host publishing defaults to 127.0.0.1. Existing stdio entry point stays compatible. HTTP health checks perform MCP initialization rather than depending on a browser GET. DB/artifacts share /data. Runtime runs unprivileged; only manager gets the Docker socket and root access required to manage local containers.

## Data model
No evidence schema migration. Runtime settings include DB URL, artifact root, MCP writes, HTTP port and optional provider credentials. ServiceStatus is projected from Compose ps; ActionResult contains exit code and sanitized output.

## Interfaces
`docker compose run --build --rm tui` opens the menu. Noninteractive `... tui status|start|stop|restart|logs|init-db|audit-ledger|sources|ci|config` mirrors each action. CLI service runs `mijobs`, defaults to help; explicit entrypoint supports stdio MCP. Contract details live in contracts/operations.md.

## Test strategy
Test actual operation argv, return codes, failure handling, secret redaction, configuration validation, HTTP entrypoint and health protocol; capture Rich output with a StringIO console. Run unchanged ledger/source fixtures and strict coverage >=90%. Run full Linux container CI and real lifecycle/MCP smoke, including volume survival and TUI quit.

## Migration/rollout
Initialize a new named volume, retain local legacy DB unmodified. Lock dependencies, build images, reconcile app, audit empty store, run CI, exercise stop/start and JSON-RPC. Generated Codex integration stays consolidated in existing locations. No GitHub publication.

## Risks and mitigations
Docker must be available; surface actual blocker if daemon cannot start. Port collisions produce Compose errors. Docker socket is trusted operator access and mounted only in tui. Long commands timeout with actionable retry; daemon-side builds may continue. Env changes require exiting/reopening manager and Start/reconcile. Never print raw Compose config or database credentials. Lock/tool versions constrain dependency drift.

## Accepted extension: separate agents
Compose default network gains an .env-controlled stable name and workforce-mcp service alias. Separate agent projects attach as external network consumers. deploy/render_kubernetes.py emits a Kubernetes List from Compose-injected runtime environment: Namespace, Secret, PVC, Recreate single-replica Deployment, and internal ClusterIP Service. The same runtime image is used; the manager is not deployed in Kubernetes. Validate renderer against defaults, custom ports/images, missing secrets, and invalid values. No cluster activation or deployment is authorized or required.
