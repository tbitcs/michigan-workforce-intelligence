# Security validation and operating limits

The current canonical Docker gate passes governance, compilation, tests with more than 90% statement coverage, source validation, 73 traced requirements, Ruff and strict mypy on 43 source files. The confidential exchange has 24 contract tests, including official MCP client initialization, discovery and all three read-only tools. Synthetic tests cover tenant boundaries, credentials, consent, offers, capacity and tamper detection. These checks do not establish production readiness.

The public evidence database audit verifies 9,572 ledger events, 55 raw hashes and 3,727 observation versions. Public report snapshots exclude arbitrary raw locators, credentials and confidential employer data. The exchange uses a different encrypted database volume, bearer authentication and an independently verified audit chain; see [exchange limits](employer-exchange.md).

Before public visibility was enabled, offline digest-pinned Gitleaks scanned all six existing commits without findings. A separate check examined 296 Git blobs for the actual configured credentials without printing them. The existing release ZIP contained only report/public evidence assets. Anonymous repository and release-asset download succeeded. GitHub shows only `tbitcs` as administrator, no deploy keys or pending invitations, an active all-branch maintainer ruleset, and enabled secret scanning/push protection.

The fresh CodeQL scan ran 174 security-and-quality queries on 100 Python files with zero findings after restructuring a rollback test. The initial three related control-flow findings were fixed, not suppressed. Live official-SDK checks verified public audit/candidate/outlook tools and all three authenticated exchange tools; the exchange had no employer signals. The browser login and audit action were checked against isolated synthetic data. Audit logs remain in ignored `.venv/security-audit/`. Run `docker compose run --rm --build ci` for the canonical gate. Host RTK is unavailable; the strict CI image provides it.

The runtime dependency scan identified fixable cryptography findings in the initial pilot dependency range. The project now locks cryptography 50.0.1; the post-upgrade Docker CI, existing encrypted-store health and live MCP reads pass. The fresh Trivy scan reports **zero high/critical Python findings, zero critical OS findings and 44 high OS package findings across the eight CVEs below, with no listed fixed versions**. These are known residual risks, not an all-clear security certification.

## Remaining OS findings

| CVE | Affected installed packages |
| --- | --- |
| CVE-2025-69720 | libncursesw6, libtinfo6, ncurses-base, ncurses-bin |
| CVE-2026-16742 | libsystemd0, libudev1 |
| CVE-2026-54369 | libacl1 |
| CVE-2026-76642 | bsdutils, libblkid1, liblastlog2-2, libmount1, libsmartcols1, libuuid1, login, mount, util-linux |
| CVE-2026-78408 | bsdutils, libblkid1, liblastlog2-2, libmount1, libsmartcols1, libuuid1, login, mount, util-linux |
| CVE-2026-78409 | bsdutils, libblkid1, liblastlog2-2, libmount1, libsmartcols1, libuuid1, login, mount, util-linux |
| CVE-2026-78410 | bsdutils, libblkid1, liblastlog2-2, libmount1, libsmartcols1, libuuid1, login, mount, util-linux |
| CVE-2026-9538 | perl-base |

Do not suppress these findings or call this production security approval. Rebuild with refreshed base/packages and rescan when fixes become available; a more minimal runtime would require separate compatibility validation. The unauthenticated local service and its shared Docker network remain for trusted clients only. The TUI has intentional Docker-socket access and must remain an operator-only tool.
