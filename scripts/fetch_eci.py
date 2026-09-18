#!/usr/bin/env python3
"""
BLS Employment Cost Index -> data/labor/eci.csv: the market price of school labor.

Why this exists alongside CPI. The two deflators answer different questions, and using
the wrong one inverts the conclusion:

  CPI-U  "Did this cost taxpayers more in real terms?"  -- what a dollar buys a
         household. Right for spending per student.
  ECI    "Did the district pay more than the going rate for staff?" -- what employers
         actually pay for labor. Right for cost per staff member.

The series used is CIS3016110000000I: total compensation for STATE AND LOCAL
GOVERNMENT workers in the ELEMENTARY AND SECONDARY SCHOOLS industry -- i.e. exactly
the market a public school district hires in, benefits included. It is national;
BLS does not publish a district- or Iowa-level cut.

Quarterly, indexed. Q2 of each year is taken because Iowa's fiscal year ends June 30,
so Q2 is the matching point rather than an annual average straddling two fiscal years.

Over FY2005-FY2025 this index rose about 74% against CPI-U's 65% -- school labor got
more expensive faster than consumer goods did. Deflating pay by CPI therefore
UNDERSTATES how much ground a district's pay lost against its own labor market.

Run:  python3 scripts/fetch_eci.py   ->  data/labor/eci.csv
"""
import csv, os, ssl, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "labor", "eci.csv")
URL = "https://download.bls.gov/pub/time.series/ci/ci.data.1.AllData"
SERIES, PERIOD = "CIS3016110000000I", "Q02"     # Q2 ~ Iowa's June 30 fiscal year end
YEARS = range(2005, 2026)


def main():
    ctx = ssl.create_default_context()
    bundle = "/root/.ccr/ca-bundle.crt"
    if os.path.exists(bundle):
        ctx.load_verify_locations(bundle)
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (ICCSD finance analysis; michael@480th.com)"})
    with urllib.request.urlopen(req, timeout=240, context=ctx) as r:
        text = r.read().decode("utf8", "ignore")

    vals = {}
    for line in text.splitlines()[1:]:
        p = line.split()
        if len(p) >= 4 and p[0] == SERIES and p[2] == PERIOD:
            try:
                vals[int(p[1])] = float(p[3])
            except ValueError:
                continue

    missing = [y for y in YEARS if y not in vals]
    if missing:
        sys.exit(f"ECI missing for {missing} -- BLS file format may have changed")

    base = vals[max(YEARS)]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fiscal_year", "eci_k12_q2", f"deflator_to_{max(YEARS)}"])
        for y in YEARS:
            w.writerow([y, vals[y], round(base / vals[y], 6)])
    print(f"-> {os.path.relpath(OUT, ROOT)}  ({min(YEARS)}={vals[min(YEARS)]}, "
          f"{max(YEARS)}={base}; school-labor cost up "
          f"{base / vals[min(YEARS)] * 100 - 100:.0f}%)")


if __name__ == "__main__":
    main()
