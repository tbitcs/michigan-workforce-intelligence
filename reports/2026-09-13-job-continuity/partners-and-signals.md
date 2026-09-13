# Candidate partners and employer advance signals

This is a **supplemental implementation proposal**, not a committed partnership or operational employer exchange. It accompanies the county/state jobs report and existing Job Continuity/Job Corps analysis.

## Candidate partner roles

| Partner | Verified service basis | Proposed pilot role / limits |
|---|---|---|
| Macomb Regional APEX Accelerator | Government-contracting assistance through Macomb Community College | Help suppliers assess procurement readiness and diversify demand; intake and capacity unconfirmed. [Client intake](https://www.macomb.edu/business/APEX/become-a-client.html) |
| Schoolcraft / Wayne State APEX network | MEDC's FY2025 report lists Schoolcraft service coverage including Oakland and parts of Wayne; Wayne State serves Detroit | Confirm jurisdiction and help eligible firms navigate contracting; contract assistance is not a funded job offer. [Official network description](https://www.michiganbusiness.org/globalassets/documents/reports/legislative-reports/fy-2025-msf-medc-annual-report.pdf) |
| Velocity, Sterling Heights | Provider describes Macomb incubation, acceleration, business coaching and advanced-manufacturing/defense/aerospace focus | Candidate convener and employer-referral/business-growth partner; no pilot grant or agreement confirmed. [Velocity](https://www.mivelocity.com/) |
| Michigan Manufacturing Technology Center / MEP | Manufacturing capability assistance | Assess process/product diversification and paid skill needs before layoffs. [NIST center](https://www.nist.gov/mep/centers/michigan-manufacturing-technology-center-mmtc) |
| Michigan Works!, Rapid Response, colleges, Job Corps, employer/union representatives | Existing employment/training and worker-support roles | Eligibility, casework, worker voice and verified transitions; responsibilities/financing require agreements |

APEX helps companies compete for contracts; it does not guarantee awards. A new bid, award ceiling or announced investment is not equivalent to funded vacancies. Velocity can help convene businesses, but its website's historical impact claims are not causal pilot outcomes. Obtain statements of work and actual receiving demand before counting either as job-continuity capacity.

## Two information layers

**Public evidence layer:** official aggregate indicators, source hashes, observation periods, revisions, geography definitions and published reports. This repository/MCP now provides discovery and bounded trend queries for that layer.

**Confidential operational layer (proposed):** authenticated employer reports of potential reductions and hiring plans, followed by separately consented worker referrals. Do not place commercially sensitive order books or identifiable workers in public report snapshots or GitHub releases. Production multi-employer onboarding, tenant permissions and a worker case-management portal are not implemented by the report-generation pipeline.

A proposed employer signal schema includes verified employer/site ID, county, SOC/version, affected headcount range, confidence, expected date range, skills/equipment, retain/redeploy options, receiving-job demand, wages/hours/benefits offered, signal expiry, contact owner and disclosure permission. Do not include names, SSNs, health information or immigration documents in aggregate signals. Treat an employer forecast as self-reported evidence, with its own source class; never relabel it official government data.

## Preventive matching sequence

1. Employer voluntarily reports possible surplus capacity before a cut, or a funded hiring requirement during expansion. Validate identity, authority, dates and uncertainty; give every signal an expiry and update history.
2. Navigator tests retention/internal paid redeployment before external transfer. Economic indicators provide context, not automatic worker-selection decisions.
3. Compare eligible job families, demonstrated skills, pay/hours, timing and commute. Return explainable candidate routes with remaining barriers; no opaque “layoff risk” score for individuals.
4. Employer hiring remains independent and worker participation voluntary. Obtain consent before identifiable referrals, and no wage-fixing/no-poach promises.
5. Confirm offer, start date and benefits before the outgoing employment ends where feasible. If prevention fails, provide existing benefits/placement support immediately.
6. Record actual payroll and follow-up. Separate advance warnings, interviews, training, placements and additional retained jobs versus comparison outcomes.

Automotive downturn and expansion planning should respond to observed orders, contracts, shifts and employment changes. The suggested 11-year cycle is **not verified**; a calendar rule would miss shorter shocks and structural changes. Build a longer history, preserve revisions and test out-of-sample warning accuracy, false alarms and lead time before deploying forecasting rules. Zero unemployment is an objective, not a guarantee.

## Automation roadmap

The current scripted collectors, shared API quotas, audited database, MCP discovery/trends and timestamped reports form the analytical foundation. A future operational service needs employer identity checks, tenant-scoped authorization, encryption/access auditing, consent/retention rules, integrations to existing case systems, data-sharing agreements and an accountable human queue. Automate expiry checks, reminders and candidate retrieval after those controls exist; do not automatically announce layoffs, contact workers or transfer people.

Use a common data contract and operator-managed scheduled collection rather than every employer independently consuming public APIs with shared keys. Keep public source refresh cadence tied to release schedules and quotas. A release build packages reviewed evidence; it does not silently trigger outreach or claim the operational exchange is live.
