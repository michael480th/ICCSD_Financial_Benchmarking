#!/usr/bin/env python3
"""
Build data/kpi-three-methodologies.csv — one row per district x fiscal year (FY2015-FY2025)
with every KPI from the three frameworks (ICCSD internal 10-point test, Moody's US K-12
scorecard, S&P US Governments), grouped by logical area (see scripts/kpi_catalog.py).

Every value is computed only when its inputs exist; missing inputs leave a blank cell (the
repo's "confidence over completeness" rule). Data basis is tracked per row: audited ACFR,
management/unaudited actual, or projected.

Inputs (all already in the repo):
  data/audit-financials.csv ............ GF rev/exp/fund-balance/cash, FY15-23, all core districts
  data/iowa-district-financials.csv .... detailed schema (debt, NPL, OPEB, salaries...), FY20-25
  data/fy15-19-extractions/*.csv ....... detailed schema back-filled to FY15-19 (pipe-delimited)
  data/fy15-19-notes/*.csv ............. govt-wide net position + capital-asset/debt notes, FY15-19
  data/notes-extractions/*.csv ......... govt-wide net position notes, FY20-25
  data/dom/{unspent-authorized-budget,certified-enrollment,levy-rates-and-valuation}.csv  FY20-25
  data/iccsd-internal-kpis-fy15-19.csv . ICCSD's own published ratios FY15-19 (authoritative)
  data/iccsd-cash-supplemental.csv ..... ICCSD FY24-26 management/unaudited GF cash
  CAR/iowa_school_district_{revenues,expenditures}_by_fiscal_year_*.csv  function detail FY17-23

-> data/kpi-three-methodologies.csv
"""
import csv, os, glob, math
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def p(*a): return os.path.join(ROOT, *a)

DISTRICTS = ["Iowa City CSD","Ankeny CSD","Cedar Rapids CSD","Davenport CSD",
    "Des Moines Independent CSD","Dubuque CSD","Johnston CSD","Linn-Mar CSD",
    "Pleasant Valley CSD","Waterloo CSD","Waukee CSD","West Des Moines CSD",
    "College CSD (Prairie)","Muscatine CSD","Burlington CSD"]
YEARS = list(range(2015, 2026))

# CAR uses short names (and has collisions) -> map our canonical name to the EXACT CAR string
CAR_NAME = {
 "Iowa City CSD":"Iowa City","Ankeny CSD":"Ankeny","Cedar Rapids CSD":"Cedar Rapids",
 "Davenport CSD":"Davenport","Des Moines Independent CSD":"Des Moines Independent",
 "Dubuque CSD":"Dubuque","Johnston CSD":"Johnston","Linn-Mar CSD":"Linn-Mar",
 "Pleasant Valley CSD":"Pleasant Valley","Waterloo CSD":"Waterloo","Waukee CSD":"Waukee",
 "West Des Moines CSD":"West Des Moines","College CSD (Prairie)":"College Community",
 "Muscatine CSD":"Muscatine","Burlington CSD":"Burlington"}

def f(x):
    if x is None: return None
    s = str(x).strip().replace(",", "").replace("$", "")
    if s in ("", "-", "—", "–", "."): return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try: v = float(s); return -v if neg else v
    except ValueError: return None

def div(a, b):
    a, b = f(a), f(b)
    if a is None or b in (None, 0): return None
    return a / b

def rows(path, delim=","):
    if not os.path.exists(path): return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter=delim))

# ----------------------------------------------------------------------------- load sources
base = defaultdict(dict)   # (district, fy) -> merged raw fields
def setrow(d, fy, data, overwrite=True):
    k = (d, int(fy))
    for kk, vv in data.items():
        if vv in (None, ""): continue
        if overwrite or kk not in base[k]:
            base[k][kk] = vv

# audit-financials (FY15-23 backbone)
for r in rows(p("data/audit-financials.csv")):
    d = r["district"]
    if d not in DISTRICTS: continue
    # NB: audit-financials `cash` is GENERAL-FUND cash (from the GF balance sheet) -> gf_cash.
    setrow(d, r["fiscal_year"], dict(
        gf_revenue=r["revenues"], gf_expenditure=r["expenditures"], gf_cash=r["cash"],
        fb_nonspendable=r["fb_nonspendable"], fb_restricted=r["fb_restricted"],
        fb_committed=r["fb_committed"], fb_assigned=r["fb_assigned"],
        fb_unassigned=r["fb_unassigned"], fb_total=r["fb_total"]))

# iowa-district-financials (detailed FY20-25) -- authoritative for those years
for r in rows(p("data/iowa-district-financials.csv")):
    d = r["district"]
    if d not in DISTRICTS: continue
    setrow(d, r["fiscal_year"], dict(
        auditor=r.get("auditor"), report_date=r.get("report_date"), opinion_type=r.get("opinion_type"),
        certified_enrollment=r.get("certified_enrollment"),
        gf_revenue=r.get("gf_revenue"), gf_expenditure=r.get("gf_expenditure"),
        gf_total_fund_balance=r.get("gf_total_fund_balance"), gf_unassigned=r.get("gf_unassigned"),
        gf_assigned=r.get("gf_assigned"), aea_flowthrough=r.get("aea_flowthrough"),
        salaries_benefits=r.get("salaries_benefits"), total_cash=r.get("cash_and_investments"),
        go_debt=r.get("go_debt_outstanding"), save_rev_bonds=r.get("save_rev_bonds"),
        lease_sbita=r.get("lease_sbita"), capital_additions=r.get("capital_additions"),
        depreciation=r.get("depreciation"), construction_in_progress=r.get("construction_in_progress"),
        save_revenue=r.get("save_revenue"), unrestricted_np=r.get("unrestricted_net_position"),
        ipers_npl=r.get("ipers_npl"), opeb_liability=r.get("opeb_liability"),
        findings_count=r.get("findings_count"), material_weakness=r.get("material_weakness"),
        repeat_finding=r.get("repeat_finding"), gfoa_cert=r.get("gfoa_cert")))

# FY15-19 detailed back-fill (pipe). These agent extractions were each cross-checked against
# audit-financials.csv and are the most carefully validated source for FY15-19 -> authoritative
# (overwrite=True), which also corrects the few broken cells in the automated audit-financials.csv.
for path in glob.glob(p("data/fy15-19-extractions/*.csv")):
    for r in rows(path, "|"):
        d = r.get("district");  fy = r.get("fiscal_year")
        if not d or not fy: continue
        setrow(d, fy, dict(
            auditor=r.get("auditor"), report_date=r.get("report_date"), opinion_type=r.get("opinion_type"),
            certified_enrollment=r.get("certified_enrollment"),
            gf_revenue=r.get("gf_revenue"), gf_expenditure=r.get("gf_expenditure"),
            gf_total_fund_balance=r.get("gf_total_fund_balance"), gf_unassigned=r.get("gf_unassigned"),
            gf_assigned=r.get("gf_assigned"), fb_committed=r.get("gf_committed"),
            aea_flowthrough=r.get("aea_flowthrough"), state_aid_direct=r.get("state_aid_direct"),
            interest_income=r.get("interest_income"), salaries_benefits=r.get("salaries_benefits"),
            gf_current_assets=r.get("gf_current_assets"), gf_receivables=r.get("gf_receivables"),
            gf_inventory=r.get("gf_inventory"), gf_prepaid=r.get("gf_prepaid"),
            gf_current_liabilities=r.get("gf_current_liabilities"), gf_deferred_inflows=r.get("gf_deferred_inflows"),
            iscap_restricted=r.get("iscap_restricted_assets"), gf_cash=r.get("cash_and_investments"),
            go_debt=r.get("go_debt_outstanding"), capital_loan_notes=r.get("capital_loan_notes"),
            save_rev_bonds=r.get("save_rev_bonds"), lease_sbita=r.get("lease_sbita"),
            annual_debt_service=r.get("annual_debt_service"), capital_additions=r.get("capital_additions"),
            depreciation=r.get("depreciation"), construction_in_progress=r.get("construction_in_progress"),
            save_revenue=r.get("save_revenue"), unrestricted_np=r.get("unrestricted_net_position"),
            ipers_npl=r.get("ipers_npl"), opeb_liability=r.get("opeb_liability"),
            pension_contribution=r.get("pension_contribution"), opeb_contribution=r.get("opeb_contribution"),
            findings_count=r.get("findings_count"), material_weakness=r.get("material_weakness"),
            repeat_finding=r.get("repeat_finding"), gfoa_cert=r.get("gfoa_cert"),
            extract_confidence=r.get("confidence")), overwrite=True)

# notes (gov-wide net position + capital-asset gross/accum dep) FY15-19 and FY20-25
for path in glob.glob(p("data/fy15-19-notes/*.csv")) + glob.glob(p("data/notes-extractions/*.csv")):
    for r in rows(path, "|"):
        d = r.get("district"); fy = r.get("fiscal_year")
        if not d or not fy or d not in DISTRICTS: continue
        setrow(d, fy, dict(
            unrestricted_np=r.get("unrestricted_net_position"),
            gross_capital_assets=r.get("gross_capital_assets"),
            accumulated_depreciation=r.get("accumulated_depreciation"),
            debt_service_next_fy=r.get("debt_service_next_fy")), overwrite=False)

# FY20-25 GF balance-sheet detail (pipe) -> current ratio / receivables / creditor-equity / interest
for path in glob.glob(p("data/fy20-25-bsheet/*.csv")):
    for r in rows(path, "|"):
        d = r.get("district"); fy = r.get("fiscal_year")
        if not d or not fy or d not in DISTRICTS: continue
        setrow(d, fy, dict(
            gf_current_assets=r.get("gf_current_assets"), gf_receivables=r.get("gf_receivables"),
            gf_inventory=r.get("gf_inventory"), gf_prepaid=r.get("gf_prepaid"),
            gf_current_liabilities=r.get("gf_current_liabilities"), gf_deferred_inflows=r.get("gf_deferred_inflows"),
            iscap_restricted=r.get("iscap_restricted_assets"), interest_income=r.get("interest_income")),
            overwrite=False)

# FY20-25 fixed-cost inputs (pension/OPEB contributions + annual debt service) -> fixed-cost & current-cost ratios
for path in glob.glob(p("data/fy20-25-flows/*.csv")):
    for r in rows(path, "|"):
        d = r.get("district"); fy = r.get("fiscal_year")
        if not d or not fy or d not in DISTRICTS: continue
        setrow(d, fy, dict(
            pension_contribution=r.get("pension_contribution"), opeb_contribution=r.get("opeb_contribution"),
            annual_debt_service=r.get("annual_debt_service")), overwrite=False)

# DOM AEA flow-through (FY15-25) -> solvency denominator (filled only where not already set)
for r in rows(p("data/dom/aea-flowthrough.csv")):
    if r["district"] in DISTRICTS:
        setrow(r["district"], r["fiscal_year"], dict(aea_flowthrough=r["aea_flowthrough"]), overwrite=False)

# ICCSD FY2025 CAR balance sheet (self-reported; fills FY25 balance-sheet ratios). PFM cash/rev/exp
# already loaded from iccsd-cash-supplemental stay (overwrite=False) — see source note re: cash gap.
for r in rows(p("data/iccsd-fy25-car.csv")):
    setrow(r["district"], r["fiscal_year"], dict(
        gf_current_assets=r["gf_current_assets"], gf_receivables=r["gf_receivables"],
        gf_inventory=r["gf_inventory"], gf_current_liabilities=r["gf_current_liabilities"],
        gf_deferred_inflows=r["gf_deferred_inflows"], gf_unassigned=r["gf_unassigned"],
        gf_assigned=r["gf_assigned"], fb_committed=r["gf_committed"],
        gf_total_fund_balance=r["gf_total_fund_balance"]), overwrite=False)

# ICCSD FY2025 CAR detail (revenue/expenditure/object + LT-liability pages) -> fills FY25 operating &
# leverage ratios. salaries_benefits is a Medium-confidence GF-function estimate (see source note).
for r in rows(p("data/iccsd-fy25-car-detail.csv")):
    setrow(r["district"], r["fiscal_year"], dict(
        state_aid_direct=r["state_aid_direct"], interest_income=r["interest_income"],
        salaries_benefits=r["salaries_benefits"], transportation_exp=r["transportation_exp"],
        local_share_direct=r["local_share_direct"], go_debt=r["go_debt"], ipers_npl=r["ipers_npl"],
        annual_debt_service=r.get("annual_debt_service"), pension_contribution=r.get("pension_contribution"),
        opeb_contribution=r.get("opeb_contribution")), overwrite=False)

# DOM: UAB, enrollment, valuation/levies (FY20-25)
for r in rows(p("data/car-salaries.csv")):
    if r["district"] in DISTRICTS:   # GF salaries+benefits (object detail) from the CAR workbooks, FY23-24
        setrow(r["district"], r["fiscal_year"], dict(salaries_benefits=r["salaries_benefits"]), overwrite=False)
for r in rows(p("data/dom/unspent-authorized-budget.csv")):
    if r["district"] in DISTRICTS:
        setrow(r["district"], r["fiscal_year"], dict(
            uab=r["unspent_authorized_budget"], uab_max=r["max_authorized_budget"],
            uab_pct_of_max=r["uab_pct_of_max"]))
for r in rows(p("data/dom/certified-enrollment.csv")):
    if r["district"] in DISTRICTS:
        setrow(r["district"], r["fiscal_year"], dict(certified_enrollment=r["certified_enrollment"]), overwrite=False)
for r in rows(p("data/dom/levy-rates-and-valuation.csv")):
    if r["district"] in DISTRICTS:
        setrow(r["district"], r["fiscal_year"], dict(
            taxable_valuation=r["taxable_valuation"], grand_total_rate=r["grand_total_rate"]))

# ICCSD management/unaudited FY24-26
for r in rows(p("data/iccsd-cash-supplemental.csv")):
    setrow(r["district"], r["fiscal_year"], dict(
        gf_cash=r["gf_cash_investments"], gf_revenue=r["gf_revenue"], gf_expenditure=r["gf_expenditures"],
        data_basis=("projected" if "projected" in r.get("status","") else "management-unaudited")))

# ICCSD FY2025: adjust the FY25 CAR balance sheet for the corrections the FY2024 audit (filed
# June 2026) made to the FY2024 CAR — see data/iccsd-fy24-car-vs-audit-cash.csv.
#   Fund balance: the audit set FY24 ending GF balance at $19,053,053 vs the CAR's $19,366,904
#   (−$313,851) and reclassified $1,400,106 from restricted to unassigned ($16,281,856 vs the
#   CAR's $14,881,750). Rolling the FY25 CAR's own net change (−$1,073,229) off the audited base:
#   total = 18,293,675 − 313,851 = $17,979,824; unassigned = 12,271,410 + 1,400,106 = $13,671,516.
#   Cash: the audit showed the CAR's fund-level cash allocation is unreliable — FY24 governmental
#   cash overstated $38.4M in total (GF −$3.4M, SAVE/PPEL −$34.4M; the unapproved-interfund-loan
#   finding). The FY25 CAR repeats the pattern (GF cash $43,685,677 vs management's actual
#   $19,364,761 while SAVE collapses to $9.2M), so GF current assets carry management's GF cash,
#   consistent with the days-cash figure above: 140,114,929 − 43,685,677 + 19,364,761 = $115,794,013.
# These are estimates pending the FY2025 audit; the row stays flagged management-unaudited.
setrow("Iowa City CSD", 2025, dict(
    gf_total_fund_balance=17979824, gf_unassigned=13671516,
    gf_current_assets=115794013), overwrite=True)

# ICCSD verbatim internal ratios FY15-19 (authoritative override for the internal block)
ICCSD_VERBATIM = {}
for r in rows(p("data/iccsd-internal-kpis-fy15-19.csv")):
    ICCSD_VERBATIM[(r["district"], int(r["fiscal_year"]))] = r

# ---- CAR function detail (FY17-23): transportation, state aid, local share, AEA flow-through ----
car_exp = defaultdict(lambda: defaultdict(float))   # (carname, fy) -> {col: amount} for General fund
car_rev = defaultdict(lambda: defaultdict(float))
WANT_CARNAMES = set(CAR_NAME.values())
ep = p("CAR/iowa_school_district_expenditures_by_fiscal_year_994_rows.csv")
if os.path.exists(ep):
    for r in csv.DictReader(open(ep)):
        if r["district_name"] in WANT_CARNAMES and r["actual_reestimated_budget"] == "Actual" and r["fund"] == "General":
            a = f(r["amount"])
            if a is not None: car_exp[(r["district_name"], r["fiscal_year"])][r["column_name"]] += a
rp = p("CAR/iowa_school_district_revenues_by_fiscal_year_995_rows.csv")
if os.path.exists(rp):
    for r in csv.DictReader(open(rp)):
        if r["district_name"] in WANT_CARNAMES and r["actual_reestimated_budget"] == "Actual" and r["fund"] == "General":
            a = f(r["amount"])
            if a is not None: car_rev[(r["district_name"], r["fiscal_year"])][(r["column_name"], r["source"].strip())] += a

# General-fund CAR columns are prefixed "gen" (gentransp, genstateaid, geninstr, ...).
LOCAL_REV = ["genproptx","genincomesurtax","genCIrepl","genutiltx","gentuittrans","genoth",
             "genact","genint","genFixedAsset","genmobilehome","genothlocal"]
STATE_REV = ["genstateaid","genotherstate"]
FED_REV   = ["genIDEA","genTitle","genfed","genotherfed","genperlIDEA"]

def car_transp(d, fy):
    e = car_exp.get((CAR_NAME[d], str(fy)))
    return e.get("gentransp") if e else None

def car_stateaid(d, fy):
    e = car_rev.get((CAR_NAME[d], str(fy)))
    return e.get(("genstateaid", "State Foundation Aid")) if e else None

def car_interest(d, fy):
    e = car_rev.get((CAR_NAME[d], str(fy)))
    if not e: return None
    return sum(v for (c, s), v in e.items() if c == "genint")

def car_local_share(d, fy):
    e = car_rev.get((CAR_NAME[d], str(fy)))
    if not e: return None
    loc = sum(v for (c, s), v in e.items() if c in LOCAL_REV)
    st  = sum(v for (c, s), v in e.items() if c in STATE_REV)
    fed = sum(v for (c, s), v in e.items() if c in FED_REV)
    tot = loc + st + fed
    return (loc / tot) if tot else None

# ----------------------------------------------------------------------------- helpers for KPIs
IMPLIED_RATE = 0.04           # ~Bond Buyer 20-bond GO 10-yr avg over FY15-25 (Moody's example 3.90%)
AMORT_DIVISOR = (1 - (1 + IMPLIED_RATE) ** -20) / IMPLIED_RATE   # level-dollar 20-yr annuity divisor

def enrollment(d, fy):
    v = f(base[(d, fy)].get("certified_enrollment"))
    if v is None and (d, fy) in ICCSD_VERBATIM:
        v = f(ICCSD_VERBATIM[(d, fy)]["enrollment_oct"])
    return v

def debt_total(rec):
    parts = [f(rec.get(k)) for k in ("go_debt","save_rev_bonds","capital_loan_notes","lease_sbita")]
    parts = [x for x in parts if x is not None]
    return sum(parts) if parts else None

def available_fb(rec):
    parts = [f(rec.get(k)) for k in ("fb_committed","gf_assigned","fb_assigned","gf_unassigned","fb_unassigned")]
    # prefer the detailed gf_* if present, else fb_*; de-dupe assigned/unassigned
    assigned = f(rec.get("gf_assigned")) if rec.get("gf_assigned") not in (None,"") else f(rec.get("fb_assigned"))
    unassigned = f(rec.get("gf_unassigned")) if rec.get("gf_unassigned") not in (None,"") else f(rec.get("fb_unassigned"))
    committed = f(rec.get("fb_committed"))
    vals = [x for x in (committed, assigned, unassigned) if x is not None]
    return sum(vals) if vals else None

# ----------------------------------------------------------------------------- compute per row
OUT_FIELDS = ["district","fiscal_year","data_basis","peer_group",
  # cash & liquidity
  "days_net_cash","moodys_net_cash_ratio","current_ratio","receivables_inventory_ratio","creditor_equity_ratio",
  # reserves
  "solvency_ratio","moodys_avail_fb_ratio","sp_available_reserves_pct","unrestricted_np_pp",
  # authority
  "uab_pct_of_max","ubr_unrestricted_pct",
  # operating
  "operating_margin","sp_oper_result_3yr","employee_cost_ratio","foundation_aid_ratio",
  "transportation_ratio","investment_income_ratio","gf_per_pupil","local_share_pct",
  # leverage
  "moodys_ltl_ratio","moodys_fixed_costs_ratio","sp_current_cost_pct","net_direct_debt_pp","npl_pp","debt_per_pupil",
  # economy & base
  "enrollment_cagr_3yr","valuation_per_pupil","grand_total_levy_rate","certified_enrollment",
  # quality
  "opinion_type","findings_count","repeat_finding","report_lag_months","gfoa_award",
  # provenance
  "confidence","sources"]

PEER_GROUP = {  # by FY2023-ish certified enrollment band, for fair benchmarking
 "Des Moines Independent CSD":"Large (>14k)","Cedar Rapids CSD":"Large (>14k)","Iowa City CSD":"Large (>14k)",
 "Davenport CSD":"Mid (7-14k)","Ankeny CSD":"Mid (7-14k)","Waukee CSD":"Mid (7-14k)","Dubuque CSD":"Mid (7-14k)",
 "Johnston CSD":"Small-mid (3-7k)","Linn-Mar CSD":"Small-mid (3-7k)","Waterloo CSD":"Mid (7-14k)",
 "West Des Moines CSD":"Small-mid (3-7k)","College CSD (Prairie)":"Small-mid (3-7k)",
 "Pleasant Valley CSD":"Small-mid (3-7k)","Muscatine CSD":"Small-mid (3-7k)","Burlington CSD":"Small-mid (3-7k)"}

def avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs)/len(xs) if xs else None

def compute():
    out = []
    for d in DISTRICTS:
        for fy in YEARS:
            rec = base.get((d, fy))
            if not rec: continue
            vb = ICCSD_VERBATIM.get((d, fy))
            row = {"district": d, "fiscal_year": fy, "peer_group": PEER_GROUP.get(d, "")}
            sources = []

            gf_rev = f(rec.get("gf_revenue")); gf_exp = f(rec.get("gf_expenditure"))
            cash = f(rec.get("gf_cash")); enr = enrollment(d, fy)   # GF cash only (not all-funds)
            row["certified_enrollment"] = round(enr, 1) if enr else ""
            row["data_basis"] = rec.get("data_basis", "audited")

            # ---------- 1. Cash & Liquidity ----------
            if vb:  # ICCSD published values win for FY15-19
                row["days_net_cash"] = vb["days_net_cash"]
                row["current_ratio"] = vb["current_ratio_pct"]
                row["creditor_equity_ratio"] = vb["creditor_equity_pct"]
            else:
                if cash is not None and gf_exp:
                    row["days_net_cash"] = round(cash / (gf_exp/365), 1)
                ca = f(rec.get("gf_current_assets"))
                cl = f(rec.get("gf_current_liabilities")); di = f(rec.get("gf_deferred_inflows")) or 0
                if ca is not None and cl is not None and (cl+di) > 0:
                    row["current_ratio"] = round(100*ca/(cl+di), 1)
                isc = f(rec.get("iscap_restricted"))
                if isc is not None and ca:
                    row["creditor_equity_ratio"] = round(100*isc/ca, 2)
            # Receivables & Inventory: ALWAYS computed from total GF receivables for a single
            # consistent definition across years/districts (the district's published ratio uses a
            # narrower receivables figure that excludes the succeeding-year property-tax receivable).
            ca2 = f(rec.get("gf_current_assets")); rcv = f(rec.get("gf_receivables")); inv = f(rec.get("gf_inventory")) or 0
            if rcv is not None and ca2:
                row["receivables_inventory_ratio"] = round(100*(rcv+inv)/ca2, 2)
            # Moody's net cash ratio (cash / operating revenue) -- always computable from backbone
            if cash is not None and gf_rev:
                row["moodys_net_cash_ratio"] = round(100*cash/gf_rev, 1)

            # ---------- 2. Reserves & Fund Balance ----------
            aea = f(rec.get("aea_flowthrough"))
            assigned = f(rec.get("gf_assigned"));
            if assigned is None: assigned = f(rec.get("fb_assigned"))
            unassigned = f(rec.get("gf_unassigned"))
            if unassigned is None: unassigned = f(rec.get("fb_unassigned"))
            if vb:
                row["solvency_ratio"] = vb["solvency_pct"]
            elif assigned is not None and unassigned is not None and gf_rev:
                denom = gf_rev - (aea or 0)
                if denom: row["solvency_ratio"] = round(100*(assigned+unassigned)/denom, 2)
            afb = available_fb(rec)
            if afb is not None and gf_rev:
                row["moodys_avail_fb_ratio"] = round(100*afb/gf_rev, 1)
                row["sp_available_reserves_pct"] = round(100*afb/gf_rev, 1)
            unp = f(rec.get("unrestricted_np"))
            if unp is not None and enr:
                row["unrestricted_np_pp"] = round(unp/enr)

            # ---------- 3. Spending Authority ----------
            if rec.get("uab_pct_of_max") not in (None, ""):
                row["uab_pct_of_max"] = round(f(rec["uab_pct_of_max"]), 2)
            elif vb:  # FY15-19: ICCSD's published Total Unspent Balance Ratio (same concept as DOM UAB %)
                row["uab_pct_of_max"] = vb["ubr_total_pct"]
            if vb:
                row["ubr_unrestricted_pct"] = vb["ubr_unrestricted_pct"]

            # ---------- 4. Operating Performance ----------
            if gf_rev and gf_exp is not None:
                row["operating_margin"] = round(100*(gf_rev-gf_exp)/gf_rev, 2)
            sal = f(rec.get("salaries_benefits"))
            if vb:
                row["employee_cost_ratio"] = vb["employee_cost_pct"]
                row["foundation_aid_ratio"] = vb["foundation_aid_pct"]
                row["transportation_ratio"] = vb["transportation_pct"]
                row["investment_income_ratio"] = vb["investment_income_pct"]
                row["gf_per_pupil"] = vb["gf_per_pupil"]
            else:
                if sal is not None and gf_exp:
                    row["employee_cost_ratio"] = round(100*sal/gf_exp, 1)
                # foundation aid: extraction state_aid_direct, else CAR genstateaid (FY17-23)
                sa = f(rec.get("state_aid_direct")) or car_stateaid(d, fy)
                if sa is not None and gf_rev:
                    row["foundation_aid_ratio"] = round(100*sa/gf_rev, 1)
                tr = car_transp(d, fy) or f(rec.get("transportation_exp"))
                if tr is not None and gf_exp:
                    row["transportation_ratio"] = round(100*tr/gf_exp, 2)
                # interest income: extraction, else CAR genint (FY17-23)
                ii = f(rec.get("interest_income"))
                if ii is None: ii = car_interest(d, fy)
                if ii is not None and gf_rev:
                    row["investment_income_ratio"] = round(100*ii/gf_rev, 3)
                if gf_exp and enr:
                    row["gf_per_pupil"] = round(gf_exp/enr)
            # local revenue share from CAR (FY17-23)
            ls = car_local_share(d, fy)
            if ls is None and rec.get("local_share_direct"):
                ls = f(rec["local_share_direct"]) / 100
            if ls is not None:
                row["local_share_pct"] = round(100*ls, 1)

            # ---------- 5. Leverage & Debt ----------
            debt = debt_total(rec); npl = f(rec.get("ipers_npl")); opeb = f(rec.get("opeb_liability"))
            if debt is not None and enr:
                row["debt_per_pupil"] = round(debt/enr)
                row["net_direct_debt_pp"] = round(debt/enr)
            if npl is not None and enr:
                row["npl_pp"] = round(npl/enr)
            if debt is not None and gf_rev:
                ll = debt + (npl or 0) + (opeb or 0)
                row["moodys_ltl_ratio"] = round(100*ll/gf_rev, 1)
            # Moody's fixed-costs: implied debt service (prior-yr debt) + pension cost + OPEB contribution
            prev = base.get((d, fy-1)); prev_debt = debt_total(prev) if prev else None
            if prev_debt is None: prev_debt = debt  # fall back to current if prior missing
            pens = f(rec.get("pension_contribution")); opebc = f(rec.get("opeb_contribution"))
            if prev_debt is not None and gf_rev and pens is not None:
                implied_ds = prev_debt / AMORT_DIVISOR
                row["moodys_fixed_costs_ratio"] = round(100*(implied_ds + pens + (opebc or 0))/gf_rev, 1)
            # S&P current cost: actual debt service + pension contrib + OPEB contrib / total govt revenue
            ads = f(rec.get("annual_debt_service"))
            if ads is not None and pens is not None and gf_rev:
                row["sp_current_cost_pct"] = round(100*(ads + pens + (opebc or 0))/gf_rev, 1)

            # ---------- 6. Economy & Tax Base ----------
            e0 = enrollment(d, fy); e3 = enrollment(d, fy-3)
            if e0 and e3 and e3 > 0:
                row["enrollment_cagr_3yr"] = round(100*((e0/e3)**(1/3) - 1), 2)
            val = f(rec.get("taxable_valuation"))
            if val is not None and enr:
                row["valuation_per_pupil"] = round(val/enr)
            if rec.get("grand_total_rate") not in (None, ""):
                row["grand_total_levy_rate"] = round(f(rec["grand_total_rate"]), 2)

            # ---------- 7. Reporting Quality & Framework ----------
            row["opinion_type"] = rec.get("opinion_type", "")
            row["findings_count"] = rec.get("findings_count", "")
            row["repeat_finding"] = rec.get("repeat_finding", "")
            row["gfoa_award"] = rec.get("gfoa_cert", "")
            rd = rec.get("report_date")
            if rd and len(str(rd)) >= 7:
                try:
                    y, m = int(str(rd)[:4]), int(str(rd)[5:7])
                    row["report_lag_months"] = (y - fy)*12 + (m - 6)
                except Exception: pass

            # provenance
            conf = rec.get("extract_confidence")
            row["confidence"] = ("verbatim-district" if vb else (conf or ("audited" if row["data_basis"]=="audited" else row["data_basis"])))
            out.append(row)
    return out

def sp_oper_3yr(out):
    """3-yr avg operating result needs the 3 prior single-year margins; fill after the pass."""
    by = {(r["district"], int(r["fiscal_year"])): r for r in out}
    for r in out:
        d, fy = r["district"], int(r["fiscal_year"])
        ms = [by.get((d, y), {}).get("operating_margin") for y in (fy-2, fy-1, fy)]
        ms = [f(m) for m in ms if m not in (None, "")]
        if len(ms) == 3:
            r["sp_oper_result_3yr"] = round(sum(ms)/3, 2)

def main():
    out = compute()
    sp_oper_3yr(out)
    out.sort(key=lambda r: (DISTRICTS.index(r["district"]), int(r["fiscal_year"])))
    with open(p("data/kpi-three-methodologies.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in out:
            r.setdefault("sources", "")
            w.writerow(r)
    # coverage report
    filled = defaultdict(int); total = len(out)
    for r in out:
        for k in OUT_FIELDS:
            if r.get(k) not in (None, ""): filled[k] += 1
    print(f"Wrote data/kpi-three-methodologies.csv: {total} district-year rows")
    print("Coverage by KPI (non-blank rows):")
    for k in OUT_FIELDS:
        if k in ("district","fiscal_year","peer_group","data_basis","confidence","sources"): continue
        print(f"  {k:28} {filled[k]:3}/{total}")

if __name__ == "__main__":
    main()
