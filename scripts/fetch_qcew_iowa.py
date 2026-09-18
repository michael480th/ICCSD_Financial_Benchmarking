#!/usr/bin/env python3
"""
Iowa wages actually paid by public K-12 schools -> data/labor/qcew-iowa-k12.csv.

Source: BLS Quarterly Census of Employment and Wages -- a near-census of employers
covered by unemployment insurance, not a survey. Slice taken:
    area 19000 (Iowa statewide), ownership 3 (local government), NAICS 6111
    (elementary and secondary schools)
i.e. the wage bill of Iowa's public school districts, and Johnson County (19103) for
local context.

Why both this and the ECI (scripts/fetch_eci.py):

  ECI   national, but a true PRICE index -- fixed job weights, so it measures pay for
        the same work over time, and it includes benefits.
  QCEW  Iowa-specific and actual dollars paid, but WAGES ONLY (no benefits) and NOT
        mix-adjusted: a district that hires more paraeducators lowers its average wage
        without cutting anyone's pay.

Neither dominates. The ECI is the better price measure; QCEW is the better local one.
The page shows both and says which is which.

Johnson County is reported for context but is a weak benchmark for ICCSD specifically,
because ICCSD is most of the county's public-school employment -- the district would
largely be benchmarking against itself.

Coverage: the QCEW open-data API serves 2015 onward; earlier years come from the
annual bulk files (~74MB per year, downloaded then discarded, keeping only Iowa rows).

Run:  python3 scripts/fetch_qcew_iowa.py   ->  data/labor/qcew-iowa-k12.csv
"""
import csv, io, os, ssl, sys, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "labor", "qcew-iowa-k12.csv")
API = "https://data.bls.gov/cew/data/api/{y}/a/area/{area}.csv"
BULK = "https://data.bls.gov/cew/data/files/{y}/csv/{y}_annual_singlefile.zip"
AREAS = {"19000": "iowa", "19103": "johnson_county"}
OWN, NAICS = "3", "6111"                 # local government, elementary & secondary schools
YEARS = range(2005, 2026)
API_FROM = 2015
UA = {"User-Agent": "Mozilla/5.0 (ICCSD finance analysis; michael@480th.com)"}


def get(url, timeout=300):
    ctx = ssl.create_default_context()
    bundle = "/root/.ccr/ca-bundle.crt"
    if os.path.exists(bundle):
        ctx.load_verify_locations(bundle)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                timeout=timeout, context=ctx) as r:
        return r.read()


def pick(reader, out):
    """Collect the local-government K-12 row for each wanted area."""
    for row in reader:
        if len(row) < 15:
            continue
        area, own, ind = row[0].strip('"'), row[1].strip('"'), row[2].strip('"')
        if area in AREAS and own == OWN and ind == NAICS:
            try:
                out[AREAS[area]] = {"emp": float(row[9]), "wkly": float(row[13]),
                                    "annual_pay": float(row[14])}
            except ValueError:
                pass


def year_rows(y):
    out = {}
    if y >= API_FROM:
        for area in AREAS:
            txt = get(API.format(y=y, area=area)).decode("utf8", "ignore")
            pick(csv.reader(io.StringIO(txt)), out)
    else:
        blob = get(BULK.format(y=y), timeout=900)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            name = next(n for n in z.namelist() if n.endswith(".csv"))
            with z.open(name) as fh:
                pick(csv.reader(io.TextIOWrapper(fh, "utf8", errors="ignore")), out)
    return out


def main():
    rows = []
    for y in YEARS:
        try:
            d = year_rows(y)
        except Exception as e:                                   # noqa: BLE001
            print(f"  {y}: failed ({e})", file=sys.stderr)
            continue
        if "iowa" not in d:
            print(f"  {y}: no Iowa row", file=sys.stderr)
            continue
        rec = {"year": y}
        for k in AREAS.values():
            rec[f"{k}_emp"] = round(d.get(k, {}).get("emp", 0))
            rec[f"{k}_avg_annual_pay"] = round(d.get(k, {}).get("annual_pay", 0))
        rows.append(rec)
        print(f"  {y}  Iowa K-12: {rec['iowa_emp']:,} employees, "
              f"avg pay ${rec['iowa_avg_annual_pay']:,}")

    if not rows:
        sys.exit("no QCEW rows collected")
    base = rows[-1]["iowa_avg_annual_pay"]
    for r in rows:
        r["iowa_deflator_to_last"] = round(base / r["iowa_avg_annual_pay"], 6)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    a, b = rows[0], rows[-1]
    print(f"\n-> {os.path.relpath(OUT, ROOT)}  ({len(rows)} years)")
    print(f"   Iowa public K-12 average pay ${a['iowa_avg_annual_pay']:,} "
          f"-> ${b['iowa_avg_annual_pay']:,} "
          f"({b['iowa_avg_annual_pay'] / a['iowa_avg_annual_pay'] * 100 - 100:+.0f}%)")


if __name__ == "__main__":
    main()
