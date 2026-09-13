# Pilot budget, economics and implementation

All figures are **planning assumptions** for a 12-month, 200-worker pilot, not grant commitments, quotes or predicted effects. Participants are incumbent workers with validated risk or workers recently displaced. Students/inbound participants are separate tracks; do not add overlapping participants to the core denominator.

## Cost envelope and financing

| Cash item | Basis | Amount |
|---|---|---:|
| Training | 200 × $2,500 blended allowance; not everyone receives the same course | $500,000 |
| Staff | Four full-time equivalents × $100,000 loaded cost | $400,000 |
| Transportation/childcare/equipment supports | 200 × $800 allowance, allocated by need | $160,000 |
| Flexible continuity support | Up to 80 × $1,500; eligibility/benefit effects must be approved | $120,000 |
| Data, legal and independent evaluation | Contract allowance | $100,000 |
| Subtotal | Sum above | $1,280,000 |
| Contingency | 10% of subtotal | $128,000 |
| **Core cash requirement** | Before any grant receipts | **$1,408,000** |
| Employer-paid training time | 200 × 80 hours × $30 loaded/hour | $480,000 |
| **Total economic resource envelope** | Cash plus training time | **$1,888,000** |

Ordinary productive wages and UI payments are excluded from this intervention budget. Training time is treated as an employer resource cost without claiming both grant and employer reimbursement for the same hours. The $2,500 allowance is a blended planning figure: some pathways cost substantially more, others require only mentoring. If actual quotes exceed the allowance, secure added financing or reduce enrollment; do not substitute an inadequate course.

**Proposal:** a fiscal sponsor assembles employer, public and philanthropic commitments. **Committed grant revenue assumed: $0.** Use [the funding matrix](funding.md) to seek eligible reimbursements. Report gross program costs and each payer's contribution separately. Do not present a grant as an economic benefit that cancels resource costs.

An optional **40-student module** adds 240 paid hours each at an assumed $22/hour ($211,200 wages), 20% payroll load ($42,240) and $40,000 coordination/support: **$293,440 additional**, excluded from the core scenarios. It requires separate employer placements and financing. Inbound relocation assistance is not budgeted; price it after verified jobs and households are identified. The four core FTE cannot silently absorb unlimited additional tracks.

## Low/base/high scenarios

Use the same 200 participants and cash budget in each case to show performance sensitivity. Assume 90 would achieve six-month sustained employment without the intervention, and average unemployment without intervention would be 45 days per participant over the six-month window. Both counterfactuals are **unmeasured assumptions**, not findings. Actual evaluation must estimate them.

| Assumption/result | Low | Base | High |
|---|---:|---:|---:|
| Sustained employed at six months | 110 | 140 | 170 |
| Additional sustained outcomes versus assumed 90 | 20 | 50 | 80 |
| Mean unemployment days with program | 30 | 18 | 8 |
| Aggregate days avoided: 200 × (45 − days) | 3,000 | 5,400 | 7,400 |
| Workers with assumed hourly pay improvement | 20 | 50 | 80 |
| Assumed hourly increase for those workers | $2 | $3 | $4 |
| Annualized gross increase at 2,080 hours | $83,200 | $312,000 | $665,600 |
| Cash cost per observed sustained outcome | $12,800 | $10,057 | $8,282 |
| Cash cost per additional sustained outcome | $70,400 | $28,160 | $17,600 |
| Economic cost per additional sustained outcome | $94,400 | $37,760 | $23,600 |
| Cash cost per unemployment day avoided | $469.33 | $260.74 | $190.27 |

Sustained outcomes may include original jobs, internal moves and new employers; the scenario does not establish how many original jobs were saved. Wage-gain workers are a subset, not extra participants. Annualized wage increases are neither guaranteed nor realized first-year benefits; no inflation adjustment is applied. Days avoided and annualized wage gains must not be monetized and added without resolving overlap, UI offsets, taxes, benefits and actual hours.

The base case requires an estimated 25-percentage-point increase in sustained employment (140/200 versus 90/200). That is a demanding assumption, not a reasonable expectation established by the database. If the true counterfactual were 130 sustained outcomes, the same 140 outcomes would imply only ten additional outcomes and a cash cost of $140,800 each. If no additional outcome occurs, cost per additional outcome is undefined and the program has not demonstrated effectiveness on that measure.

Do not use these scenarios to claim statewide fiscal savings or a positive return on investment. Collect actual wages, benefits, unemployment intervals, program expenditures and comparable controls first. The [report's evaluation section](report.md#7-economics-and-evaluation) defines outcomes.

Recompute the JSON using the existing Docker runtime (no additional service or package):

```powershell
docker compose run --rm -T --volume "${PWD}:/workspace" --entrypoint python cli /workspace/reports/2026-09-13-job-continuity/build_scenarios.py
```

## Staffing and responsibilities

The [Job Corps revision](job-corps.md) adds a conditional 30-person youth transition module, 0.5 FTE and $93,500 incremental local cash. Together with the student option, total specified local cash becomes $1,794,940; including core employer training time gives $2,274,940, excluding federal center operating costs. Its youth scenarios and longer follow-up are separate from the core table above. During days 1–30 confirm center/arrival status; days 31–60 plan near-completer transitions; days 61–90 verify actual offers/starts and separately report new trainees' progress.

**Proposal:** one program/employer lead, two navigators and one fiscal/data coordinator constitute the four FTE. Independent evaluation/legal expertise comes from the contract allowance. Local agencies determine program eligibility; they are not assumed to supply free unlimited casework. Seek a written service agreement and budget any additional work before assigning it.

| Actor | Accountable work | Confirmation before launch |
|---|---|---|
| Fiscal sponsor / steering group | Sign agreements, hold funds, approve risk and outcome rules | Sponsor named; cash commitments; worker representation |
| Program/employer lead | Recruit 8–12 employer types across sending/receiving roles; verify jobs and risks | Signed employer participation terms; requisition owners |
| Two navigators | Consent, task assessment, support plan, referrals and follow-up | Caseload/time plan; accessibility and grievance process |
| Fiscal/data coordinator | Payer approvals, invoice controls, case status and evidence quality | Cost-allocation rules and access controls |
| Local Michigan Works!/Rapid Response/UIA | Determine respective eligibility and administer approved services | Named contacts and service boundaries |
| Employers and worker/union representatives | Paid training, safe work, independent hiring, benefit/start-date clarity | Named supervisors, release time and written worker terms |
| Training providers | Assess prerequisite skills, quote/deliver training, document competence | Seat dates, accessibility, exams and cancellation terms |
| Independent evaluator | Predefine comparison, missingness rules and outcome analysis | Evaluation protocol and lawful data access |

Proposed participating employer types: automotive/supplier plants with redeployment needs; machinery/precision production firms; dual-use aerospace/defense suppliers; engineering and testing businesses; and healthcare, construction/logistics or service employers with validated receiving roles. No named employer has agreed to participate.

## 90-day launch roadmap

Day 1 is the sponsor's authorized kickoff, not automatically this report's date. Do not wait for the entire pilot to launch to refer an urgent worker to existing services.

| Window | Owner and action | Required output / release gate |
|---|---|---|
| Days 1–15 | Sponsor/lead: select local partners, recruit employer cohort, engage worker representatives | Signed governance, privacy and independent-hiring terms; initial cash authority |
| Days 16–30 | Lead/navigators: verify risk, jobs, skills and barriers; fiscal lead checks programs | First 30–50 potentially eligible cases; employer-approved receiving/internal roles; written provider quotes |
| Days 31–45 | Navigators/fiscal coordinator: consented plans, payer decisions, timing and supports | No paid cohort without credible destination roles, financing and feasible schedules |
| Days 46–60 | Employers/providers: start paid bridges/internal moves; receiving interviews | Attendance/competence logs, offer decisions, benefits/start-date checks |
| Days 61–75 | Navigators: verify first payroll/continued jobs; resolve failed matches | Early outcomes with denominators, failure reasons and alternative referrals |
| Days 76–90 | Sponsor/evaluator: review access, costs, job quality and evidence completeness | Continue/modify/pause decision; release next enrollment tranche toward 200 |

Suggested operational targets are assumptions: assign a case owner in two business days; assess in five; produce an initial plan in ten; aim for a signed destination before separation when feasible. Missed targets remain visible. Two navigators should begin with about 15–25 active intensive cases each; stagger enrollment or add resources if actual case time makes 200 annual cases infeasible.

## Case movement and readiness gates

1. **Risk confirmed:** record who confirmed it, potential date, affected role and uncertainty. An unverified news item stays a lead.
2. **Worker opted in:** explain choices, data use and support; record the worker's preferences and current compensation baseline.
3. **Pathway assessed:** demonstrate skills, validate necessary requirements and locate a real internal/receiving role.
4. **Resources approved:** written payer determination, provider quote, paid-time arrangement and support plan.
5. **Transition agreed:** retained-role confirmation or voluntary signed offer with pay/hours/benefits/start date and unresolved conditions.
6. **Job verified:** payroll plus worker confirmation; do not count an interview, course completion or conditional offer as a placement.
7. **Follow-up:** 30/90 days and 6/12 months; preserve failed/lost-to-follow-up cases in denominators, with continued referrals.

Launch is conditional on real employer participation and financing. Program design, the reporting skill and the evidence package do not themselves create job openings, award funds or authorize outreach.
