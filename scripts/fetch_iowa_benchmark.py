#!/usr/bin/env python3
"""
Iowa statewide cost per teacher, built EXACTLY as the ICCSD figure is
-> data/labor/iowa-benchmark.csv.

This is the most defensible Iowa-specific yardstick for "did ICCSD outpay its market,"
and it beats a generic deflator on three counts:

  1. Iowa-specific -- not a national index standing in for Iowa.
  2. Identical construction -- same numerator definition (instruction salaries plus
     benefits, from the same filings) and same denominator (CCD teacher FTE, with
     paraeducator FTE weighted by the same PARA_PAY_RATIO). Whatever bias the
     construction carries, it cancels in the comparison.
  3. Includes benefits, which a wage series such as QCEW does not, and benefits grew
     faster than wages over this window.

ICCSD is about 3% of Iowa's public-school teaching workforce, so the state total is a
genuine external benchmark rather than the district measuring itself.

Sources, mirroring the main series:
  FY2005-FY2023  Census F-33, every Iowa district summed (cached by fetch_f33_labor.py)
  FY2024-FY2025  Iowa DE CAR workbooks, every district summed
  staff          NCES CCD, all Iowa districts (CCD year Y = fiscal year Y+1)

Run:  python3 scripts/fetch_iowa_benchmark.py  ->  data/labor/iowa-benchmark.csv
"""
import csv, json, os, ssl, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "labor", "iowa-benchmark.csv")
F33_CACHE = os.path.join(ROOT, "CAR", "_f33_cache")
CAR_DIR = os.path.join(ROOT, "CAR")
API = ("https://educationdata.urban.org/api/v1/school-districts/ccd/directory"
       "/{y}/?fips=19")
FIRST, LAST, SPLICE = 2005, 2025, 2023
PARA_PAY_RATIO = 0.40                      # must match build_labor_waterfall.py
CAR_FILES = {2024: "2023_2024 CAR data-for website (1).xlsx",
             2025: "2024_2025 CAR data.xlsx"}
UA = {"User-Agent": "Mozilla/5.0 (ICCSD finance analysis; michael@480th.com)"}


def get_json(url):
    ctx = ssl.create_default_context()
    bundle = "/root/.ccr/ca-bundle.crt"
    if os.path.exists(bundle):
        ctx.load_verify_locations(bundle)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                timeout=180, context=ctx) as r:
        return json.loads(r.read())


def iowa_staff(fy):
    """Sum teacher and aide FTE across every Iowa district. CCD year = fy - 1."""
    url, t, a = API.format(y=fy - 1), 0.0, 0.0
    while url:
        d = get_json(url)
        for r in d["results"]:
            for key, acc in (("teachers_total_fte", "t"), ("instructional_aides_fte", "a")):
                v = r.get(key)
                if v and v > 0:                      # negatives are CCD missing-sentinels
                    if acc == "t":
                        t += v
                    else:
                        a += v
        url = d.get("next")
    return t, a


def iowa_instruction(fy, pd):
    """Iowa-wide instruction salaries + benefits, from whichever source covers fy."""
    if fy <= SPLICE:
        yy = f"{fy % 100:02d}"
        path = next((os.path.join(F33_CACHE, f"elsec{yy}.{e}")
                     for e in ("xlsx", "xls")
                     if os.path.exists(os.path.join(F33_CACHE, f"elsec{yy}.{e}"))), None)
        if not path:
            sys.exit(f"FY{fy}: F-33 cache missing -- run scripts/fetch_f33_labor.py first")
        df = pd.read_excel(path)
        df.columns = [str(c).strip().upper() for c in df.columns]
        # Select Iowa by the NCES district ID's leading FIPS digits, NOT the STATE
        # column: older F-33 vintages carry no FIPST, and their STATE column is a
        # sequential alphabetical code in which 19 is Louisiana, not Iowa.
        def fips(v):
            """Leading 2 digits of the NCES district ID. Vintages vary: some store it
            as a float (1914700.0), some as a padded string that may contain letters
            ("06D0001"), so normalise rather than assume a numeric type."""
            if pd.isna(v):
                return ""
            t = str(v).strip()
            if t.replace(".", "", 1).isdigit():
                t = str(int(float(t)))
            return t.zfill(7)[:2]

        nces = df["NCESID"].apply(fips)
        ia = df[nces == "19"]
        # Published in thousands; negatives are missing-value sentinels.
        sal = pd.to_numeric(ia["Z33"], errors="coerce").clip(lower=0).sum() * 1000
        ben = pd.to_numeric(ia["V10"], errors="coerce").clip(lower=0).sum() * 1000
        return float(sal + ben), "Census F-33"

    path = os.path.join(CAR_DIR, CAR_FILES[fy])
    if not os.path.exists(path):
        sys.exit(f"FY{fy}: {path} missing -- run scripts/fetch_car_labor.py first")
    xl = pd.ExcelFile(path)
    total = 0.0
    for sheet in xl.sheet_names:
        stem = sheet.split("Data1")[0]
        if "Data1" not in sheet or stem not in (
                "GenExp", "MgmntExp", "NutritionExp", "LunchExp", "ActExp", "PERLExp",
                "EntreExp", "LibExp", "SuppTrustExp", "TrustExp", "CustodialExp",
                "InternalServ", "DisastRecovExp", "NonFidSch", "OthEntExp"):
            continue
        df = pd.read_excel(path, sheet_name=sheet, header=None)
        hdr = [str(h).strip() for h in df.iloc[2].tolist()]
        if "InstSal" not in hdr:
            continue
        body = df.iloc[3:]
        # Each sheet ends with "LEA Total", "AEA Total" and "LEA/AEA Total" rows, which
        # have no district number. Summing them alongside the districts triples the
        # state figure. Keep only real districts, and drop AEA rows (codes >= 9000)
        # so the total matches the F-33's district-only basis.
        code = pd.to_numeric(body.iloc[:, 1], errors="coerce")
        districts = body[code.notna() & (code < 9000)]
        for col in ("InstSal", "InstBen"):
            total += pd.to_numeric(districts.iloc[:, hdr.index(col)],
                                   errors="coerce").fillna(0).sum()
    return float(total), "Iowa DE CAR"


def main():
    try:
        import pandas as pd
    except ImportError:
        sys.exit("pandas required")

    rows = []
    for fy in range(FIRST, LAST + 1):
        instr, src = iowa_instruction(fy, pd)
        t, a = iowa_staff(fy)
        # Same teacher-equivalent denominator as the ICCSD figure.
        per_teacher = instr / (t + PARA_PAY_RATIO * a)
        rows.append({"fiscal_year": fy, "source": src,
                     "instruction_labor": round(instr),
                     "teacher_fte": round(t, 1), "aide_fte": round(a, 1),
                     "cost_per_teacher": round(per_teacher)})
        print(f"FY{fy}  Iowa instruction ${instr/1e9:5.2f}B  teachers {t:>7,.0f}  "
              f"cost/teacher ${per_teacher:>8,.0f}   [{src}]")

    base = rows[-1]["cost_per_teacher"]
    for r in rows:
        r["deflator_to_last"] = round(base / r["cost_per_teacher"], 6)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    a0, b0 = rows[0], rows[-1]
    print(f"\n-> {os.path.relpath(OUT, ROOT)}  ({len(rows)} years)")
    print(f"   Iowa cost per teacher ${a0['cost_per_teacher']:,} -> "
          f"${b0['cost_per_teacher']:,} "
          f"({b0['cost_per_teacher'] / a0['cost_per_teacher'] * 100 - 100:+.0f}%)")


if __name__ == "__main__":
    main()
