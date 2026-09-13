# ChatGPT desktop connection and readiness

The local MCP server is registered as `michigan_workforce` at `http://127.0.0.1:8000/mcp` in the desktop host's shared MCP configuration. Docker must be running and the app service healthy. No public endpoint, tunnel, cloud deployment or new API key is needed for this local connection.

In ChatGPT desktop, open Settings → Plugins → MCPs and restart the connection if it is not already active. Start a new local conversation and select/use `michigan_workforce`. ChatGPT desktop, Codex CLI and IDE use the same host configuration; ChatGPT web does not read it. If you change MIJOBS_MCP_PORT in .env, update the client URL to match.

Try:

> Use michigan_workforce to list the reviewed source families and audit the ledger. Tell me whether any evidence has actually been ingested.

Or, once evidence is ingested:

> Search Michigan observations for the requested metric, report the source and observation periods, and explain any missing evidence. Do not treat the source registry as data.

## What is complete
Docker Compose runtime, single .env setup, persistent storage, Rich manager, deterministic evidence core, 14 MCP tools, local strict CI, separate-agent network, and optional Kubernetes manifest generation.

## What is not complete
The store verified on 2026-09-13 contains zero evidence-bearing records and zero ledger events. Registry entries describe available source families; they are not downloaded observations. MCP has no general live-source ingestion tool. Current workforce answers require ingesting and validating source data first.

Foundation tasks still open: Census LODES/PSEO plus geographic hierarchy, signed/Merkle checkpoints, the official O*NET-SOC 2019 → SOC 2018 crosswalk, and validation against exact official Michigan release workbooks. The roadmap also includes deeper loaders and reporting features. Do not describe the whole platform as production-complete or capable of every planned analysis.

## Tool behavior
13 tools are marked read-only; `claims_challenge` is marked as a non-destructive, non-idempotent write and still requires server-side MIJOBS_MCP_WRITE_ENABLED opt-in. Server initialization instructions explicitly require evidence searches and tracing and prohibit invented figures when results are empty.

References: [official desktop MCP setup](https://learn.chatgpt.com/docs/extend/mcp), [ChatGPT MCP tool behavior](https://developers.openai.com/api/docs/guides/developer-mode).

## Connection security
Host/Origin validation is enabled. Configure MIJOBS_MCP_ALLOWED_HOSTS and MIJOBS_MCP_ALLOWED_ORIGINS in .env; keep browser origins empty for native desktop use. Default hostnames support loopback and the workforce-mcp Docker alias. See [security validation](security-validation.md) for verified results and remaining OS vulnerabilities.
