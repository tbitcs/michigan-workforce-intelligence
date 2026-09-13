# Local setup and live-data verification — 2026-09-13

The local Compose service is healthy. The previous commit `4932c1e8df4dfcdec69c8c6a81f37920dcd1e3a7` matches private origin/main. This follow-up has local source and documentation changes; they are not part of that remote commit.

## Verified

- Canonical Docker CI: 210 tests pass, 90.57% coverage; governance, compilation, 16-source registry, 43 requirement mappings, Ruff and strict Mypy pass. Host RTK is unavailable; container CI provides it.
- SQLite integrity returns `ok`. All 9 raw files exist and their SHA-256 hashes match. All 240 BLS and 8 QWI observation values match their raw source responses.
- 248 observations remain unchanged. No taxonomy mappings are stored. After corrections: 19 claim versions, 10 challenges, 324 audited ledger events/entities; no uncovered evidence rows.
- Ledger head: `157764ed5db574c283a54871fe302e73c5a2878cc89e52a3b523dabbf7e7884f`.
- MCP initialize/tools-list and all 19 read-only tools succeed through both host loopback and the separate Docker CLI container using `workforce-mcp:8000`. All 20 tools are advertised. The write-disabled challenge call and an excessive query limit are rejected. Ledger before/after the read tests is identical.
- The registered MCP connection in this desktop conversation successfully built report context for all 5 corrected supported claims, with valid lineage/audit metadata.
- Rich manager status reports running/healthy. The documented harvest dry-run succeeds without fetching or modifying evidence.

## Corrections

Report generation previously used the unadjusted unemployment rate as a person count and unemployment level as labor force. It now uses exact BLS identifiers, latest observation revisions, matching observation months for annual comparisons, and an observation-period cutoff. It refuses unaudited evidence before generating records.

The corrected report has these sections:

| Section | Value | Observation period |
| --- | --- | --- |
| U.S. seasonally adjusted unemployment rate | 4.1% | August 2026 |
| Same-month annual rate change | −0.2 percentage points | August 2026 vs August 2025 |
| U.S. unemployed persons | 7,031 thousand | August 2026 |
| Civilian labor force | Insufficient data | Correct source series absent |
| Michigan QWI beginning-of-quarter employment | 4,160,099 persons | 2021 Q4 |
| Historical QWI annual change | +187,729 / +4.7% | 2021 Q4 vs 2020 Q4 |

The generated JSON is at `artifacts/reports/insights.json` (local, Git-ignored). Each computed section includes claim and derived-metric IDs. Ten incorrect historical records received append-only challenges; five new report claims were added. No source artifacts or observations were overwritten. Two latest claim keys remain contested (the unsupported old labor-force claim and incorrectly dated September annual-change claim); use effective status when selecting conclusions.

SQLite was backed up before corrections to `/data/backups/before-report-correction-20260913T200806Z.sqlite` in the evidence volume. Existing immutable artifacts remain in that volume; the SQLite backup alone is not a complete portable evidence backup.

The four institution UnitIDs and Oakland's public classification were corrected against official NCES/institution pages linked from the README. Registry metadata is curated context; university outcome data has not been ingested.

## Limits

Michigan QWI coverage ends in 2021, so it cannot establish current Michigan conditions. Recent BLS observations describe the United States. No university completions, retention outcomes or official crosswalks have been loaded. Scenario tools were tested with hypothetical inputs without persisting synthetic evidence; their arithmetic does not validate their assumptions. The README explains limitations including unmatched completions, overlapping demand and unused retention inputs.

The earlier [security scan](security-validation.md) found remaining high-severity OS findings. This data-readiness check is not a new CodeQL or vulnerability-scan certification for the expanded source tree. There are no hosted CI/CD workflows; local CI remains canonical.

Local verification logs: `.venv/security-audit/data-check-ci-final.log`, `live-db-validation.txt`, `live-mcp-validation.json`, and `live-mcp-loopback.json`.
