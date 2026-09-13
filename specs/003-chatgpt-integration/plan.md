# Plan: ChatGPT integration

## Constitution check
PASS: preserve evidence lineage and writes opt-in; report missing evidence. No source or database mutation is required.

## Architecture and research
Keep the existing Docker MCP service. Add SDK-supported annotations and initialization instructions; update FakeMCPServer fixture and assert metadata. Current official docs confirm local ChatGPT desktop shares Codex host MCP configuration, whereas ChatGPT web requires remote plugin tools (https://learn.chatgpt.com/docs/extend/mcp). ChatGPT respects readOnlyHint (https://developers.openai.com/api/docs/guides/developer-mode). Secure MCP Tunnel supports private HTTP forwarding but needs an associated workspace, tunnel ID, and runtime API key (https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

## Interfaces and data
No new tools, models, or dependencies. Preserve all 14 tool signatures. Existing .env still configures Docker runtime. Account/client transport configuration is client-side registration, not duplicate application settings.

## Validation
Run focused metadata tests, full Docker CI, restart application, initialize MCP and inspect tools. Configure chosen desktop or web client through supported controls. Never report registry rows as ingested evidence.

## Security validation follow-up
Explicit SDK Host/Origin allowlists prevent DNS rebinding while retaining Docker aliases. Configure through .env. Verify trusted clients succeed and untrusted Host/Origin requests fail, all 14 tools respond, full CI passes, and local CodeQL and dependency scans are reviewed. No cloud workflow activation.

Base-image decision: upgrade Python 3.12 from Debian bookworm to trixie and apply published apt updates. The candidate scan shows fixes for critical Perl findings and no old SQLite critical finding; retain Python version and locked application dependencies. Rebuild runtime/CI and rescan before concluding.

## Live data verification follow-up
Validate stored artifact hashes and raw values independently of claim accuracy. Correct CPS report series semantics and actual-period YoY pairing, use latest observation versions, and reject invalid ledgers. Preserve raw evidence; append challenges to misinterpreted claims. Document actual stored coverage, missing institution/crosswalk data, and query/report examples. Deploy current tools only after Docker CI.
