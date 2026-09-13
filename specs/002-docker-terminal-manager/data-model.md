# Runtime data model

RuntimeSettings comes from .env through Compose: database URL, artifact path, MCP write flag, port, provider credentials. Credentials are never rendered.
ServiceStatus: service, state, health, published ports. States follow Docker (running/exited/etc); missing rows mean not created.
ActionResult: integer exit code, sanitized text. Nonzero is preserved; timeout and unavailable engine are explicit failures.
Persistent volume: /data/mijobs.db and /data/artifacts. Existing versioned evidence tables, triggers, artifacts and hash-chain rules remain unchanged.
