#!/usr/bin/env python3
"""
Build "Where did the money go?" (iccsd-labor-waterfall.html) -- a FY2005-FY2025
decomposition of Iowa City CSD's labor cost (salaries + employee benefits), set
against the growth in student headcount.

The question the page answers: labor is ~90% of what a school district spends, so
"where did spending grow?" is very nearly "which payrolls grew?" This splits two
decades of payroll growth into teachers, paraeducators, school support, school
administration, central administration and the rest, and asks how much of it is
explained by having more students.

Inputs (each produced by its own fetch script, each independently sourced):
  data/labor/f33-iccsd.csv   Census F-33, FY2005-FY2023  (salary/benefit by function)
  data/labor/car-iccsd.csv   Iowa DE CAR,  FY2019-FY2025  (extends past the F-33)
  data/labor/staff-fte.csv   NCES CCD,     FY2005-FY2025  (staff counts by role)
  data/labor/cpi-u.csv       BLS CPI-U                    (constant-dollar view)

Two deliberate adjustments, both visible on the page:

  1. SPLICE. F-33 carries FY2005-FY2023; CAR carries FY2024-FY2025. On the five
     overlapping years the two agree to within 0.6% on the total and essentially to
     the dollar on every named category, which is what justifies joining them.
  2. RESIDUAL. F-33 doesn't fully allocate salaries to its nine named functions --
     "other support services" and enterprise staff land in the totals without an
     object line. That remainder is spread pro-rata across the named categories so
     the two halves of the series sit on the same basis. Left alone it would show up
     as a phantom category that collapses at FY2024 purely because the source
     changed. It is under 1% of salaries in every year except FY2005 (2.2%).

Run:  python3 scripts/build_labor_waterfall.py  ->  iccsd-labor-waterfall.html
                                                    data/labor/labor-series.csv
"""
import csv, datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _nav import nav

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "labor")
OUT_HTML = os.path.join(ROOT, "iccsd-labor-waterfall.html")
OUT_CSV = os.path.join(D, "labor-series.csv")

FIRST, LAST, SPLICE = 2005, 2025, 2023        # CAR takes over after SPLICE

# Paraeducator pay as a share of teacher pay, used to split the Instruction function
# into teachers and paraeducators. Neither source reports that split. See the methods
# note on the page: the central case is 0.40 and the band is the sensitivity test.
PARA_PAY_RATIO = 0.40
PARA_RATIO_BAND = (0.30, 0.50)

# Source categories (identical names in both fetch scripts) -> display categories.
SOURCE_CATS = ["instruction", "pupil_support", "instr_staff_support", "general_admin",
               "school_admin", "business_central_other", "oper_maint",
               "transportation", "food_service", "other_unallocated"]
ALLOCATABLE = [c for c in SOURCE_CATS if c != "other_unallocated"]

# Short forms for the waterfall x-axis; the full names are used everywhere else.
SHORT = {"Student & staff support": "Student &\nstaff support",
         "School administration": "School\nadmin",
         "Central administration": "Central\nadmin",
         "Operations & maintenance": "Operations &\nmaintenance",
         "Paraeducators": "Para-\neducators"}

DISPLAY = [
    ("Teachers",                  "#2a78d6", True),
    ("Paraeducators",             "#eb6834", True),
    ("Student & staff support",   "#1baf7a", False),
    ("School administration",     "#eda100", False),
    ("Central administration",    "#e87ba4", False),
    ("Operations & maintenance",  "#008300", False),
    ("Food service",              "#4a3aa7", False),
    ("Transportation",            "#e34948", False),
]
LABELS = [d[0] for d in DISPLAY]
COLORS = [d[1] for d in DISPLAY]
MODELED = {d[0] for d in DISPLAY if d[2]}

# Staff roles summed into a comparable FTE series. support_staff_students_fte is
# deliberately excluded: CCD only reports it from FY2020, and including it would
# manufacture a ~400-FTE jump mid-series that never happened.
FTE_PARTS = ["teachers_total_fte", "instructional_aides_fte",
             "guidance_counselors_total_fte", "librarian_support_staff_fte",
             "school_administrators_fte", "school_admin_support_staff_fte",
             "lea_administrators_fte", "lea_admin_support_staff_fte",
             "support_staff_other_fte"]

NAVY, MUT, GRID = "#1e3a5f", "#64748b", "#e2e8f0"


def read(name, key="fiscal_year"):
    with open(os.path.join(D, name)) as f:
        return {int(r[key]): r for r in csv.DictReader(f)}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build_rows():
    f33, car = read("f33-iccsd.csv"), read("car-iccsd.csv")
    staff, cpi = read("staff-fte.csv"), read("cpi-u.csv", "year")
    rows = []
    for y in range(FIRST, LAST + 1):
        src = f33[y] if y <= SPLICE else car[y]
        raw = {c: float(src[c + "_labor"]) for c in SOURCE_CATS}

        # Spread the unallocated remainder pro-rata (see module docstring).
        residual = raw.pop("other_unallocated", 0.0)
        base = sum(raw[c] for c in ALLOCATABLE)
        cat = {c: raw[c] + (residual * raw[c] / base if base else 0) for c in ALLOCATABLE}

        st = staff[y]
        T, A = num(st["teachers_total_fte"]), num(st["instructional_aides_fte"])
        tshare = T / (T + PARA_PAY_RATIO * A) if T and A else 1.0

        disp = {
            "Teachers":                 cat["instruction"] * tshare,
            "Paraeducators":            cat["instruction"] * (1 - tshare),
            "Student & staff support":  cat["pupil_support"] + cat["instr_staff_support"],
            "School administration":    cat["school_admin"],
            "Central administration":   cat["general_admin"] + cat["business_central_other"],
            "Operations & maintenance": cat["oper_maint"],
            "Food service":             cat["food_service"],
            "Transportation":           cat["transportation"],
        }
        total = sum(disp.values())
        enroll = num(f33[y]["enrollment"]) if y in f33 else num(st["enrollment"])
        fte = sum(num(st[p]) or 0 for p in FTE_PARTS)

        rows.append({
            "fiscal_year": y,
            "source": "Census F-33" if y <= SPLICE else "Iowa DE CAR",
            **{k: round(v) for k, v in disp.items()},
            "total_labor": round(total),
            "enrollment": int(enroll),
            "staff_fte_comparable": round(fte, 1),
            "labor_per_pupil": round(total / enroll),
            "deflator": float(cpi[y][f"deflator_to_{LAST}"]),
            "real_labor_per_pupil": round(total / enroll * float(cpi[y][f"deflator_to_{LAST}"])),
            "labor_per_fte": round(total / fte) if fte else None,
        })
    return rows


def decompose(a, b):
    """Split per-pupil growth into three multiplicative drivers, allocating the dollar
    change by each driver's share of total log growth:
        labour = (cost per staff FTE) x (staff FTE per pupil) x (pupils)
    Log shares are used because the three compound rather than add."""
    import math
    f = [("Cost per staff member", b["labor_per_fte"] / a["labor_per_fte"]),
         ("Staff per student",
          (b["staff_fte_comparable"] / b["enrollment"]) / (a["staff_fte_comparable"] / a["enrollment"])),
         ("More students", b["enrollment"] / a["enrollment"])]
    logs = [(n, math.log(r)) for n, r in f]
    tot_log = sum(l for _, l in logs)
    delta = b["total_labor"] - a["total_labor"]
    return [{"name": n, "ratio": r, "pct": (r - 1) * 100,
             "dollars": delta * (lg / tot_log)}
            for (n, r), (_, lg) in zip(f, logs)]


def money(v, dp=1):
    return f"${v / 1e6:,.{dp}f}M"


def growth_pct(new, old):
    """Percent change, or "n/a" off a zero base. ICCSD contracts out student
    transportation, so that category's payroll is genuinely $0 in the early years --
    a real fact, not missing data, and one that has no meaningful growth rate."""
    return f"{(new / old - 1) * 100:+.0f}%" if old else "n/a"


def main():
    rows = build_rows()
    a, b = rows[0], rows[-1]

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- waterfall: start, one step per category, end -------------------------
    steps, run = [], a["total_labor"]
    for lab in LABELS:
        d = b[lab] - a[lab]
        steps.append({"label": lab, "delta": d, "lo": min(run, run + d),
                      "hi": max(run, run + d)})
        run += d

    wf_labels = ([f"FY{FIRST}"] + [SHORT.get(l, l).split("\n") if "\n" in SHORT.get(l, l)
                 else SHORT.get(l, l) for l in LABELS] + [f"FY{LAST}"])
    wf_data = ([[0, a["total_labor"]]] + [[s["lo"], s["hi"]] for s in steps]
               + [[0, b["total_labor"]]])
    wf_colors = [NAVY] + COLORS + [NAVY]
    wf_deltas = [a["total_labor"]] + [s["delta"] for s in steps] + [b["total_labor"]]

    growth = b["total_labor"] - a["total_labor"]
    ranked = sorted(steps, key=lambda s: -s["delta"])
    top = ranked[0]
    fastest = max(
        ({"label": l, "mult": b[l] / a[l], "delta": b[l] - a[l]} for l in LABELS if a[l] > 0),
        key=lambda x: x["mult"])

    dec = decompose(a, b)
    real_pp_chg = (b["real_labor_per_pupil"] / a["real_labor_per_pupil"] - 1) * 100
    # a["deflator"] scales FY2005 dollars up to FY2025 dollars, so it IS 1 + inflation.
    infl = (a["deflator"] - 1) * 100

    years = [r["fiscal_year"] for r in rows]
    idx = {l: [round(r[l] / a[l] * 100, 1) if a[l] else None for r in rows] for l in LABELS}
    idx_enroll = [round(r["enrollment"] / a["enrollment"] * 100, 1) for r in rows]

    # Sensitivity of the modelled teacher/para split to the pay-ratio assumption.
    staff = read("staff-fte.csv")
    band = []
    for r_ in (PARA_RATIO_BAND[0], PARA_PAY_RATIO, PARA_RATIO_BAND[1]):
        out = {}
        for yr, row in ((FIRST, a), (LAST, b)):
            st = staff[yr]
            T, A = num(st["teachers_total_fte"]), num(st["instructional_aides_fte"])
            instr = row["Teachers"] + row["Paraeducators"]
            out[yr] = instr * (1 - T / (T + r_ * A))
        band.append({"ratio": r_, "first": out[FIRST], "last": out[LAST],
                     "share_last": out[LAST] / (b["Teachers"] + b["Paraeducators"]) * 100})

    generated = datetime.date.today().isoformat()
    html = render(locals())
    with open(OUT_HTML, "w") as f:
        f.write(html)
    print(f"-> {os.path.relpath(OUT_HTML, ROOT)}")
    print(f"-> {os.path.relpath(OUT_CSV, ROOT)}  ({len(rows)} years)")
    print(f"   labor {money(a['total_labor'])} -> {money(b['total_labor'])} "
          f"({growth / a['total_labor'] * 100:+.0f}%), enrollment "
          f"{a['enrollment']:,} -> {b['enrollment']:,} "
          f"({(b['enrollment'] / a['enrollment'] - 1) * 100:+.0f}%)")
    print(f"   biggest contributor: {top['label']} {money(top['delta'])} "
          f"({top['delta'] / growth * 100:.0f}% of growth)")
    print(f"   fastest growing: {fastest['label']} x{fastest['mult']:.1f}")
    print(f"   real per-pupil {real_pp_chg:+.0f}% after {infl:.0f}% inflation")


def render(c):
    """Assemble the page. `c` is main()'s locals -- unpacked here to keep the template
    readable rather than threading a dozen arguments through."""
    rows, a, b = c["rows"], c["a"], c["b"]
    growth, top, fastest, dec = c["growth"], c["top"], c["fastest"], c["dec"]
    steps, band, years = c["steps"], c["band"], c["years"]

    enroll_pct = (b["enrollment"] / a["enrollment"] - 1) * 100
    labor_pct = growth / a["total_labor"] * 100
    pp_pct = (b["labor_per_pupil"] / a["labor_per_pupil"] - 1) * 100

    kpis = [
        ("Total labor cost", f"{money(a['total_labor'],0)} &rarr; {money(b['total_labor'],0)}",
         f"{labor_pct:+.0f}% over 20 years", "blue"),
        ("Students", f"{a['enrollment']:,} &rarr; {b['enrollment']:,}",
         f"{enroll_pct:+.0f}% over the same period", "blue"),
        ("Labor per student", f"${a['labor_per_pupil']:,} &rarr; ${b['labor_per_pupil']:,}",
         f"{pp_pct:+.0f}% before inflation", "amber"),
        ("Per student, inflation-adjusted",
         f"${a['real_labor_per_pupil']:,} &rarr; ${b['real_labor_per_pupil']:,}",
         f"{c['real_pp_chg']:+.0f}% in constant {LAST} dollars", "green"),
    ]
    kpi_html = "".join(
        f'<div class="kpi {k[3]}"><div class="lbl">{k[0]}</div>'
        f'<div class="val">{k[1]}</div><div class="sub">{k[2]}</div></div>' for k in kpis)

    dec_html = "".join(
        f'<div class="factor {cls}"><div class="f-num">{d["pct"]:+.0f}%</div>'
        f'<div class="f-lbl">{d["name"]}</div>'
        f'<div class="f-body">accounts for about <strong>{money(d["dollars"],0)}</strong> '
        f'of the {money(growth,0)} increase</div></div>'
        for d, cls in zip(dec, ["red", "amber", "blue"]))

    # Category table
    cat_rows = "".join(
        f'<tr><td class="lft"><span class="sw" style="background:{col}"></span>{lab}'
        + (' <span class="tag">modeled</span>' if lab in MODELED else '') + '</td>'
        f'<td>{money(a[lab])}</td><td>{money(b[lab])}</td>'
        f'<td class="{"gap-pos" if b[lab] >= a[lab] else "gap-neg"}">{money(b[lab] - a[lab])}</td>'
        f'<td>{growth_pct(b[lab], a[lab])}</td>'
        f'<td>{(b[lab] - a[lab]) / growth * 100:.1f}%</td></tr>'
        for lab, col, _ in DISPLAY)

    # Year-by-year table
    yr_rows = "".join(
        f'<tr><td class="lft">FY{r["fiscal_year"]}</td>'
        + "".join(f'<td>{r[l] / 1e6:,.1f}</td>' for l in LABELS)
        + f'<td class="tot">{r["total_labor"] / 1e6:,.1f}</td>'
        f'<td>{r["enrollment"]:,}</td><td>${r["labor_per_pupil"]:,}</td>'
        f'<td>${r["real_labor_per_pupil"]:,}</td>'
        f'<td class="src">{r["source"].replace("Census ", "").replace("Iowa DE ", "")}</td></tr>'
        for r in rows)

    band_html = "".join(
        f'<tr><td class="lft">{x["ratio"]:.2f}{" &larr; used" if x["ratio"] == PARA_PAY_RATIO else ""}</td>'
        f'<td>{money(x["first"])}</td><td>{money(x["last"])}</td>'
        f'<td>{x["share_last"]:.0f}%</td></tr>' for x in band)

    J = json.dumps
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Where did the money go? &mdash; ICCSD labor costs, FY{FIRST}&ndash;FY{LAST}</title>
<meta name="description" content="Iowa City Community School District payroll costs
 broken into teachers, paraeducators, school support, school administration and central
 administration, FY{FIRST}-FY{LAST}, compared against enrollment growth.">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{{--ink:#0f172a;--mut:{MUT};--line:{GRID};--bg:#f1f5f9;--card:#fff}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
.wrap{{max-width:960px;margin:0 auto;padding:8px 20px 60px}}
a{{color:#1d4ed8}}
h1{{font-size:26px;margin:18px 0 6px;color:{NAVY};line-height:1.25}}
.lede{{font-size:16px;color:#334155;margin:0 0 18px;max-width:760px}}
h2{{font-size:18px;margin:38px 0 6px;color:{NAVY};border-bottom:2px solid var(--line);
 padding-bottom:5px}}
h3{{font-size:15px;margin:22px 0 5px;color:#1e40af}}
p{{max-width:760px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:18px 0 6px}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 15px}}
.kpi .lbl{{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);
 font-weight:700}}
.kpi .val{{font-size:19px;font-weight:800;margin:5px 0 2px;color:{NAVY}}}
.kpi .sub{{font-size:12.5px;color:var(--mut)}}
.kpi.green .val{{color:#15803d}} .kpi.amber .val{{color:#b45309}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;
 padding:16px 18px;margin:14px 0}}
.chart{{position:relative;height:420px}}
.chart.short{{height:330px}}
.factors{{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px;margin:14px 0}}
.factor{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 15px}}
.factor .f-num{{font-size:25px;font-weight:800;line-height:1.1}}
.factor .f-lbl{{font-weight:700;font-size:14px;margin:3px 0 6px}}
.factor .f-body{{font-size:13px;color:#374151;margin:0}}
.factor.red{{border-top:3px solid #dc2626}} .factor.red .f-num{{color:#b91c1c}}
.factor.amber{{border-top:3px solid #d97706}} .factor.amber .f-num{{color:#b45309}}
.factor.blue{{border-top:3px solid #2563eb}} .factor.blue .f-num{{color:#1e40af}}
.callout{{background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:14px 16px;
 font-size:13.5px;color:#0c4a6e;margin:16px 0;max-width:820px}}
.callout strong{{color:#075985}}
.warn{{background:#fff7ed;border-color:#fed7aa;color:#7c2d12}} .warn strong{{color:#9a3412}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;margin:10px 0}}
th{{background:{NAVY};color:#fff;padding:6px 8px;text-align:right;font-weight:600;
 position:sticky;top:0}}
th.lft,td.lft{{text-align:left}}
td{{padding:5px 8px;border-bottom:1px solid #f1f5f9;text-align:right;
 font-variant-numeric:tabular-nums}}
tr:nth-child(even) td{{background:#f8fafc}}
td.gap-pos{{color:#15803d;font-weight:700}} td.gap-neg{{color:#b91c1c;font-weight:700}}
td.tot{{font-weight:700;border-left:1px solid var(--line);border-right:1px solid var(--line)}}
td.src{{color:var(--mut);font-size:11.5px}}
.sw{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:7px;
 vertical-align:baseline}}
.tag{{font-size:10px;text-transform:uppercase;letter-spacing:.04em;background:#eef2ff;
 color:#4338ca;border:1px solid #c7d2fe;border-radius:4px;padding:1px 5px;margin-left:5px;
 font-weight:700}}
.scroll{{overflow-x:auto;max-height:560px;overflow-y:auto}}
table.wide{{font-size:11.5px}} table.wide td,table.wide th{{padding:4px 6px}}
.foot{{color:var(--mut);font-size:12.5px;margin-top:34px;border-top:1px solid var(--line);
 padding-top:14px}}
details{{margin:10px 0}} summary{{cursor:pointer;font-weight:600;color:#1e40af}}
@media(max-width:640px){{.chart{{height:360px}} h1{{font-size:22px}}}}
</style></head><body>
{nav("more")}
<div class="wrap">

<h1>Where did the money go?</h1>
<p class="lede">Roughly nine of every ten dollars a school district spends is somebody's
pay. So &ldquo;where did spending grow?&rdquo; is very nearly &ldquo;whose payroll
grew?&rdquo; This page splits two decades of Iowa City CSD payroll &mdash; salaries
<em>and</em> benefits &mdash; into the jobs that make it up, and asks how much of the
growth is simply explained by teaching more children.</p>

<div class="kpis">{kpi_html}</div>

<div class="callout"><strong>The one-line answer.</strong>
Labor cost rose {labor_pct:.0f}% while enrollment rose {enroll_pct:.0f}%.
{top["label"]} added the most money ({money(top["delta"],0)}, or
{top["delta"] / growth * 100:.0f}% of all growth), because it is by far the biggest
payroll. But the <em>fastest-growing</em> line was {fastest["label"]}, which
multiplied {fastest["mult"]:.1f}&times; &mdash; well over double the
{b["total_labor"] / a["total_labor"]:.1f}&times; of the district as a whole.
Set against {c["infl"]:.0f}% inflation, spending per student rose
{c["real_pp_chg"]:+.0f}% in real terms.</div>

<h2>1. The waterfall: {money(a["total_labor"],0)} to {money(b["total_labor"],0)}</h2>
<p>Each bar is one category's contribution to the {money(growth,0)} increase. The
navy bars are the FY{FIRST} and FY{LAST} totals; everything between them adds up to
the difference.</p>
<div class="card"><div class="chart"><canvas id="wf"></canvas></div></div>

<div class="scroll"><table>
<thead><tr><th class="lft">Category</th><th>FY{FIRST}</th><th>FY{LAST}</th>
<th>Change</th><th>Growth</th><th>Share of growth</th></tr></thead>
<tbody>{cat_rows}
<tr><td class="lft"><strong>Total</strong></td><td><strong>{money(a["total_labor"])}</strong></td>
<td><strong>{money(b["total_labor"])}</strong></td>
<td class="gap-pos"><strong>{money(growth)}</strong></td>
<td><strong>{labor_pct:+.0f}%</strong></td><td><strong>100.0%</strong></td></tr>
</tbody></table></div>

<h2>2. Every category outran enrollment</h2>
<p>Indexed so FY{FIRST}&nbsp;=&nbsp;100. The dashed black line is the number of
students. Any line above it is a payroll that grew faster than the district it
serves.</p>
<div class="card"><div class="chart"><canvas id="idx"></canvas></div></div>

<h2>3. So what actually drove it?</h2>
<p>Payroll is the product of three things: how many students there are, how many
staff the district employs per student, and what each staff member costs. Splitting
the {money(growth,0)} increase across the three:</p>
<div class="factors">{dec_html}</div>
<p>Read it this way: more students explain a real but minority share of the growth.
The district also employs more adults per student than it did in FY{FIRST}, and each
of those adults costs more &mdash; most of which is ordinary wage and benefit
inflation rather than a policy choice.</p>

<h2>4. After inflation</h2>
<p>Nominal dollars flatter every twenty-year comparison. In constant FY{LAST}
dollars, spending per student went from
<strong>${a["real_labor_per_pupil"]:,}</strong> to
<strong>${b["real_labor_per_pupil"]:,}</strong> &mdash; {c["real_pp_chg"]:+.0f}%. That
is the number to quote; the {pp_pct:+.0f}% nominal figure mostly measures the dollar,
not the district.</p>
<div class="card"><div class="chart short"><canvas id="real"></canvas></div></div>

<h2>5. Year by year</h2>
<p>Every figure behind the charts. Dollars in millions.</p>
<div class="scroll"><table class="wide">
<thead><tr><th class="lft">Year</th>
{"".join(f"<th>{SHORT.get(l, l).replace(chr(10), '<br>')}</th>" for l in LABELS)}
<th>Total</th><th>Students</th><th>Per student</th>
<th>Per student<br>(real)</th><th>Source</th></tr></thead>
<tbody>{yr_rows}</tbody></table></div>

<h2>Where these numbers come from, and what to distrust</h2>

<h3>Sources</h3>
<p>Two official records, spliced. <strong>FY{FIRST}&ndash;FY{SPLICE}</strong> is the
U.S. Census Bureau's <em>Annual Survey of School System Finances</em> (the F-33),
which republishes Iowa's own filing with salaries and benefits broken out by
function. <strong>FY{SPLICE + 1}&ndash;FY{LAST}</strong> is the Iowa Department of
Education's <em>Certified Annual Report</em> workbooks, which the F-33 has not yet
caught up to. Staff counts are the federal Common Core of Data. Inflation is BLS
CPI-U.</p>
<p>The splice is not a leap of faith: both sources exist for FY2019&ndash;FY2023, and
on those five years they agree within <strong>0.6%</strong> on total labor and
essentially to the dollar on every named category. The FY{LAST} figures were
separately reconciled &mdash; to the cent &mdash; against the district's own certified
CAR.</p>

<div class="callout warn"><strong>Three things to hold loosely.</strong>
<br><strong>1. Teachers vs. paraeducators is modeled, not reported.</strong> Neither
source separates them &mdash; both sit inside &ldquo;Instruction.&rdquo; The split here
assumes a paraeducator costs {PARA_PAY_RATIO:.2f} of a teacher and divides Instruction
pay by staff counts. The sensitivity table below shows it barely moves the story, but
those two bars are estimates and are tagged as such.
<br><strong>2. Staff headcounts are noisy where the dollars are not.</strong> Districts
recode roles between years. Two visible cases: reported teacher aides drop about a
third at FY2011, and school administrators roughly double at FY2022 &mdash; neither with
any matching move in spending. The FY2011 one is why the modeled paraeducator line
steps down that year; read it as a change in counting, not in staffing. The
<em>dollars</em> throughout this page come from the financial filings and are
unaffected.
<br><strong>3. Pandemic money distorts the recent years.</strong> Federal ESSER funds
inflate FY2021&ndash;FY2024 payroll and their expiry deflates FY{LAST}. The FY{LAST}
endpoint is a post-ESSER number; treat the last four years as a bump, not a trend.</div>

<h3>Is the teacher/paraeducator split load-bearing?</h3>
<p>No. Varying the pay-ratio assumption across its plausible range changes the
paraeducator line by a few million dollars and leaves every conclusion intact.</p>
<table><thead><tr><th class="lft">Assumed pay ratio</th><th>Paraeducators FY{FIRST}</th>
<th>Paraeducators FY{LAST}</th><th>Share of instruction pay</th></tr></thead>
<tbody>{band_html}</tbody></table>

<details><summary>Further notes on method</summary>
<p><strong>Scope.</strong> All operating funds, not just the General Fund &mdash;
including the Management fund, which carries early-retirement and insurance costs
that are unmistakably labor and that a General-Fund-only view would miss entirely.
Capital funds (SAVE, PPEL, construction) and debt service are excluded; SAVE's
construction-management payroll is excluded with them, for consistency with the
earlier years.</p>
<p><strong>Unallocated residual.</strong> The F-33 does not push every salary dollar
into a named function. That remainder is spread pro-rata across the named categories
so both halves of the series sit on the same basis. It is under 1% of salaries in
every year except FY{FIRST} (2.2% of salaries, 7.7% of benefits) &mdash; the base year,
so it is worth knowing about.</p>
<p><strong>Transportation</strong> looks near-zero because ICCSD contracts the service
out: the cost is real but appears as purchased services, not payroll, and so is
outside a labor analysis by construction.</p>
<p><strong>Choice of deflator.</strong> CPI-U measures what a dollar buys a household,
which is the right lens for &ldquo;did this cost taxpayers more in real terms.&rdquo;
A different question &mdash; &ldquo;did the district pay above the going rate for
staff?&rdquo; &mdash; would call for the BLS Employment Cost Index for state and local
government compensation, which has run somewhat above CPI over this period. Because
the ECI is the larger deflator, an ECI-based series would show <em>less</em> real
growth than the +{c["real_pp_chg"]:.0f}% shown here. So this page states the higher of
the two figures, not the more favorable one.</p>
<p><strong>No grade-level split.</strong> A frequent request, deliberately not
answered: no public dataset reports district spending by elementary / middle / high
school over this period. It could only be modeled from building-level staffing, and
would be an allocation, not a measurement.</p>
</details>

<p class="foot">Built by <code>scripts/build_labor_waterfall.py</code> from
<code>data/labor/</code>. Every figure traces to the U.S. Census F-33, the Iowa DE
Certified Annual Report, the federal Common Core of Data, or BLS CPI-U.
Generated {c["generated"]}.</p>
</div>

<script>
const FONT={{family:'-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',size:12}};
const GRID='{GRID}', TICK='{MUT}';
const fmtM=v=>'$'+(v/1e6).toFixed(1)+'M';
const LBL={J(c["wf_labels"])}, DAT={J(c["wf_data"])}, COL={J(c["wf_colors"])},
      DELTA={J(c["wf_deltas"])}, NCAT={len(LABELS)};

Chart.defaults.font=FONT; Chart.defaults.color=TICK;

new Chart(document.getElementById('wf'),{{
  type:'bar',
  data:{{labels:LBL,datasets:[{{data:DAT,backgroundColor:COL,borderRadius:4,
        borderSkipped:false,borderWidth:2,borderColor:'#fff'}}]}},
  options:{{responsive:true,maintainAspectRatio:false,
    layout:{{padding:{{top:26}}}},
    plugins:{{legend:{{display:false}},
      tooltip:{{callbacks:{{label:ctx=>{{
        const i=ctx.dataIndex, d=DELTA[i];
        return (i===0||i===LBL.length-1)?('Total '+fmtM(d))
          :((d>=0?'+':'\\u2212')+fmtM(Math.abs(d)));
      }}}}}}}},
    scales:{{x:{{grid:{{display:false}},ticks:{{maxRotation:0,minRotation:0,autoSkip:false,
        font:{{...FONT,size:11}}}}}},
      y:{{grid:{{color:GRID}},ticks:{{callback:v=>'$'+(v/1e6).toFixed(0)+'M'}},
        title:{{display:true,text:'Annual labor cost',color:TICK}}}}}}
  }},
  plugins:[{{id:'vals',afterDatasetsDraw(ch){{
    const cx=ch.ctx; cx.save();
    cx.font='700 11px '+FONT.family; cx.textAlign='center'; cx.fillStyle='#0f172a';
    ch.getDatasetMeta(0).data.forEach((bar,i)=>{{
      const d=DELTA[i];
      const t=(i===0||i===LBL.length-1)?fmtM(d)
             :((d>=0?'+':'\\u2212')+fmtM(Math.abs(d)));
      cx.fillText(t,bar.x,bar.y-6);
    }});
    cx.restore();
  }}}}]
}});

const YEARS={J(years)};
const IDX={J(c["idx"])}, IDXE={J(c["idx_enroll"])}, ICOL={J(COLORS)}, ILBL={J(LABELS)};
new Chart(document.getElementById('idx'),{{
  type:'line',
  data:{{labels:YEARS.map(y=>'FY'+y),
    datasets:ILBL.map((l,i)=>({{label:l,data:IDX[l],borderColor:ICOL[i],
      backgroundColor:ICOL[i],borderWidth:2,pointRadius:0,pointHoverRadius:5,tension:.25}}))
      .concat([{{label:'Students',data:IDXE,borderColor:'#0f172a',backgroundColor:'#0f172a',
        borderWidth:2.5,borderDash:[6,4],pointRadius:0,pointHoverRadius:5,tension:.25}}])}},
  options:{{responsive:true,maintainAspectRatio:false,
    interaction:{{mode:'index',intersect:false}},
    plugins:{{legend:{{position:'bottom',labels:{{boxWidth:11,boxHeight:11,usePointStyle:true,
        pointStyle:'rect',padding:11}}}},
      tooltip:{{callbacks:{{label:ctx=>ctx.dataset.label+': '+ctx.parsed.y+
        ' (FY{FIRST}=100)'}}}}}},
    scales:{{x:{{grid:{{display:false}},ticks:{{maxRotation:0,autoSkip:true,maxTicksLimit:11}}}},
      y:{{grid:{{color:GRID}},title:{{display:true,text:'Index, FY{FIRST} = 100',color:TICK}}}}}}
  }}
}});

const REAL={J([r["real_labor_per_pupil"] for r in rows])},
      NOM={J([r["labor_per_pupil"] for r in rows])};
new Chart(document.getElementById('real'),{{
  type:'line',
  data:{{labels:YEARS.map(y=>'FY'+y),datasets:[
    {{label:'Per student, nominal',data:NOM,borderColor:'#94a3b8',backgroundColor:'#94a3b8',
      borderWidth:2,borderDash:[5,4],pointRadius:0,pointHoverRadius:5,tension:.25}},
    {{label:'Per student, constant FY{LAST} dollars',data:REAL,borderColor:'{NAVY}',
      backgroundColor:'{NAVY}',borderWidth:2.5,pointRadius:0,pointHoverRadius:5,tension:.25}}]}},
  options:{{responsive:true,maintainAspectRatio:false,
    interaction:{{mode:'index',intersect:false}},
    plugins:{{legend:{{position:'bottom',labels:{{boxWidth:11,boxHeight:11,usePointStyle:true,
        pointStyle:'rect',padding:11}}}},
      tooltip:{{callbacks:{{label:ctx=>ctx.dataset.label+': $'+
        ctx.parsed.y.toLocaleString()}}}}}},
    scales:{{x:{{grid:{{display:false}},ticks:{{maxRotation:0,autoSkip:true,maxTicksLimit:11}}}},
      y:{{grid:{{color:GRID}},ticks:{{callback:v=>'$'+(v/1000).toFixed(0)+'k'}},
        title:{{display:true,text:'Labor cost per student',color:TICK}}}}}}
  }}
}});
</script>
</body></html>"""


if __name__ == "__main__":
    main()
