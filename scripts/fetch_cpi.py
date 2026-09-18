#!/usr/bin/env python3
"""
CPI-U annual averages -> data/labor/cpi-u.csv, used to state the labor series in
constant dollars as well as nominal.

Source: BLS series CUUR0000SA0 (CPI for All Urban Consumers, U.S. city average, all
items, not seasonally adjusted), annual average period M13, pulled from the BLS flat
files. The public JSON API rejects unregistered callers, so the flat file is used.

A note on choice of deflator: CPI-U measures what a dollar buys a household, which is
the right lens for "did this cost taxpayers more in real terms." It is NOT a measure
of what school labor costs -- for that, BLS's Employment Cost Index for state and
local government compensation is the better yardstick, and it has run somewhat above
CPI over this period. Because the ECI is the larger deflator, an ECI-based series
would show LESS real growth than a CPI-based one. Using CPI-U therefore reports the
higher real-growth figure -- the less flattering one for the district -- which is the
appropriate direction to err and is stated as such on the page.

Run:  python3 scripts/fetch_cpi.py   ->  data/labor/cpi-u.csv
"""
import csv, os, ssl, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "labor", "cpi-u.csv")
URL = "https://download.bls.gov/pub/time.series/cu/cu.data.1.AllItems"
SERIES, PERIOD = "CUUR0000SA0", "M13"       # M13 = annual average
YEARS = range(2005, 2026)


def main():
    ctx = ssl.create_default_context()
    bundle = "/root/.ccr/ca-bundle.crt"
    if os.path.exists(bundle):
        ctx.load_verify_locations(bundle)
    # BLS blocks unidentified agents on the flat-file host.
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (ICCSD finance analysis; michael@480th.com)"})
    with urllib.request.urlopen(req, timeout=180, context=ctx) as r:
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
        sys.exit(f"CPI missing for {missing} -- BLS file format may have changed")

    base = vals[max(YEARS)]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "cpi_u_annual", f"deflator_to_{max(YEARS)}"])
        for y in YEARS:
            w.writerow([y, vals[y], round(base / vals[y], 6)])
    print(f"-> {os.path.relpath(OUT, ROOT)}  "
          f"({min(YEARS)}={vals[min(YEARS)]}, {max(YEARS)}={base}; "
          f"cumulative inflation {base / vals[min(YEARS)] * 100 - 100:.0f}%)")


if __name__ == "__main__":
    main()
