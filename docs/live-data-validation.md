# Live data validation

The current public report audit is recorded in [data reanalysis](../reports/2026-09-13-job-continuity/data-reanalysis.md) and its JSON snapshot. It verifies all 55 artifact hashes, the 9,572-event ledger, evidence coverage and 3,727 observation versions. Thirty-three configured monthly BLS series are available. Observation periods, units, adjustment and latest revisions remain explicit; totals do not imply every source catalog entry has been ingested.

IPEDS and Scorecard outcome records were reused without another university harvest. All institutions are candidates only. Historical QWI, current monthly data, academic awards, earnings cohorts, annual prices and quarterly employer statistics must not be pooled as if they measure the same population or period.

Analysis uses the evidence volume read-only and produces an allowlisted aggregate snapshot. It does not export the live SQLite database or the separate confidential exchange. Official-source homelessness research remains external to the ledger; the attempted HUD bulk retrieval returned no usable artifact. Missing evidence is not zero.

Use the [README query guide](../README.md#evidence-and-queries) to discover metrics and periods, and the [security validation](security-validation.md) for test scope. Git history preserves earlier audit baselines; this page describes current evidence rather than stacking obsolete totals.

## Published report verification

Release [reports-2026.09.14.004029Z](https://github.com/AXIOVEX/michigan-workforce-intelligence/releases/tag/reports-2026.09.14.004029Z) was built from commit `1b29abe`. It contains a 9-page executive brief, 61-page jobs/economic report and 40-page supplemental continuity report, with 41 charts. All pages were rendered; revised covers and legal notices were visually checked against the previously reviewed analytical pages. Six public release assets were downloaded without authentication and their checksums verified. The ZIP includes MIT, CC BY 4.0, Spec Kit and font license texts, scope and source notices. No live database or private exchange records are packaged.

The older release reports-2026.09.13.231357Z was deleted before replacement; its Git tag/history was retained. Workflow [34793451385](https://github.com/AXIOVEX/michigan-workforce-intelligence/actions/runs/34793451385) passed Linux, Windows and macOS launcher tests, Docker report construction and publication. GitHub issued informational Node 20 action-runtime deprecation annotations (forced Node 24 execution); these were not job failures. Application Docker CI passed with 91.55% coverage, lint, type checks, source registry and traceability checks. Existing container vulnerability limitations remain documented in security-validation.md.

The repository is public, GitHub identifies the software license as MIT, and the access audit found only tbitcs with write access, no deploy keys or pending invitations, and an active maintainer-only branch ruleset. Original report content is CC BY 4.0; source material keeps provider terms.
