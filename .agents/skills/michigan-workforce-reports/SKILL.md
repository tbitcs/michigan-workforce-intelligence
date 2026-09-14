---
name: michigan-workforce-reports
description: Build Michigan workforce briefs, layoff-prevention plans, skills-transition analyses, funding matches, university outcome reports, and job-retention pilot designs from audited evidence and current official sources. Use for Michigan workforce decisions and reports, not generic hiring or unrelated database administration.
---

# Michigan workforce reports

Translate the user's plain-language question into the smallest useful evidence-backed report. The user need not know MCP tools, SQL, SOC/CIP codes or source names. Infer the mode from their request; use [prompt templates](references/prompts.md) for examples, not mandatory additional questions. Default geography is Michigan and date is today; label both. For a worker or employer case, proceed with known information and ask only for missing constraints that would change the recommendation.

## Evidence workflow

Use the configured `michigan_workforce` MCP service when available. Audit the ledger before treating stored data as trusted, then inspect observations and claim effective statuses. Read [data and tool guide](references/data-guide.md) for exact filters and semantic traps. If the service is unavailable, disclose that limitation and continue the authorized official-source research; do not claim an audit passed or fabricate database results.

Research current primary sources for gaps: Michigan MCDA/LEO/MiLEAP/MEDC, administering Michigan Works! agencies, BLS, Census, NCES, College Scorecard, O*NET, official colleges and credential bodies. Funding/legal eligibility, deadlines, wages and training availability must be reverified for each report. A program's existence is not an open award or remaining balance. Prefer operative approval letters over proposals and dated announcements over stale FAQs. Keep statewide and regional forecast vintages separate.

Each conclusion should identify evidence, observation period, population and material limits. Keep facts, derived calculations, hypotheses and proposed operating rules distinct. Preserve source URLs and, for database evidence, observation/claim/artifact IDs and the ledger head. Do not label online research as ingested evidence unless it was actually stored and audited.

## Recommendations

Every educational institution is a candidate only. Never describe a college or university as represented, participating, committed, or supplying available trainees based on stored outcomes or published programs. Recommend additional candidates using official program evidence, geography, and plausible work-based learning fit. Separately label program existence, current seats, employer commitments, tuition, funding, and consent; the latter remain unverified until confirmed. Legacy `partner_institutions_list` is a candidate lookup, not a partnership registry.

For eligible youth, consider Job Corps as a distinct education/training and transition pathway. Verify current admissions, center/trade operation, individual eligibility and seat availability; historical closure announcements and current website listings alone do not settle availability. Living allowances are not replacement wages. Separate incoming trainees from near-completers, youth outcomes from incumbent jobs saved, and federal program costs from proposed local coordination costs. Do not assume center attendance proves Michigan employment or residence.

Favor voluntary, income-preserving transitions before separation: retention, internal redeployment, paid skill upgrades, then confirmed external placement. Require a receiving employer's credible requisition, wage, hours, benefits and start date before calling a pathway available. Training alone does not create a job. Evaluate the worker's actual pay and total compensation, not just occupation medians. Identify transport, childcare, schedule and accommodation constraints.

For aerospace/defense, separate ordinary production jobs from licensed work, controlled-data access and classified positions. A security clearance is not a short-course credential. Do not assume ITAR requires U.S. citizenship for every role. Check actual role/contract requirements. Keep employer recruiting voluntary and independent; do not propose wage-fixing, no-poach agreements or unnecessary worker-data sharing.

For funding, show eligibility, allowable cost, administrator, application route, current status, employer obligations and unresolved approvals. A funding stack must allocate distinct costs; never charge one cost twice. Verify Work Share/training compatibility rather than promising full income replacement. Label budgets as scenarios and independently recompute totals, denominator definitions and counterfactual effects.

## Output

For county jobs reports, default to Macomb (26099), Oakland (26125), Wayne (26163) and Michigan (26). Discover stored series with `economic_indicators`, then use `economic_trend` with exact geography and metric. Preserve units, seasonal adjustment, periods, margins of error and artifact IDs. Compare interstate earnings and BEA price parities only for compatible years. Label sentiment geography and expectations separately from outcomes. APEX, Velocity and other candidate partners require verified roles and current capacity; never infer job offers from procurement assistance or assume a fixed automotive cycle. A separate local confidential exchange supports aggregate employer signals and consent-attested transitions; public report tools cannot access it. Compare national/state benchmarks only on compatible periods. Treat monthly outlooks as reference paths with disclosed holdout error and stress ranges, not confidence intervals. Evaluate U-3, U-6, participation and hardship separately without double counting; label non-ingested homelessness research and missing sentiment evidence.

Match the requested scope. Full program reports should include an executive brief, demand/risk assessment, occupation-transition and regional matrices, funding matrix, pilot design, budget scenarios, 90-day roadmap, evaluation plan and evidence appendix. Focused queries should not trigger the whole package. Save requested artifacts in the active project, link them, and briefly name important unresolved evidence. Do not email employers, submit grants, enroll workers, change secrets or deploy systems merely because a report recommends doing so.
