# Michigan Workforce Intelligence

A local workforce evidence platform for Michigan: official source adapters, versioned observations and claims, immutable artifacts, an audited hash-chain ledger, deterministic analytics, and MCP tools.

## Start here

Install and start **Docker Desktop** (Linux containers) or Docker Engine with Compose. No host Python, database, or build tools are required.

From this project folder, copy the settings once:

```powershell
Copy-Item .env.example .env
```

On Linux/macOS, use `cp .env.example .env`. Then open the manager:

```sh
docker compose run --build --rm tui
```

Choose **1 — Start / apply configuration**. The first run builds the application and creates its data volume. Later runs reuse cached layers. Choose **q** to leave the manager; the service keeps running. Reopen with the same command.

## Terminal manager

The Rich console shows service state and health, with these actions:

| Key | Action |
| --- | --- |
| 1 | Build/start service and apply `.env` changes |
| 2 | Stop service, keeping all data |
| 3 | Reconcile and restart service |
| 4 | Show last 100 log lines |
| 5 | Initialize database (safe to repeat) |
| 6 | Audit evidence coverage and ledger integrity |
| 7 | List reviewed official source families |
| 8 | Build and run strict CI in an isolated container |
| 9 | Show credential configuration status without values |
| r | Refresh service status |
| q | Exit manager |

The manager is a trusted local administration tool: it alone mounts the Docker socket to operate this project's containers. The application runs as an unprivileged user and has no Docker socket access. There are no evidence-delete or volume-delete menu actions.

## Configuration

**Edit only `.env`** for deployment settings. It is ignored by Git and excluded from image builds. `.env.example` documents every variable.

| Variable | Default / purpose |
| --- | --- |
| `COMPOSE_PROJECT_NAME` | `michigan-workforce-intelligence`; scopes containers and the data volume |
| `MIJOBS_NETWORK_NAME` | `michigan-workforce`; shared network for agent containers |
| `MIJOBS_MCP_PORT` | `8000`; host and container HTTP port |
| `MIJOBS_DATABASE_URL` | `sqlite:////data/mijobs.db` |
| `MIJOBS_ARTIFACT_ROOT` | `/data/artifacts` |
| `MIJOBS_MCP_WRITE_ENABLED` | `false`; opt in explicitly to MCP evidence writes |
| `BLS_API_KEY`, `CENSUS_API_KEY` | Optional official API credentials |
| `ONET_USERNAME`, `ONET_PASSWORD` | Optional O*NET credentials |

Single-quote secrets containing `$` or `#`. After editing `.env`, reopen the manager and choose **Start / apply configuration**. Keep the default `/data` paths for persistent SQLite/artifacts. Changing the project name selects a different volume; it does not migrate the old data. No sources are downloaded automatically.

## ChatGPT desktop

Use the registered `michigan_workforce` MCP server in local ChatGPT desktop conversations. See [connection instructions and readiness limits](docs/chatgpt.md). The operational setup is complete, but the initial evidence store is empty and broader data-ingestion work remains.

## Agent container connection

Keep your agent in its own container and attach it to the shared `michigan-workforce` Docker network. Point its MCP client at **`http://workforce-mcp:8000/mcp`**. The network name is configured by `MIJOBS_NETWORK_NAME` in `.env`. The agent does not need database or Docker socket access.

See [agent wiring and optional Kubernetes deployment](deploy/README.md). Compose is the supported local setup; Kubernetes manifests can be generated later from the same `.env`.

## MCP

HTTP endpoint: **`http://127.0.0.1:8000/mcp`** (or the configured port). The service uses stateless Streamable HTTP and is published only on host loopback. Configure an MCP client that supports this transport with that URL. A protocol-aware Docker probe checks readiness; opening the endpoint in a browser is not a health check.

For stdio clients, set this project as the working directory and use:

```sh
docker compose run --rm -T --entrypoint mijobs-mcp cli
```

The default CLI and stdio MCP share the same persistent evidence store as HTTP. Existing MCP tools list sources, search observations/claims/mappings, trace evidence, audit the ledger, calculate compatible gaps, and evaluate explicit policy assumptions. Write tools remain opt-in. See [MCP contracts](specs/001-michigan-workforce-intelligence/contracts/mcp-tools.md).

## Commands and quality checks

Every menu action also works without an interactive terminal:

```sh
docker compose run --rm -T tui status
docker compose run --rm -T tui start
docker compose run --rm -T tui audit-ledger
docker compose run --rm -T tui ci
```

Direct equivalents:

```sh
docker compose up --build -d --wait app
docker compose run --build --rm -T cli sources
docker compose run --build --rm -T cli audit-ledger
docker compose run --build --rm -T ci
docker compose stop app
```

CI enforces governance, compilation, unit tests with **at least 90% coverage**, source registry validation, spec traceability, Ruff, and strict Mypy. Runtime and CI dependencies are resolved in `uv.lock`; Docker installs with `--frozen`. CI includes official Rust Token Killer and Spec Kit. CI uses isolated temporary storage and receives no production credentials or evidence volume.

The optional Makefile wraps these Docker commands. `make ci-local` is the internal container gate; host development can use a Python virtual environment but is not needed for operations.

## Persistence and troubleshooting

The single Compose `evidence` volume holds the database and content-addressed artifacts. Stop, restart, rebuild, and manager exit preserve it. Back up the whole volume with the app stopped to keep SQLite and artifact files together. Never use `docker compose down -v` unless you intend to erase the local evidence store.

- **Docker unavailable:** start Docker Desktop and wait for `docker info` to succeed. The manager cannot repair the host engine from inside a container.
- **Desktop `sailor-ingest.sock` startup error:** first wait and recheck `docker info`; startup can recover. If it persists, fully quit/restart Docker Desktop. Do not factory-reset or delete WSL data as a routine fix.
- **Port busy:** change `MIJOBS_MCP_PORT` in `.env`, reopen the manager, and choose Start.
- **Service unhealthy:** inspect Logs. Check `.env` for valid paths and a port from 1–65535.
- **Changed code or dependencies:** reopen with `--build`; Start and CI build their current targets from the mounted source.
- **Timed-out action:** Docker may still be completing it; inspect Status and Logs before retrying.

## Project map

- `src/mijobs/`: sources, ingestion, provenance, analytics, CLI/MCP, and terminal manager.
- `config/sources.json`: reviewed registry of 16 official source families.
- `tests/`: offline evidence, adapter, runtime, and management tests.
- `specs/001-michigan-workforce-intelligence/`: foundation requirements and evidence contracts.
- `specs/002-docker-terminal-manager/`: implementation plan, tasks, and validation for this setup.
- `.specify/`, `.agents/skills/`, `AGENTS.md`, `RTK.md`: Spec Kit/Codex governance.

See [source methodology](docs/source-methodology.md) and [roadmap](docs/roadmap.md). Model-generated prose is never source evidence.
