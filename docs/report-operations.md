# Report operations

The primary publication covers jobs and economic trends in Macomb, Oakland, Wayne and Michigan. Job continuity, Job Corps and candidate partner proposals are supplemental publications. The analytical database is operational; a multi-employer confidential exchange is a proposed future service.

Use Python 3.12+ and Docker on Windows, Linux or macOS. These host commands use only the Python standard library; document dependencies run in Docker. Keep credentials in `.env` and preserve the Compose evidence volume.

```sh
python scripts/reports.py build-image
python scripts/reports.py collect
python scripts/reports.py analyze
python scripts/reports.py build
```

`collect` refreshes the configured BLS monthly series and writes audited evidence. Additional reviewed collectors are `collect_qcew.py` (2026 Q1), `collect_reference_data.py` (BEA current vintage), and `collect_comparisons.py` (2024 ACS/BEA plus authorized O*NET graphic). They are intentionally vintage-specific; review source release dates and update their periods before a future refresh. Run them through the report launcher collection commands. Do not mistake the dated report for automatically current information.

Analysis opens the evidence volume read-only, checks the ledger and artifact hashes and reruns university summaries without reloading outcomes. PDF builds use reviewed snapshots offline; they never upload the database or call paid APIs. Outputs are under `output/pdf/YYYY.MM.DD.HHMMSSZ`, with PDFs, charts, public snapshots, manifest, checksums and ZIP. Every page is rendered under `tmp/pdfs/` for visual review. Review all pages and claims before release.

The GitHub workflow is manually dispatched from committed, reviewed source. It checks the portable launcher on three operating systems and builds the Docker reports on Linux. This validates portable orchestration, not every Docker Desktop version. It publishes immutable timestamp tags and only allowlisted report artifacts. No secrets or live volumes are provided to the workflow. Use `python scripts/reports.py release` after a clean commit and push, then inspect the workflow result and release checksums.

For API limits, attribution and redistribution rules, see [source policy](source-policy.md) and [third-party notices](../THIRD_PARTY_NOTICES.md). Source-specific notices apply independently of any license for original project code.
