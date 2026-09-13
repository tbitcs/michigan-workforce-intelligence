# Operations contract

TUI commands: status, start, stop, restart, logs, init-db, audit-ledger, sources, ci, config. No arguments opens the menu; q or EOF exits without stopping app. Noninteractive failures return nonzero. Start applies configuration with Compose up --build --wait; restart starts/reconciles then restarts. Logs are limited to 100 lines. CI is an isolated one-off container. App lifecycle is scoped to the configured Compose project. No down -v, prune, or delete command exists.

One root .env configures COMPOSE_PROJECT_NAME, MIJOBS_MCP_PORT, MIJOBS_DATABASE_URL, MIJOBS_ARTIFACT_ROOT, MIJOBS_MCP_WRITE_ENABLED, BLS_API_KEY, CENSUS_API_KEY, ONET_USERNAME, ONET_PASSWORD. Defaults retain SQLite and artifacts under /data. Credential display is only configured/not set.

HTTP endpoint: http://127.0.0.1:<MIJOBS_MCP_PORT>/mcp. Existing MCP tools and stdio interface retain their public contracts. No new evidence schema.
