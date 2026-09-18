#!/usr/bin/env python3
"""
Iowa City CSD staff counts (FTE) by role, FY2005-FY2025 -> data/labor/staff-fte.csv.

Source: NCES Common Core of Data (CCD) local-education-agency universe, served through
the Urban Institute's Education Data API (public, no key). The CCD is the federal
staffing census districts file each fall; it is the only series that separates
TEACHERS from INSTRUCTIONAL AIDES (paraeducators) over the full window.

That separation is the whole point of this file. Neither the Census F-33 nor the Iowa
CAR splits paraeducator pay out of "Instruction" -- both bury it with teacher salaries.
build_labor_waterfall.py uses these FTE counts to model the split.

Two alignment traps, both handled here:

  1. CCD is stamped with the FALL of the school year; Iowa's fiscal year ends the
     following June. So CCD year Y is fiscal year Y+1. Verified against enrollment:
     CCD 2005 = 10,822 students = F-33 FY2006 exactly, and the same holds for all 19
     overlapping years. Getting this wrong would shift every staffing ratio by a year.
  2. CCD uses small NEGATIVE numbers as missing-data sentinels (-1 "missing",
     -2 "not applicable"). They are not counts. They are nulled here and linearly
     interpolated across interior gaps only -- never extrapolated past the ends.

Also note two visible reporting discontinuities in ICCSD's own filings -- aides drop
~100 FTE at FY2011 and school administrators roughly double at FY2022 -- which look
like changes in how roles were coded rather than real hiring. They are flagged to
data/labor/staff-data-quality.csv so the modeled split can be read with that in mind.

Run:  python3 scripts/fetch_staff_fte.py   ->  data/labor/staff-fte.csv
"""
import csv, json, os, ssl, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "labor", "staff-fte.csv")
API = ("https://educationdata.urban.org/api/v1/school-districts/ccd/directory"
       "/{yr}/?leaid=1914700")
CCD_YEARS = range(2004, 2025)     # -> fiscal years 2005..2025
QUALITY = os.path.join(ROOT, "data", "labor", "staff-data-quality.csv")
# Year-over-year jump (as a multiple) above which a change is more likely a coding
# change than real hiring, and worth surfacing rather than silently modelling on.
JUMP_FLAG = 1.4

FIELDS = [
    "enrollment",
    "teachers_total_fte", "teachers_elementary_fte", "teachers_secondary_fte",
    "teachers_kindergarten_fte", "teachers_prek_fte",
    "instructional_aides_fte",
    "guidance_counselors_total_fte", "librarian_support_staff_fte",
    "school_administrators_fte", "school_admin_support_staff_fte",
    "lea_administrators_fte", "lea_admin_support_staff_fte",
    "support_staff_students_fte", "support_staff_other_fte",
    "staff_total_fte",
]


def get(url):
    ctx = ssl.create_default_context()
    bundle = "/root/.ccr/ca-bundle.crt"
    if os.path.exists(bundle):
        ctx.load_verify_locations(bundle)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
        return json.loads(r.read())


def clean(v):
    """CCD sentinels: negatives mean missing / not applicable, not zero."""
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if v < 0 else v


def interpolate(rows, field):
    """Fill interior gaps only. Leading/trailing gaps stay blank -- a missing count at
    the edge of the series is genuinely unknown, and guessing it would bias the
    endpoints the whole waterfall is measured between."""
    idx = [i for i, r in enumerate(rows) if r[field] is not None]
    if len(idx) < 2:
        return 0
    filled = 0
    for a, b in zip(idx, idx[1:]):
        if b - a == 1:
            continue
        ya, yb = rows[a][field], rows[b][field]
        for i in range(a + 1, b):
            rows[i][field] = round(ya + (yb - ya) * (i - a) / (b - a), 1)
            filled += 1
    return filled


def main():
    rows = []
    for ccd_year in CCD_YEARS:
        fy = ccd_year + 1                       # CCD is stamped with the fall; Iowa FY ends in June
        try:
            res = get(API.format(yr=ccd_year)).get("results", [])
        except Exception as e:                                  # noqa: BLE001
            print(f"FY{fy}: fetch failed ({e})", file=sys.stderr)
            res = []
        if not res:
            print(f"FY{fy} (CCD {ccd_year}): no record", file=sys.stderr)
            rows.append({"fiscal_year": fy, "ccd_year": ccd_year,
                         **{f: None for f in FIELDS}})
            continue
        rec = res[0]
        rows.append({"fiscal_year": fy, "ccd_year": ccd_year,
                     **{f: clean(rec.get(f)) for f in FIELDS}})

    for f in FIELDS:
        n = interpolate(rows, f)
        if n:
            print(f"  interpolated {n} interior gap(s) in {f}")

    # Surface step-changes that look like recoding rather than hiring.
    issues = []
    for f in ("teachers_total_fte", "instructional_aides_fte",
              "school_administrators_fte", "lea_administrators_fte"):
        for prev, cur in zip(rows, rows[1:]):
            a, b = prev[f], cur[f]
            if not a or not b:
                continue
            ratio = b / a
            if ratio >= JUMP_FLAG or ratio <= 1 / JUMP_FLAG:
                issues.append((cur["fiscal_year"], f, f"{a:,.0f} -> {b:,.0f} "
                               f"({(ratio - 1) * 100:+.0f}%) -- likely a coding change"))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["fiscal_year", "ccd_year"] + FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(QUALITY, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["fiscal_year", "field", "detail"])
        w.writerows(issues)

    print(f"\n{'FY':<6}{'teachers':>10}{'aides':>9}{'sch admin':>11}{'dist admin':>12}{'enroll':>9}")
    for r in rows:
        g = lambda k: f"{r[k]:,.0f}" if r[k] is not None else "--"      # noqa: E731
        print(f"{r['fiscal_year']:<6}{g('teachers_total_fte'):>10}{g('instructional_aides_fte'):>9}"
              f"{g('school_administrators_fte'):>11}{g('lea_administrators_fte'):>12}"
              f"{g('enrollment'):>9}")
    print(f"\n-> {os.path.relpath(OUT, ROOT)}  ({len(rows)} years)")
    print(f"-> {os.path.relpath(QUALITY, ROOT)}  ({len(issues)} discontinuities flagged)")
    for y, f, d in issues:
        print(f"   FY{y} {f}: {d}")


if __name__ == "__main__":
    main()
