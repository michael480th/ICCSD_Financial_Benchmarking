#!/usr/bin/env python3
"""
Extract Iowa City CSD salaries + benefits by FUNCTION from the U.S. Census Bureau's
Annual Survey of School System Finances (the "F-33") -> data/labor/f33-iccsd.csv.

Why this source. Iowa audited ACFRs report expenditures by function only, so salaries
can't be separated from the rest of a function's spending -- the site README says as
much. The Iowa DE's CAR workbooks do carry the function x object matrix, but the DE
only publishes them back to FY2019. The F-33 carries both: Census collects Iowa's own
CAR filing and republishes it with salaries and employee benefits broken out per
function, every year back to FY1992. That is what makes a FY2005-FY2025 labor series
possible at all.

Caveats worth knowing:
  - Amounts in the published files are in THOUSANDS of dollars. Scaled on ingest.
  - ICCSD contracts out student transportation, so transport salaries are ~0 in the
    early years. Real, not missing -- but it means growth rates off that base blow up.
  - Census reprocesses the state filing, so figures can differ slightly from the DE's
    own CAR workbook. The overlap years are compared in build_labor_waterfall.py.

Run:  python3 scripts/fetch_f33_labor.py   ->  data/labor/f33-iccsd.csv
                                               data/labor/f33-data-quality.csv
"""
import csv, io, os, re, sys, urllib.request, ssl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "labor", "f33-iccsd.csv")
QUALITY = os.path.join(ROOT, "data", "labor", "f33-data-quality.csv")
CACHE = os.path.join(ROOT, "CAR", "_f33_cache")

BASE = ("https://www2.census.gov/programs-surveys/school-finances/tables"
        "/{yr}/secondary-education-finance/")
YEARS = range(2005, 2024)          # FY2005 .. FY2023 (latest published)
DISTRICT = "IOWA CITY COMM"        # NCESID 1914700; match on name (ID has leading zeros)

# (category, salary code, benefit code). Codes are the Census F-33 object-detail items.
CATEGORIES = [
    ("instruction",            ["Z33"], ["V10"]),
    ("pupil_support",          ["V11"], ["V12"]),
    ("instr_staff_support",    ["V13"], ["V14"]),
    ("general_admin",          ["V15"], ["V16"]),
    ("school_admin",           ["V17"], ["V18"]),
    ("business_central_other", ["V37"], ["V38"]),
    ("oper_maint",             ["V21"], ["V22"]),
    ("transportation",         ["V23"], ["V24"]),
    ("food_service",           ["V29"], ["V30"]),
]
# A tenth category, "other_unallocated", is derived below as the residual to the
# published totals -- it has no object codes of its own in the F-33.
TOTAL_SAL, TOTAL_BEN = "Z32", "Z34"
CONTEXT = {"enrollment": "V33", "total_current_spend": "TCURELSC"}


def fetch(url, dest):
    """Download to dest unless already cached. Returns bytes."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return open(dest, "rb").read()
    ctx = ssl.create_default_context()
    bundle = "/root/.ccr/ca-bundle.crt"
    if os.path.exists(bundle):
        ctx.load_verify_locations(bundle)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180, context=ctx) as r:
        data = r.read()
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    return data


def district_file(year):
    """Find the district-level workbook for a year. Filenames drift across years
    (elsec05.xls .. elsec23.xlsx), so read the directory index rather than guess."""
    idx = fetch(BASE.format(yr=year), os.path.join(CACHE, f"idx{year}.html")).decode(
        "utf8", "ignore")
    yy = f"{year % 100:02d}"
    # The plain district file is elsec<yy>.xls[x]; the *f / *t / *_sumtables variants
    # are the state-summary and per-pupil tables, which we don't want.
    for ext in ("xlsx", "xls"):
        if re.search(rf'elsec{yy}\.{ext}\b', idx):
            return f"elsec{yy}.{ext}"
    raise SystemExit(f"FY{year}: no district workbook found in the Census index")


def main():
    try:
        import pandas as pd
    except ImportError:
        sys.exit("pandas required:  pip install pandas openpyxl xlrd")

    rows, issues = [], []
    for year in YEARS:
        name = district_file(year)
        raw = fetch(BASE.format(yr=year) + name, os.path.join(CACHE, name))
        df = pd.read_excel(io.BytesIO(raw))
        df.columns = [str(c).strip().upper() for c in df.columns]

        hit = df[df["NAME"].astype(str).str.contains(DISTRICT, case=False, na=False)]
        if len(hit) != 1:
            issues.append((year, "district_match", f"{len(hit)} rows matched {DISTRICT!r}"))
            if len(hit) == 0:
                continue
        row = hit.iloc[0]

        def val(code):
            """F-33 uses negative sentinels for missing/not-applicable."""
            try:
                v = float(row[code])
            except (KeyError, TypeError, ValueError):
                issues.append((year, "missing_code", code))
                return 0.0
            return 0.0 if v < 0 else v * 1000.0        # published in thousands

        rec = {"fiscal_year": year, "source": "census_f33", "source_file": name}
        sal_sum = ben_sum = 0.0
        for cat, scodes, bcodes in CATEGORIES:
            s = sum(val(c) for c in scodes)
            b = sum(val(c) for c in bcodes)
            rec[f"{cat}_salaries"], rec[f"{cat}_benefits"] = round(s), round(b)
            rec[f"{cat}_labor"] = round(s + b)
            sal_sum += s
            ben_sum += b

        tot_s, tot_b = val(TOTAL_SAL), val(TOTAL_BEN)
        # The nine named functions don't fully reconstruct the published totals: F-33
        # folds "other support services" and enterprise/community-service staff into
        # Z32/Z34 without a separate object line. Carry that remainder explicitly as
        # its own category so the waterfall reconciles to the published total exactly
        # rather than quietly losing money. It runs ~2% of salaries in FY2005, <1% later.
        res_s, res_b = max(tot_s - sal_sum, 0.0), max(tot_b - ben_sum, 0.0)
        rec["other_unallocated_salaries"] = round(res_s)
        rec["other_unallocated_benefits"] = round(res_b)
        rec["other_unallocated_labor"] = round(res_s + res_b)

        rec["total_salaries"], rec["total_benefits"] = round(tot_s), round(tot_b)
        rec["total_labor"] = round(tot_s + tot_b)
        for k, code in CONTEXT.items():
            v = val(code)
            rec[k] = round(v / 1000) if k == "enrollment" else round(v)

        # Record the size of that remainder every year so a reader can see how much
        # of the series is unallocated, and flag it only if it grows large enough to
        # distort a category comparison.
        for label, res, whole in (("salaries", res_s, tot_s), ("benefits", res_b, tot_b)):
            if not whole:
                continue
            share = res / whole
            issues.append((year, f"{label}_unallocated_share", f"{share * 100:.1f}%"))
            if share > 0.05:
                issues.append((year, f"{label}_unallocated_large",
                               f"{res:,.0f} of {whole:,.0f} ({share * 100:.1f}%) sits "
                               f"outside the nine named functions"))
        rows.append(rec)
        print(f"FY{year}  labor ${rec['total_labor']/1e6:7.1f}M   "
              f"enrollment {rec['enrollment']:>6,}   [{name}]")

    if not rows:
        sys.exit("no rows extracted")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(QUALITY, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fiscal_year", "issue", "detail"])
        w.writerows(issues)

    print(f"\n-> {os.path.relpath(OUT, ROOT)}  ({len(rows)} years)")
    print(f"-> {os.path.relpath(QUALITY, ROOT)}  ({len(issues)} issues)")
    for y, k, d in issues[:15]:
        print(f"   FY{y} {k}: {d}")


if __name__ == "__main__":
    main()
