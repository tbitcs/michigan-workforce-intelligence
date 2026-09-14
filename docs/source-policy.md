# Source access, attribution and API policy

Reviewed September 13, 2026. Registry membership is discovery, not an enabled API or proof of loaded data. `implementation_status`, `api_policy`, `license_url` (a policy lookup pointer, not a license grant) and `attribution` travel through MCP source discovery. The default for a new source is catalog-only. Report collection is explicit; rebuilding PDFs is offline and does not consume API quota.

| Implemented access | Official rule / project enforcement |
|---|---|
| BLS v2 | Registered requests: up to 50 series/20 inclusive years; unregistered: 25 series/10 inclusive years. Project quotas are conservatively 450 registered or 20 unregistered per rolling 24 hours, with 1.1-second spacing. Inclusive-year off-by-one corrected. [BLS limits](https://www.bls.gov/developers/api_faqs.htm) |
| Census QWI/ACS | API key required under current guidance; maximum 50 requested variables enforced for QWI and below that in ACS collectors. Project budget 450 requests per rolling day, 1.1-second spacing; a local budget is not a claim about the provider's keyed entitlement. Reserved QWI parameters cannot be overridden by filters. [Census API guide](https://www.census.gov/data/developers/guidance/api-user-guide.html) |
| Scorecard / api.data.gov | Project budgets: DEMO_KEY 25/hour and 45/day; personal key 900/hour. These are below published default/demo limits; provider-specific lower quotas require policy review; server cooldowns take precedence. [api.data.gov manual](https://api.data.gov/docs/developer-manual/) |
| O*NET bulk downloads, NCES/IPEDS, BEA bulk files and official publications | Two-second spacing and 200-request/day local host budget; these are project courtesy limits, not claimed official API entitlements. O*NET authenticated Web Services are explicitly disabled pending service-specific integration. |
| Other registered economic APIs | Catalog only; no unreviewed BEA/HUD/EIA/FRED/Web Services API calls or invented credentials. Bulk BEA data uses its public download route, not the keyed API. |

Default connector clients use `sources/http_policy.py`. Its SQLite quota ledger is separate from the evidence ledger and shared in the Docker evidence volume (`MIJOBS_HTTP_STATE`, default `/data/http-policy.sqlite3`). It persists only bucket names/timestamps, not keys or request URLs. Processes sharing this file share budgets. Other machines/applications using the same credential/IP can consume provider quota outside this ledger; centralize collection for a shared deployment. Tests may inject isolated mock HTTP clients; production callers must use the governed defaults or an equally constrained injected client.

HTTP 429/503 records a cooldown honoring `Retry-After` seconds/date with a minimum 60 seconds; there is no automatic retry storm. Quota exhaustion fails before dispatch. Authentication failures and schema errors stop collection. No key rotation, account/IP sharding or bypass of provider blocks is permitted. If a provider communicates a lower limit, configure/review the policy before more collection. Access rules can change; this dated review is not a perpetual compliance guarantee.

Requests are batched where supported. Immutable source files support offline repeat analysis; PDF release builds never fetch live APIs. Explicit recollection may append source/observation revisions and consumes quota; it is not the default report command. Downloads preserve original hashes and retrieval times. Analysts verify units, survey identity and geographic catalog metadata before interpretation.

See [third-party notices](../THIRD_PARTY_NOTICES.md). Do not assume every government-hosted publication is wholly public domain. Retain dataset-specific attribution, suppression rules and source licenses; do not upload private employer/worker records in report assets. Additional source activation requires a reviewed endpoint, credentials if needed, quota/retry semantics, permission to reuse the selected content, normalization/lineage tests and explicit missing-data handling.

## Project licensing boundary

Original software is MIT; original reports, documentation and charts are CC BY 4.0. Neither grant replaces provider API or redistribution terms. Preserve per-source credits and restrictions in exported evidence, and do not label all source records CC BY merely because the report is CC BY. See [license scope](../LICENSING.md).
