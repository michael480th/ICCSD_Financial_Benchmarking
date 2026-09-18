#!/usr/bin/env python3
"""
Iowa City CSD salaries + benefits by FUNCTION from the Iowa DE's Certified Annual
Report (CAR) workbooks, FY2019-FY2025 -> data/labor/car-iccsd.csv.

This is the district's own filing to the state, and it carries the full
function x object matrix that audited ACFRs don't. It serves two jobs here:

  1. Extends the labor series past FY2023, where the Census F-33 stops.
  2. Independently checks F-33 on FY2019-FY2023, where both exist. Census reprocesses
     Iowa's filing, so the two should be close but need not be identical -- the
     comparison is published on the page rather than resolved silently.

Each workbook holds one "<Fund>ExpData1" sheet per fund: districts as rows (row 3 is
the header, column 2 the district number -- ICCSD is 3141), columns named
<FunctionPrefix><Object>, e.g. InstSal / InstBen / SchAdSal.

Fund selection matters. Only OPERATING funds count as labor here, to match the F-33's
"current spending" basis:
  - General carries the bulk.
  - Management is benefits-only (early retirement, unemployment, insurance) and IS
    labor cost -- ~$9M a year that a General-Fund-only view would miss entirely.
  - Nutrition and Trust carry small payrolls.
  - SAVE/PPEL/CapProj/Debt are excluded: capital and debt, which the F-33 codes
    outside current spending. SAVE does carry ~$0.6M of construction-management
    salary; leaving it in would break comparability with the pre-FY2024 series.

Self-check: FY2025 is reconciled against the district's own certified CAR, extracted
to CAR/FY25 CAR Iowa City/. That file is ALL FUNDS (not General Fund, despite what the
General-Fund-looking layout suggests) -- salaries reconcile to the dollar once SAVE's
construction-management payroll is added back to the operating-fund figure here.

Run:  python3 scripts/fetch_car_labor.py   ->  data/labor/car-iccsd.csv
                                               data/labor/car-data-quality.csv
"""
import csv, os, ssl, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "labor", "car-iccsd.csv")
QUALITY = os.path.join(ROOT, "data", "labor", "car-data-quality.csv")
ANCHOR = os.path.join(ROOT, "CAR", "FY25 CAR Iowa City",
                      "FY25_IowaCity_04_expenditures_by_function_object.csv")
CACHE = os.path.join(ROOT, "CAR")
ICCSD = 3141

# Iowa DE publishes these as /media/<id>/download. Cached locally; large (~9MB each).
WORKBOOKS = {
    2019: ("13478", "2018_2019 CAR data.xlsx"),
    2020: ("13479", "2019_2020 CAR data.xlsx"),
    2021: ("13480", "2020_2021 CAR data.xlsx"),
    2022: ("13481", "2021_2022 CAR data.xlsx"),
    2023: (None,    "2022_2023 CAR data-for website.xlsx"),      # already in repo
    2024: (None,    "2023_2024 CAR data-for website (1).xlsx"),  # already in repo
    2025: ("13326", "2024_2025 CAR data.xlsx"),
}
MEDIA = "https://educate.iowa.gov/media/{mid}/download"

# Operating funds only -- see the module docstring on why capital/debt are excluded.
# Sheet names drift between vintages, so match on a stem rather than an exact name:
# FY2025 appends fund numbers ("GenExpData1fund10", "MgmntExpData1-fund22") and the
# nutrition fund was renamed from "Lunch" to "Nutrition" partway through the series.
OPERATING_STEMS = [
    "GenExp", "MgmntExp", "NutritionExp", "LunchExp", "ActExp", "PERLExp",
    "EntreExp", "LibExp", "SuppTrustExp", "TrustExp", "CustodialExp",
    "InternalServ", "DisastRecovExp", "NonFidSch", "OthEntExp",
]
# Capital and debt: outside the F-33's "current spending" basis. SAVE does carry
# ~$0.6M of construction-management salary, which is exactly why it must be dropped --
# including it would break comparability with the pre-FY2024 half of the series.
# AEA funds (25/26) are area-education-agency flowthrough, not district payroll.
EXCLUDED_STEMS = ["SAVEExp", "PPELExp", "CapProj", "DebtExp", "PermExp",
                  "AEASEInst", "AEAJHInst", "BalSheet", "Rev"]


def operating_sheets(sheet_names):
    """Pick the operating-expenditure data sheets out of a workbook, tolerating the
    fund-number suffixes and renames that differ between vintages."""
    chosen = []
    for name in sheet_names:
        stem = name.split("Data1")[0]
        if "Data1" not in name or any(stem.startswith(x) for x in EXCLUDED_STEMS):
            continue
        if any(stem == s for s in OPERATING_STEMS):
            chosen.append(name)
    return chosen

# Iowa CAR function prefixes rolled up to the same categories fetch_f33_labor.py uses,
# so the two sources stack into one series.
CATEGORY_FUNCTIONS = {
    "instruction":            ["Inst"],
    "pupil_support":          ["AttendSoc", "Guid", "Heal", "Psych", "Spch", "OT",
                               "PT", "Vis", "OthStud"],
    "instr_staff_support":    ["ImpInst", "Lib", "Tech", "Ass", "OthInstSupp"],
    "general_admin":          ["Bd", "Admin", "SpAd"],
    "school_admin":           ["SchAd"],
    "business_central_other": ["BusAd", "Ware", "Print", "PR", "PInfo", "Pers",
                               "ATech", "OthBA", "OthSupp"],
    "oper_maint":             ["OpMaint"],
    "transportation":         ["Trans"],
    "food_service":           ["FS"],
    "other_unallocated":      ["OthEnt", "CommServ", "Fac", "Flow", "Out", "Spec",
                               "Extra", "LossD", "Adj", "Debt"],
}
CATEGORIES = list(CATEGORY_FUNCTIONS)


def fetch(mid, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    if mid is None:
        sys.exit(f"missing expected in-repo workbook: {dest}")
    ctx = ssl.create_default_context()
    bundle = "/root/.ccr/ca-bundle.crt"
    if os.path.exists(bundle):
        ctx.load_verify_locations(bundle)
    req = urllib.request.Request(MEDIA.format(mid=mid),
                                 headers={"User-Agent": "Mozilla/5.0"})
    print(f"  downloading {os.path.basename(dest)} ...")
    with urllib.request.urlopen(req, timeout=300, context=ctx) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def verify_fy25(pd, path, operating_sal, operating_ben):
    """Reconcile the FY2025 operating-fund figures against the district's own certified
    CAR. That document totals ALL funds, so SAVE payroll -- excluded upstream as
    capital -- has to be added back before the two can be compared."""
    if not os.path.exists(ANCHOR):
        return [("2025", "anchor_missing", os.path.relpath(ANCHOR, ROOT))]
    d = pd.read_csv(ANCHOR)
    d.columns = [c.strip() for c in d.columns]
    total = d[d["Line"] == 42].iloc[0]
    want_s = float(pd.to_numeric(total["Salaries"], errors="coerce") or 0)
    want_b = float(pd.to_numeric(total["Employee Benefits"], errors="coerce") or 0)

    xl = pd.ExcelFile(path)
    save = [s for s in xl.sheet_names if s.split("Data1")[0] == "SAVEExp"]
    save_s = save_b = 0.0
    if save:
        df = pd.read_excel(path, sheet_name=save[0], header=None)
        hdr = [str(h).strip() for h in df.iloc[2].tolist()]
        hit = df[pd.to_numeric(df.iloc[:, 1], errors="coerce") == ICCSD]
        if not hit.empty:
            r = hit.iloc[0]
            for col, add in (("TotSal", "s"), ("TotBen", "b")):
                v = pd.to_numeric(r.iloc[hdr.index(col)], errors="coerce")
                v = 0.0 if pd.isna(v) else float(v)
                if add == "s":
                    save_s = v
                else:
                    save_b = v

    got_s, got_b = operating_sal + save_s, operating_ben + save_b
    out = []
    for label, got, want in (("salaries", got_s, want_s), ("benefits", got_b, want_b)):
        delta = got - want
        ok = abs(delta) < 1
        out.append(("2025", f"fy25_anchor_{label}",
                    f"{'OK' if ok else 'MISMATCH'}: operating+SAVE {got:,.2f} vs "
                    f"district CAR {want:,.2f} (delta {delta:+,.2f})"))
        print(f"  FY25 anchor {label}: {'OK' if ok else 'MISMATCH'} "
              f"({got:,.0f} vs {want:,.0f}, delta {delta:+,.0f})")
    return out


def main():
    try:
        import pandas as pd
    except ImportError:
        sys.exit("pandas required:  pip install pandas openpyxl")

    rows, issues = [], []
    for fy, (mid, fname) in sorted(WORKBOOKS.items()):
        path = fetch(mid, os.path.join(CACHE, fname))
        xl = pd.ExcelFile(path)
        rec = {"fiscal_year": fy, "source": "iowa_de_car", "source_file": fname}
        totals = {c: {"sal": 0.0, "ben": 0.0} for c in CATEGORIES}
        fund_detail, grand_s, grand_b = [], 0.0, 0.0

        sheets = operating_sheets(xl.sheet_names)
        if not sheets:
            sys.exit(f"FY{fy}: no operating expenditure sheets matched in {fname}")
        for sheet in sheets:
            df = pd.read_excel(path, sheet_name=sheet, header=None)
            hdr = [str(h).strip() for h in df.iloc[2].tolist()]
            hit = df[pd.to_numeric(df.iloc[:, 1], errors="coerce") == ICCSD]
            if hit.empty:
                continue
            row = hit.iloc[0]

            def cell(col):
                if col not in hdr:
                    return 0.0
                v = pd.to_numeric(row.iloc[hdr.index(col)], errors="coerce")
                return 0.0 if pd.isna(v) else float(v)

            fs = fb = 0.0
            for cat, prefixes in CATEGORY_FUNCTIONS.items():
                s = sum(cell(p + "Sal") for p in prefixes)
                b = sum(cell(p + "Ben") for p in prefixes)
                totals[cat]["sal"] += s
                totals[cat]["ben"] += b
                fs += s
                fb += b

            # The sheet's own TotSal/TotBen is the authoritative fund total; if our
            # function roll-up misses it, a function prefix is unmapped.
            ts, tb = cell("TotSal"), cell("TotBen")
            if abs(fs - ts) > 1 or abs(fb - tb) > 1:
                print(f"  FY{fy} {sheet}: roll-up {fs:,.0f}/{fb:,.0f} != "
                      f"sheet total {ts:,.0f}/{tb:,.0f} -- unmapped function?",
                      file=sys.stderr)
            grand_s += ts
            grand_b += tb
            if ts or tb:
                fund_detail.append(f"{sheet.split('Data1')[0]}:{ts + tb:,.0f}")

        for cat in CATEGORIES:
            s, b = totals[cat]["sal"], totals[cat]["ben"]
            rec[f"{cat}_salaries"], rec[f"{cat}_benefits"] = round(s), round(b)
            rec[f"{cat}_labor"] = round(s + b)
        rec["total_salaries"], rec["total_benefits"] = round(grand_s), round(grand_b)
        rec["total_labor"] = round(grand_s + grand_b)
        rec["funds_included"] = " ".join(fund_detail)
        rows.append(rec)
        print(f"FY{fy}  labor ${rec['total_labor']/1e6:7.1f}M   "
              f"(salaries ${grand_s/1e6:.1f}M + benefits ${grand_b/1e6:.1f}M)")
        if fy == 2025:
            issues += verify_fy25(pd, path, grand_s, grand_b)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(QUALITY, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fiscal_year", "check", "detail"])
        w.writerows(issues)
    print(f"\n-> {os.path.relpath(OUT, ROOT)}  ({len(rows)} years)")
    print(f"-> {os.path.relpath(QUALITY, ROOT)}")


if __name__ == "__main__":
    main()
