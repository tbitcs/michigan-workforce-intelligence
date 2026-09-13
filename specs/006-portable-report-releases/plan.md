# Plan

Use standard-library Python orchestration on the host and a separately built Docker reports target for analysis, PDF rendering and packaging. Add locked optional report dependencies without changing the MCP runtime. Reanalysis reads a read-only evidence volume, never initializes or harvests it. Commit only a minimized aggregate analysis snapshot; release builds do not access the live database.

Generate two PDFs from reviewed Markdown plus a generated data appendix. Render every page for QA; package only allowlisted PDFs/JSON/Markdown with hashes and UTC timestamp version `YYYY.MM.DD.HHMMSSZ`. GitHub workflow_dispatch runs portable launcher tests on Linux/Windows/macOS, builds in Linux Docker, then publishes immutable timestamped assets using repository token contents:write only in the publishing job. Pin actions to full SHAs. A portable script wraps workflow dispatch and release inspection; no secret-bearing output.

No additional question is needed: timestamp timezone defaults to UTC; application semantic version remains independent from report release version. A report rebuild does not imply refreshed research. Snapshot observation dates and evidence review dates remain visible.
