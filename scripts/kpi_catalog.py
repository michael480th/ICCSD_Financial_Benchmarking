#!/usr/bin/env python3
"""
Catalog of every KPI in the three-methodology benchmark, grouped into logical areas.

Single source of truth shared by build_kpi_dataset.py (computes the values) and
build_kpi_report.py (renders them) and the methodology appendix. Each KPI declares:
  key       - column name in data/kpi-three-methodologies.csv
  label     - human label
  group     - logical KPI area (see GROUPS)
  source    - which methodology defines it: Internal | Moody's | S&P | Shared | Context
  formula   - plain-English formula
  unit      - pct | days | ratio_pct | usd | usd_pp | number | x
  good      - 'up' higher-better, 'down' lower-better, 'context' neither
  target    - Iowa / methodology benchmark band (text)
  note      - caveats (e.g. per-capita vs per-pupil, reported vs adjusted)

Methodology factors that CANNOT be derived from audited financials (Moody's Resident
Income & Full-Value-per-Capita; S&P Economy & Management; income/GCP data) are listed in
QUALITATIVE so the report can name them as "external / not scored" rather than guess.
"""

GROUPS = [
    ("cash_liquidity",  "1. Cash & Liquidity",
     "Can the district pay its bills through the year? Cash on hand and short-term solvency."),
    ("reserves",        "2. Reserves & Fund Balance",
     "The financial cushion: available fund balance / reserves relative to the size of operations."),
    ("authority",       "3. Spending Authority (Iowa-specific)",
     "Iowa's binding legal constraint — Unspent Authorized Budget. Not in Moody's or S&P; the #1 ISFIS health indicator."),
    ("operating",       "4. Operating Performance",
     "Does the district live within its means? Margins, operating result, cost structure."),
    ("leverage",        "5. Leverage & Debt",
     "Long-term obligations (debt + pension + OPEB) and the annual fixed-cost burden they create."),
    ("economy_base",    "6. Economy & Tax Base",
     "Revenue-raising capacity: enrollment trend, property wealth, levy effort."),
    ("quality",         "7. Reporting Quality & Framework",
     "Can we trust the numbers, and what state framework do they operate in? Opinions, findings, timeliness."),
]

# good: up=higher better, down=lower better, context=neither
KPIS = [
 # ---- 1. Cash & Liquidity ----
 dict(key="days_net_cash", label="Day's Net Cash Ratio", group="cash_liquidity",
      source="Internal", unit="days", good="up", target="90–120 days (internal target 90)",
      formula="(GF cash + investments) / (total GF expenditures / 365)",
      note="ICCSD FY2024 is audited (ACFR filed June 2026; GF cash $22.5M, ≈41 days). FY2025 uses management figures (PFM GF cash $19.4M, ≈33 days). The FY2025 CAR's GF cash of $43.7M is NOT used: the FY2024 audit proved the CAR's fund-level cash allocation unreliable — it corrected FY2024 CAR governmental cash down $38.4M in total (GF −$3.4M, SAVE+PPEL −$34.4M; the unapproved interfund-loan finding), and the FY2025 CAR repeats the pattern (GF $43.7M vs management's $19.4M while SAVE cash collapses to $9.2M). Management's GF actual is the audit-consistent figure pending the FY2025 audit; see data/iccsd-fy24-car-vs-audit-cash.csv."),
 dict(key="moodys_net_cash_ratio", label="Net Cash Ratio", group="cash_liquidity",
      source="Moody's", unit="ratio_pct", good="up", target="Aaa ≥17.5% · A 5–10% · Ba 0–5% (Aaa endpoint 50%)",
      formula="GF net cash (cash+investments − short-term operating debt) / operating revenue"),
 dict(key="current_ratio", label="Current Ratio", group="cash_liquidity",
      source="Internal", unit="ratio_pct", good="up", target="≥100%",
      formula="GF current assets / (GF current liabilities + deferred inflows)"),
 dict(key="receivables_inventory_ratio", label="Receivables & Inventory Ratio", group="cash_liquidity",
      source="Internal", unit="ratio_pct", good="context", target="context (Iowa property-tax timing dominates)",
      formula="(GF total receivables + inventory) / GF current assets",
      note="In Iowa this is dominated by the succeeding-year property-tax receivable (offset by a matching deferred inflow), so it runs high (~70–80%) and is shown as context. The district's own published ratio (~10%) uses a narrower receivables figure that excludes that item."),

 # ---- 2. Reserves & Fund Balance ----
 dict(key="solvency_ratio", label="Financial Solvency Ratio", group="reserves",
      source="Internal", unit="ratio_pct", good="up", target="5–10% target · ≤25% · <0% alert (Ehlers/ISCAP)",
      formula="(GF unassigned + assigned fund balance) / (GF revenue − AEA flow-through)"),
 dict(key="moodys_avail_fb_ratio", label="Available Fund Balance Ratio", group="reserves",
      source="Moody's", unit="ratio_pct", good="up", target="Aaa ≥17.5% · Aa 10–17.5% · A 5–10% · Baa 0–5%",
      formula="GF available fund balance (committed+assigned+unassigned) / operating revenue"),
 dict(key="sp_available_reserves_pct", label="Available Reserves % of Revenue", group="reserves",
      source="S&P", unit="ratio_pct", good="up", target="'1' >15% · '2' 8–15% · '3' 4–8% · '4' 1–4% · '5' <1%",
      formula="Available GF reserves (fund balance) / GF revenue"),
 dict(key="unrestricted_np_pp", label="Unrestricted Net Position / pupil", group="reserves",
      source="Shared", unit="usd_pp", good="up", target="negative is normal in Iowa (pension/OPEB driven)",
      formula="Government-wide governmental-activities unrestricted net position / certified enrollment"),

 # ---- 3. Spending Authority ----
 dict(key="uab_pct_of_max", label="Unspent Authorized Budget % of Max", group="authority",
      source="Internal", unit="ratio_pct", good="up", target="10–15% total · negative = unlawful → SBRC",
      formula="Unspent authorized budget / maximum authorized budget (Iowa DOM)"),

 # ---- 4. Operating Performance ----
 dict(key="operating_margin", label="Operating Margin (1-yr)", group="operating",
      source="Shared", unit="pct", good="context", target="persistent negative = spending above means",
      formula="(GF revenue − GF expenditure) / GF revenue"),
 dict(key="sp_oper_result_3yr", label="3-yr Avg Operating Result", group="operating",
      source="S&P", unit="pct", good="up", target="'1' >3% · '2' 0–3% · '3' −3–0% · '4' <−3%",
      formula="3-year average of (GF revenue − GF expenditure, net transfers) / GF revenue"),
 dict(key="employee_cost_ratio", label="Employee Cost Ratio", group="operating",
      source="Internal", unit="ratio_pct", good="context", target="75–85% (internal target <80%)",
      formula="(GF salaries + benefits) / total GF expenditures",
      note="Iowa General Funds report expenditures by FUNCTION, not object, so salaries+benefits aren't separable from most audited GF statements. Filled from: ICCSD FY15–19 (its own report), the Iowa DE Certified Annual Report object detail for FY23–24 (all districts, incl. ICCSD — the CAR is filed even when the audit is late), and a few districts whose audits publish object detail. FY20–22 gaps reflect data availability, not oversight."),
 dict(key="foundation_aid_ratio", label="Foundation Aid Ratio", group="operating",
      source="Internal", unit="ratio_pct", good="context", target="no fixed target (falls as property wealth grows)",
      formula="Direct state foundation aid / total GF revenue"),
 dict(key="transportation_ratio", label="Student Transportation Ratio", group="operating",
      source="Internal", unit="ratio_pct", good="down", target="no fixed target",
      formula="Student transportation expenditure / total GF expenditures (CAR)"),
 dict(key="investment_income_ratio", label="Investment Income Ratio", group="operating",
      source="Internal", unit="ratio_pct", good="up", target="higher better",
      formula="GF interest/investment income / total GF revenue"),
 dict(key="gf_per_pupil", label="GF Expenditure per Pupil", group="operating",
      source="Internal", unit="usd_pp", good="context", target="efficiency context vs state avg",
      formula="Total GF expenditures / certified enrollment"),
 dict(key="local_share_pct", label="Local Revenue Share (Contribution)", group="operating",
      source="Internal", unit="ratio_pct", good="context", target="local taxation effort",
      formula="GF local-source revenue / total GF revenue"),

 # ---- 5. Leverage & Debt ----
 dict(key="moodys_ltl_ratio", label="Long-term Liabilities Ratio", group="leverage",
      source="Moody's", unit="ratio_pct", good="down", target="Aaa 125–250% · Aa 250–400% · A 400–550%",
      formula="(direct debt + net pension liab + net OPEB liab) / operating revenue",
      note="Uses REPORTED GASB NPL/OPEB, not Moody's discount-rate-adjusted ANPL/ANOPEB; operating revenue proxied by GF revenue."),
 dict(key="moodys_fixed_costs_ratio", label="Fixed-Costs Ratio", group="leverage",
      source="Moody's", unit="ratio_pct", good="down", target="Aaa 15–20% · Aa 20–25% · A 25–30%",
      formula="(implied 20-yr debt service + pension cost + OPEB contribution) / operating revenue",
      note="Implied debt service = prior-yr debt / 20-yr level annuity at the implied muni rate; pension cost uses actual contribution where tread-water not computable. ICCSD FY24 is audited (debt service $28.8M, pension contribution $12.75M, OPEB pay-go $0.81M per the June-2026 ACFR); ICCSD FY25 uses actual debt service from the CAR but ESTIMATED pension/OPEB contributions (FY25 audit not filed)."),
 dict(key="sp_current_cost_pct", label="Current Cost % of Revenue", group="leverage",
      source="S&P", unit="ratio_pct", good="down", target="local govt '1' <8% · '2' 8–14% · '3' 14–20%",
      formula="(actual debt service P&I + pension contribution + OPEB contribution) / total governmental revenue",
      note="Uses ACTUAL debt service, so bond-refunding years spike (S&P removes such distortions); the Moody's Fixed-Costs Ratio above (implied 20-yr debt service) is the refunding-robust comparator. ICCSD FY23 reflects a refunding; ICCSD FY25 uses CAR debt service + ESTIMATED pension/OPEB (FY25 audit not filed)."),
 dict(key="net_direct_debt_pp", label="Net Direct Debt / pupil", group="leverage",
      source="S&P", unit="usd_pp", good="down", target="S&P bands are per-CAPITA; shown per-pupil as proxy",
      formula="(GO bonds + sales-tax/SAVE revenue bonds + capital loan notes + leases) / certified enrollment",
      note="S&P scores net direct debt PER CAPITA (population). Population not in audits — per-pupil proxy shown, not mapped to the S&P band."),
 dict(key="npl_pp", label="Net Pension Liability / pupil", group="leverage",
      source="S&P", unit="usd_pp", good="down", target="S&P bands are per-CAPITA; shown per-pupil as proxy",
      formula="IPERS net pension liability (governmental activities) / certified enrollment",
      note="Per-capita in S&P; per-pupil proxy here."),
 dict(key="debt_per_pupil", label="Total Debt / pupil", group="leverage",
      source="Shared", unit="usd_pp", good="down", target="context",
      formula="(GO + SAVE/sales-tax revenue bonds + capital loan notes + leases) / certified enrollment"),

 # ---- 6. Economy & Tax Base ----
 dict(key="enrollment_cagr_3yr", label="Enrollment Trend (3-yr CAGR)", group="economy_base",
      source="Moody's", unit="pct", good="context", target="Aaa 2–4% · Aa 0–2% or >4% · A −2–0% (V-shaped: ~3% ideal)",
      formula="3-year compound annual growth rate of certified enrollment"),
 dict(key="valuation_per_pupil", label="Taxable Valuation per Pupil", group="economy_base",
      source="Context", unit="usd_pp", good="up", target="local revenue-raising capacity (PPEL/debt headroom)",
      formula="District taxable valuation / certified enrollment (Iowa DOM)"),
 dict(key="grand_total_levy_rate", label="Total Property Tax Rate", group="economy_base",
      source="Internal", unit="x", good="context", target="local taxation effort (per $1,000 valuation)",
      formula="Grand total district levy rate per $1,000 taxable valuation (Iowa DOM)"),

 # ---- 7. Reporting Quality & Framework ----
 dict(key="opinion_type", label="Audit Opinion", group="quality",
      source="Shared", unit="text", good="context", target="unmodified = clean",
      formula="Independent auditor's opinion type"),
 dict(key="findings_count", label="Audit Findings (count)", group="quality",
      source="Shared", unit="number", good="down", target="0 best; repeat findings weighted worse",
      formula="Count of internal-control / compliance findings in Schedule of Findings"),
 dict(key="repeat_finding", label="Repeat Finding", group="quality",
      source="Shared", unit="yn", good="down", target="N",
      formula="Any finding repeated from the prior year (not remediated)"),
 dict(key="report_lag_months", label="Audit Filing Lag", group="quality",
      source="Shared", unit="months", good="down", target="filed within statutory window (~3–6 mo)",
      formula="Months from fiscal year-end (June 30) to audit report date"),
 dict(key="gfoa_award", label="GFOA / ASBO Recognition", group="quality",
      source="Shared", unit="yn", good="up", target="Y = earns GFOA Certificate of Achievement (or ASBO)",
      formula="District submits for and earns the GFOA Certificate of Achievement for Excellence in Financial Reporting (some hold ASBO instead)",
      note="Tracks the GFOA certificate flag; a 'N' may still hold the ASBO Certificate of Excellence (e.g. Dubuque, Linn-Mar) — recognition, not a deficiency."),
 dict(key="data_basis", label="Data Basis", group="quality",
      source="Context", unit="text", good="context", target="audited > management/unaudited",
      formula="audited ACFR vs management/unaudited actual vs projected"),
]

# Methodology factors that cannot be computed from audited financials (named, not scored)
QUALITATIVE = [
 dict(methodology="Moody's", factor="Resident Income (MHI adj for RPP / US MHI)", weight="10%",
      reason="Needs Census ACS median household income + BEA regional price parity — external, not in audits."),
 dict(methodology="Moody's", factor="Full Value per Capita", weight="10%",
      reason="Needs district POPULATION (not enrollment). Valuation-per-pupil is shown instead as an Iowa-appropriate proxy."),
 dict(methodology="Moody's", factor="Institutional Framework", weight="10%",
      reason="Qualitative & identical statewide: Iowa is a STATE-DETERMINED revenue framework (foundation formula caps spending authority) with limited voter-approved local supplements (ISL, PPEL, SAVE). Analyst-assigned, same for all Iowa districts."),
 dict(methodology="S&P", factor="Economy (county GCP per capita, PCPI)", weight="20%",
      reason="Needs county gross product & per-capita personal income vs US — external macro data, not in audits."),
 dict(methodology="S&P", factor="Management", weight="20%",
      reason="Qualitative assessment of budgeting, long-term planning, policies — read from governance, not a single ratio."),
 dict(methodology="S&P", factor="Institutional Framework", weight="anchor",
      reason="S&P assigns an IF by state/government type; same for all Iowa school districts."),
]


# ---------------------------------------------------------------------------------------------
# Rating BANDS for the line-chart background shading, the legend, and the heatmap cell colors.
# Each band: (label, color, lo, hi) in the metric's own units; lo/hi None = open-ended.
# Colors run green (strong) -> red (weak). "good" direction is encoded in the KPI itself; the
# bands are written in absolute metric space so the chart can shade them regardless of direction.
RATING = {  # Moody's alpha categories
 "Aaa":"#15803d","Aa":"#22c55e","A":"#86efac","Baa":"#fde047","Ba":"#fb923c","B":"#f87171","Caa":"#dc2626"}
SP = {"1":"#15803d","2":"#22c55e","3":"#fde047","4":"#fb923c","5":"#f87171","6":"#dc2626"}
TG = {"good":"#22c55e","ok":"#fde047","watch":"#fb923c","bad":"#f87171","neut":"#cbd5e1"}

def _m(lo, hi, order):  # build Moody's 7-band list given ascending value cut points (worst->best by 'order')
    pass

BANDS = {
 # ---- cash & liquidity ----
 "days_net_cash": [("watch","#fb923c",None,60),("ok","#fde047",60,90),("good","#22c55e",90,None)],
 "moodys_net_cash_ratio": [("Caa",RATING["Caa"],None,-10),("B",RATING["B"],-10,-5),("Ba",RATING["Ba"],-5,0),
     ("Baa",RATING["Baa"],0,5),("A",RATING["A"],5,10),("Aa",RATING["Aa"],10,17.5),("Aaa",RATING["Aaa"],17.5,None)],
 "current_ratio": [("bad","#f87171",None,90),("ok","#fde047",90,100),("good","#22c55e",100,None)],
 # ---- reserves ----
 "solvency_ratio": [("bad","#f87171",None,0),("watch","#fb923c",0,5),("ok","#fde047",5,10),("good","#22c55e",10,None)],
 "moodys_avail_fb_ratio": [("Caa",RATING["Caa"],None,-10),("B",RATING["B"],-10,-5),("Ba",RATING["Ba"],-5,0),
     ("Baa",RATING["Baa"],0,5),("A",RATING["A"],5,10),("Aa",RATING["Aa"],10,17.5),("Aaa",RATING["Aaa"],17.5,None)],
 "sp_available_reserves_pct": [("5",SP["5"],None,1),("4",SP["4"],1,4),("3",SP["3"],4,8),("2",SP["2"],8,15),("1",SP["1"],15,None)],
 # ---- authority ----
 "uab_pct_of_max": [("bad","#f87171",None,0),("watch","#fb923c",0,5),("ok","#fde047",5,10),("good","#22c55e",10,None)],
 # ---- operating ----
 "operating_margin": [("bad","#f87171",None,-3),("watch","#fb923c",-3,0),("good","#22c55e",0,None)],
 "sp_oper_result_3yr": [("4",SP["4"],None,-3),("3",SP["3"],-3,0),("2",SP["2"],0,3),("1",SP["1"],3,None)],
 "employee_cost_ratio": [("good","#22c55e",None,80),("ok","#fde047",80,85),("bad","#f87171",85,None)],
 # ---- leverage ----
 "moodys_ltl_ratio": [("Aaa",RATING["Aaa"],None,250),("Aa",RATING["Aa"],250,400),("A",RATING["A"],400,550),
     ("Baa",RATING["Baa"],550,700),("Ba",RATING["Ba"],700,850),("B",RATING["B"],850,1000),("Caa",RATING["Caa"],1000,None)],
 "moodys_fixed_costs_ratio": [("Aaa",RATING["Aaa"],None,20),("Aa",RATING["Aa"],20,25),("A",RATING["A"],25,30),
     ("Baa",RATING["Baa"],30,35),("Ba",RATING["Ba"],35,45),("B",RATING["B"],45,55),("Caa",RATING["Caa"],55,None)],
 "sp_current_cost_pct": [("1",SP["1"],None,8),("2",SP["2"],8,14),("3",SP["3"],14,20),("4",SP["4"],20,25),
     ("5",SP["5"],25,30),("6",SP["6"],30,None)],
 # ---- economy ----
 "enrollment_cagr_3yr": [("bad","#f87171",None,-2),("watch","#fb923c",-2,0),("good","#22c55e",0,None)],
 # ---- quality (categorical handled separately in the report) ----
}

# KPIs that are per-pupil proxies for a per-capita agency band, or otherwise context-only: no band shading.
CONTEXT_KEYS = {"unrestricted_np_pp","receivables_inventory_ratio","foundation_aid_ratio","transportation_ratio","investment_income_ratio",
 "gf_per_pupil","local_share_pct","net_direct_debt_pp","npl_pp","debt_per_pupil",
 "valuation_per_pupil","grand_total_levy_rate"}

def band_label_for(key, value):
    """Return (label, color) for a numeric value, or None."""
    bands = BANDS.get(key)
    if bands is None or value is None: return None
    for label, color, lo, hi in bands:
        if (lo is None or value >= lo) and (hi is None or value < hi):
            return (label, color)
    return None
