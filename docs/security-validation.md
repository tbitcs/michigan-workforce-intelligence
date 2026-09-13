# MCP and security validation — 2026-09-13

MCP connectivity, local CI, and local CodeQL pass. Security is **not all-clear**: the final runtime image has 44 high-severity package findings across eight CVEs without a listed Debian fix. No critical findings remain. Scanner findings are not equivalent to proven exploitability; their reachability has not been exhaustively established.

## Verified results

- Invoked all 14 tools through this desktop chat's registered MCP connection. Ten valid read/calculation requests succeeded; three missing-record lookups and the disabled challenge write correctly returned tool errors. Six additional invalid-input requests were rejected. The production evidence store remains unchanged and empty.
- Added 20 real SDK HTTP contract cases using an isolated synthetic database: all tool handlers, populated artifact/claim/trace/report reads, calculations, write denial, and invalid inputs. Added three real HTTP Host/Origin cases. No synthetic evidence was inserted into the running service.
- Full Docker CI: 138 tests passed, 93.79% coverage; compilation, governance, source registry, 43 requirement mappings, Ruff, and strict mypy passed. Host RTK was unavailable; canonical container CI includes RTK and Spec Kit and ran with STRICT_TOOLS=1.
- Live deployment: healthy, non-root UID 10001, port published only on 127.0.0.1:8000. Tools/list returns 14 tools, including 13 read-only annotations. Ledger audit is valid with zero events.
- Legitimate MCP initialization returns 200. An untrusted Origin returns 403; an untrusted Host returns 421.
- CodeQL 2.27.0 official checksummed bundle: python-security-and-quality, 174 queries, 68/68 Python files, zero findings after fixes. This is a local scan, not a GitHub check run.
- pip-audit: no known vulnerabilities in the locked installed Python runtime and development dependencies. Trivy also reports no high/critical Python package findings.
- Bandit: no high/medium findings after the documented container-bind exception. Two low notices for the manager's subprocess import/call were reviewed: fixed Docker argument lists, no shell, bounded timeout, output redaction. These notices remain visible rather than broadly disabling subprocess checks.
- Gitleaks: no leaks in src, config, deploy, or scripts. Scan ran offline with the official digest-pinned image, read-only mounts and dropped capabilities. This does not certify Git history or unscanned files. .env and scan artifacts are Git-ignored.
- git diff --check passes.

## Fixes applied

Explicit SDK DNS-rebinding protection with .env host/origin allowlists replaces the previous permissive HTTP behavior. The listener still binds inside Docker; Compose publishes only loopback. Native MCP clients omit Origin. Hostnames in MIJOBS_MCP_ALLOWED_HOSTS have the configured port appended; MIJOBS_MCP_ALLOWED_ORIGINS is empty by default.

Upgraded the official Python 3.12 base from Debian bookworm to trixie and applied published apt updates. Python and locked application packages remain unchanged. Initial runtime scan: 62 high/critical package findings, including five critical findings. Final scan: 44 high, zero critical. No listed fixes remain for these eight CVEs on Debian 13.7.

CodeQL's rollback-test unreachable-statement finding was resolved by putting the throwing transaction in a helper; commit/rollback assertions remain. An intentionally ignored optional-extension-directory error now has an explanatory comment.

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

## GitHub CI/CD limitation

There are no .github/workflows files; repository policy keeps local CI canonical and prohibits enabling cloud CI without a project decision. Both GitHub CLI and the connected GitHub app returned 404 for tbitcs/michigan-workforce-intelligence. Hosted workflows, CodeQL alerts, and Dependabot alerts could not be verified. Nothing was pushed, published, or enabled remotely.

## Evidence and repeatability

Local evidence is in .venv/security-audit: ci-trixie.log, codeql.sarif, codeql-final.log, codeql.sh, bandit.log, trivy-final.json, and trivy-final.log. CodeQL scanned the final Python source including the new HTTP tests. Scan databases describe vulnerabilities known at scan time; no scan proves absence of all security issues.

Run the canonical gate with `docker compose run --rm --build ci`. CodeQL can be repeated by mounting the evidence directory at /reports and running its codeql.sh in the CI container. It downloads the official checksummed bundle into the disposable container. Vulnerability and secret scans were separate audit tools, not silently added cloud workflows.

The initial network-enabled third-party secret-scan command was rejected by automatic approval review. The successful replacement used the official pinned image offline and mounted only the stated source folders.
