# ICCSD financial KPIs under three methodologies (FY2015–FY2025)

**What this is.** A single, comparable calculation of the Iowa City Community School District's
financial KPIs — and the 14 benchmarked peer districts — under **three methodologies**:

1. **ICCSD's own internal definitions** — the district's *Annual Financial Health Report* "Ten-Point
   Financial Condition Test" (Leslie Finger, the FY2019 edition is the reference).
2. **Moody's Ratings** — *US K-12 Public School Districts* methodology (24 July 2024).
3. **S&P Global Ratings** — *Methodology For Rating US Governments* (9 Sept 2024).

KPIs are grouped into **seven logical areas** so the same financial question can be read across all
three frameworks at once. The companion deliverables are:

| File | What it is |
|---|---|
| `kpi-three-methodologies.html` | Interactive grouped report — ICCSD vs. 14 peers, FY15–25, per-KPI district×year heatmaps |
| `data/kpi-three-methodologies.csv` | One row per district-year, every computable KPI, with data-basis/confidence |
| `scripts/kpi_catalog.py` | The KPI catalog (group, methodology, formula, target, caveats) — single source of truth |
| `scripts/build_kpi_dataset.py` | Consolidates the source data and computes every KPI |
| `scripts/build_kpi_report.py` | Renders the HTML |

Every figure traces to an audited ACFR or an official Iowa state filing. ICCSD's **FY2024 audit was
filed June 10, 2026** (RSM US LLP; five financial-statement material weaknesses, qualified single-audit
opinions) and FY2024 is now included **as audited**. Its **FY2025 audit is still unfiled**, so FY2025 uses
management/unaudited actuals (PFM Financial Advisors, April 2026) plus the FY2025 CAR balance sheet,
**adjusted for the corrections the FY2024 audit made to the FY2024 CAR** (see below); FY2025 is flagged
as such everywhere.

### FY2024 audit vs the FY2024 CAR, and how it carries into FY2025

The FY2024 audit materially corrected the district's self-reported CAR, concentrated in cash by fund
(full detail: `data/iccsd-fy24-car-vs-audit-cash.csv`):

| Item | FY24 CAR | FY24 audited | Correction |
|---|---:|---:|---:|
| GF cash & investments | $25,913,933 | $22,536,992 | −$3.38M |
| SAVE + PPEL + Other Capital cash | $64,112,359 | $29,750,724 (combined Capital Projects Fund) | −$34.36M |
| **Total governmental-funds cash** | **$105,655,525** | **$67,238,805** | **−$38.42M** |
| GF ending fund balance | $19,366,904 | $19,053,053 | −$0.31M |
| GF unassigned balance | $14,881,750 | $16,281,856 | +$1.40M (reclass from restricted) |

The $38.4M cash overstatement matches the audit's finding of ~$38M in interfund transfers made without
board approval: the CAR reported fund-level cash as if the money had never moved. The FY2025 CAR repeats
the pattern — GF cash of $43.7M against management's actual of $19.4M, with SAVE cash collapsing to $9.2M —
so for FY2025 we: (1) roll the FY2025 CAR's own net change (−$1,073,229) off the **audited** FY2024 base,
giving an adjusted GF balance of **$17,979,824** (unassigned **$13,671,516** after carrying the audit's
reclassification); and (2) use management's GF cash ($19,364,761) in current assets instead of the FY2025
CAR's $43.7M. Both are estimates pending the FY2025 audit.

---

## The seven KPI groups

| # | Group | What it answers | KPIs (and which methodology defines each) |
|---|---|---|---|
| 1 | **Cash & Liquidity** | Can the district pay its bills through the year? | Day's Net Cash *(Internal)* · Net Cash Ratio *(Moody's)* · Current Ratio *(Internal)* · Receivables & Inventory Ratio *(Internal)* · Creditor's Equity Ratio *(Internal)* |
| 2 | **Reserves & Fund Balance** | How big is the cushion vs. the size of operations? | Financial Solvency Ratio *(Internal)* · Available Fund Balance Ratio *(Moody's)* · Available Reserves % of Revenue *(S&P)* · Unrestricted Net Position / pupil *(shared)* |
| 3 | **Spending Authority** (Iowa-unique) | Is the district within its legal spending cap? | Unspent Authorized Budget % of Max *(Internal/ISFIS)* · Unrestricted Unspent Balance Ratio *(Internal)* |
| 4 | **Operating Performance** | Does it live within its means? | Operating Margin *(shared)* · 3-yr Avg Operating Result *(S&P)* · Employee Cost Ratio *(Internal)* · Foundation Aid Ratio *(Internal)* · Transportation Ratio *(Internal)* · Investment Income Ratio *(Internal)* · GF Expenditure / pupil *(Internal)* · Local Revenue Share *(Internal)* |
| 5 | **Leverage & Debt** | How heavy are long-term obligations & their annual cost? | Long-term Liabilities Ratio *(Moody's)* · Fixed-Costs Ratio *(Moody's)* · Current Cost % of Revenue *(S&P)* · Net Direct Debt / pupil *(S&P proxy)* · Net Pension Liability / pupil *(S&P proxy)* · Total Debt / pupil *(shared)* |
| 6 | **Economy & Tax Base** | What revenue-raising capacity backs the district? | Enrollment 3-yr CAGR *(Moody's)* · Taxable Valuation / pupil *(context)* · Total Property Tax Rate *(Internal)* |
| 7 | **Reporting Quality & Framework** | Can we trust the numbers; what state framework governs them? | Audit Opinion · Findings count · Repeat Finding · Audit Filing Lag *(shared)* · Institutional Framework *(qualitative)* |

---

## Methodology 1 — ICCSD internal "Ten-Point Financial Condition Test"

Drawn from the district's published report; data is mostly from the Certified Annual Report (CAR).

| Ratio | Formula | District target |
|---|---|---|
| Creditor's Equity | ISCAP restricted assets ÷ current assets | 0% (no short-term borrowing) |
| Current Ratio | current assets ÷ (current liabilities + deferred inflows) | ≥ 100% |
| Day's Net Cash | (cash + investments) ÷ (GF expenditures ÷ 365) | 90–120 days |
| Employee Cost | (wages + benefits) ÷ GF expenditures | 75–85% (target < 80%) |
| Foundation Aid | direct state aid ÷ GF revenue | no fixed target |
| Financial Solvency | (assigned + unassigned GF balance) ÷ (GF revenue − AEA flow-through) | 5–10%; ≤ 25%; < 0% = alert |
| Investment Income | interest income ÷ GF revenue | higher is better |
| Receivables & Inventory | (receivables + inventory) ÷ current assets | as close to 0% |
| Student Transportation | transportation expenditure ÷ GF expenditures | no fixed target |
| Unspent Balance | unspent spending authority ÷ maximum budget authority | 10–15% total; > 5% unrestricted |

For **ICCSD FY2015–FY2019** these ratios are taken **verbatim** from the district's own report
(`data/iccsd-internal-kpis-fy15-19.csv`) — the highest-confidence source. For peers and later years
they are recomputed from the same definitions where the inputs exist.

## Methodology 2 — Moody's US K-12 scorecard (computable sub-factors)

Moody's weights: Economy 30%, Financial Performance 30%, Institutional Framework 10%, Leverage 30%,
plus notching. We compute the **audit-derivable** sub-factors:

| Sub-factor (weight) | Formula | Aaa / Aa / A bands |
|---|---|---|
| Available Fund Balance Ratio (20%) | available fund balance ÷ operating revenue | ≥17.5% / 10–17.5% / 5–10% |
| Net Cash Ratio (10%) | net cash ÷ operating revenue | ≥17.5% / 10–17.5% / 5–10% |
| Long-term Liabilities Ratio (20%) | (debt + net pension + net OPEB) ÷ operating revenue | 125–250% / 250–400% / 400–550% |
| Fixed-Costs Ratio (10%) | (implied debt service + pension cost + OPEB contribution) ÷ operating revenue | 15–20% / 20–25% / 25–30% |
| Enrollment Trend (10%) | 3-yr CAGR of enrollment | 2–4% / 0–2% or >4% / −2–0% |

*Implied debt service* = prior-year debt ÷ a 20-year level-dollar annuity divisor at a ~4.0% implied
muni rate (Moody's method). *Long-term liabilities* use **reported** GASB pension/OPEB, not Moody's
discount-rate-adjusted ANPL/ANOPEB. *Operating revenue* is proxied by General Fund revenue.

## Methodology 3 — S&P US Governments (computable factors)

S&P uses five equally-weighted factors plus an institutional-framework anchor. We compute the
**financial** ones:

| Factor | Metric | Bands (local government) |
|---|---|---|
| Financial Performance | 3-yr average operating result % | '1' >3% · '2' 0–3% · '3' −3–0% · '4' <−3% |
| Reserves & Liquidity | available reserves ÷ revenue | '1' >15% · '2' 8–15% · '3' 4–8% · '4' 1–4% · '5' <1% |
| Debt & Liabilities | current cost (debt service + pension + OPEB) ÷ governmental revenue | '1' <8% · '2' 8–14% · '3' 14–20% |
| Debt & Liabilities | net direct debt **per capita**; net pension liability **per capita** | <$500 … >$4,500 |

Net direct debt and net pension liability are scored by S&P **per capita** (population). Audits do not
carry population, so this report shows them **per pupil** as an Iowa-appropriate proxy and does **not**
map them onto S&P's per-capita bands.

---

## What is *not* scored (named, not guessed)

Per the agreed approach, factors that cannot be derived from audited financials are named rather than
estimated:

- **Moody's Resident Income** (Census MHI adjusted for BEA regional price parity) and **Full Value per
  Capita** (needs population) — external. Valuation-per-pupil is shown as the Iowa proxy.
- **S&P Economy** (county gross product, per-capita personal income vs. U.S.) and **S&P Management**
  (budgeting / planning / policies) — external or qualitative.
- **Institutional Framework** (both agencies) — qualitative and **identical for all Iowa districts**:
  a *state-determined* revenue framework. Iowa's foundation formula sets each district's spending
  authority; districts add limited voter-approved local money (Instructional Support Levy, PPEL, SAVE).
  This is why **spending authority (UAB), not cash, is the binding constraint** in Iowa — captured in
  KPI Group 3, which has no Moody's/S&P analogue.

## Data sources & coverage

- **Audited ACFRs** — `auditreports/` (74 FY2015–2019 PDFs + FY2020–2025). GF backbone in
  `data/audit-financials.csv`; detailed schema in `data/iowa-district-financials.csv` (FY20–25) and
  `data/fy15-19-extractions/` + `data/fy15-19-notes/` (FY15–19, extracted for this analysis).
- **Iowa DOM** — `data/dom/` : Unspent Authorized Budget, certified enrollment, valuations, levy rates (FY20–25).
- **Certified Annual Report** — `CAR/` : function-level detail (transportation, state aid, local share,
  interest) FY2017–2023.
- **ICCSD internal report** — `data/iccsd-internal-kpis-fy15-19.csv` (verbatim FY15–19 ratios).
- **ICCSD management** — `data/iccsd-cash-supplemental.csv` (FY24–26 unaudited/projected).

**Coverage notes.** Object-level salaries are not broken out in most Iowa General Funds, so the
Employee Cost Ratio is available for ICCSD (its own report) and for years/districts where the audit or
CAR separates it. Fixed-cost and current-cost ratios need annual debt service and employer
pension/OPEB contributions — extracted for FY2015–2019; blank for later years where not yet captured.
Blanks are honest gaps, never guesses (the repo's "confidence over completeness" rule).
