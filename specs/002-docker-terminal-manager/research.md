# Research decisions

- Docker Compose profiles provide explicit one-off tools without starting them with the app. Source: https://docs.docker.com/compose/how-tos/profiles/
- Docker CLI/Compose inside manager preserves orchestration behavior; Python Docker SDK would duplicate it. Only manager mounts Docker socket. Source: https://docs.docker.com/engine/security/protect-access/
- Named data volumes avoid daemon-host bind path mismatch inside a manager container on Windows. Source: https://docs.docker.com/engine/storage/bind-mounts/
- Rich panels, tables, Prompt and bounded status calls provide a simple terminal interface without another UI framework. Source: https://rich.readthedocs.io/en/stable/live.html
- Installed MCP 2.2.0 MCPServer.run supports transport='streamable-http', host, port, json_response=True, stateless_http=True. Existing run() remains stdio. Confirmed from installed SDK code.
- Docker Desktop can be started with docker desktop start. Source: https://docs.docker.com/desktop/features/desktop-cli/

No unresolved technical unknowns. Docker daemon readiness is a validation prerequisite, not an architectural ambiguity.
