# Validation quickstart

1. Start Docker Desktop; copy .env.example to .env.
2. Launch docker compose run --build --rm tui; Start builds the application.
3. Choose Start, Status, Sources, Initialize, Audit, Logs; confirm each result returns to menu.
4. Choose Stop then Start; audit still passes and named volume is retained.
5. Choose CI; require all seven gates and >=90% coverage.
6. Quit; app remains running. Connect MCP client to loopback /mcp and call sources_list and ledger_audit.
7. Test automation with docker compose run --rm -T tui status and failing/unavailable-engine fixtures.

8. Connect a separate container on the michigan-workforce network to http://workforce-mcp:8000/mcp; initialize MCP, list 14 tools and query 16 sources.
9. Render Kubernetes resources from fixture settings and validate all five resources against schemas; do not deploy a cluster.
