# Local MCP connections

The existing desktop connection is named `michigan_workforce` and uses `http://127.0.0.1:8000/mcp`. Start the Docker `app` service and verify its protocol health before using it. A browser GET is not an MCP initialization request. The native client uses Streamable HTTP; a separate agent container on the shared network uses `http://workforce-mcp:8000/mcp`.

Ask: “Use michigan_workforce to audit the ledger, show compatible county/state trends, and explain missing evidence.” The public service exposes 22 tools, with writes disabled by default. It provides evidence reads, lineage, candidate institution context, deterministic calculations and monthly reference outlooks. It does not harvest arbitrary live websites or access confidential employer records. Refresh the client connection after server updates if it has cached schemas.

The [reporting skill](../.agents/skills/michigan-workforce-reports/SKILL.md) translates ordinary questions into evidence queries and current-source research. A client needs its own supported MCP configuration; this local configuration is not a ChatGPT web deployment or a public hosted connector. No tunnel is required for the local desktop setup.

The separate local employer exchange offers an authenticated MCP endpoint on `http://127.0.0.1:8085/mcp`. Configure it separately with the intended employer's bearer credential through the client's secure credential configuration. Its three tools read scoped signals, candidate matches and transitions. Do not put credentials in prompts, repository files or public report assets. It is not automatically registered by adding the public evidence connection.

Host/Origin validation remains enabled. Keep loopback publishing and only the intended native/Docker client hosts. See [README](../README.md), [exchange operations](employer-exchange.md), and [deployment guide](../deploy/README.md). Current evidence coverage is in the scripted snapshot rather than a fixed tool-count claim of completeness.

The sibling `manufacturing-inference-advisor` repository can register a Docker MCP Gateway profile named `manufacturing-intelligence`. Its portable setup script builds this repository's `mcp-stdio` Docker target, mounts the existing evidence volume read-only, and combines the 22 workforce tools with ten inference-planning tools. Its verification command initializes a real MCP client through the gateway and calls one tool on each server.
