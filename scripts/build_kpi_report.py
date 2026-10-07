#!/usr/bin/env python3
"""
Render kpi-three-methodologies.html — the grouped three-methodology KPI benchmark.

Primary visual is a per-KPI LINE CHART: ICCSD highlighted (blue), the peer average bold/neutral
(slate), and the individual peer districts as faint lines, over a background shaded into the metric's
RATING BANDS (Moody's Aaa/Aa/A…, S&P 1–6, or the internal target green/amber/red). The shaded bands
double as the legend. A "Show all 15 districts" toggle reveals the exact district×year table (also
band-colored, with a peer-average row). Categorical KPIs (opinion, repeat finding, awards) render as a
colored table instead of a chart.

Reads data/kpi-three-methodologies.csv and scripts/kpi_catalog.py.  -> kpi-three-methodologies.html
"""
import csv, os, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kpi_catalog as K
from _nav import nav

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def p(*a): return os.path.join(ROOT, *a)

ICCSD = "Iowa City CSD"
ORDER = ["Iowa City CSD","Ankeny CSD","Cedar Rapids CSD","Davenport CSD","Des Moines Independent CSD",
 "Dubuque CSD","Johnston CSD","Linn-Mar CSD","Pleasant Valley CSD","Waterloo CSD","Waukee CSD",
 "West Des Moines CSD","College CSD (Prairie)","Muscatine CSD","Burlington CSD"]
SHORT = {d: d.replace(" CSD","").replace(" (Prairie)","") for d in ORDER}
YEARS = list(range(2015, 2026))
BADGE = {"Internal":"#7c3aed","Moody's":"#c2410c","S&P":"#0369a1","Shared":"#0f766e","Context":"#64748b"}
CATEGORICAL = {"opinion_type","repeat_finding","gfoa_award"}

def fnum(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def load():
    data = {}
    for r in csv.DictReader(open(p("data/kpi-three-methodologies.csv"))):
        data[(r["district"], int(r["fiscal_year"]))] = r
    return data

def fmt(x, unit):
    if x is None: return ""
    if unit in ("pct","ratio_pct"): return f"{x:g}%"
    if unit == "usd_pp": return f"${x:,.0f}"
    if unit in ("days","x","months","number"): return f"{x:g}"
    return f"{x:g}"

# ---------------------------------------------------------------- SVG line chart (numeric KPIs)
def yfmt(x, unit):
    if unit in ("pct","ratio_pct"): return f"{x:g}%"
    if unit == "usd_pp": return f"${x/1000:g}k" if abs(x) >= 1000 else f"${x:g}"
    return f"{x:g}"

def line_chart(kpi, series, peer_avg, basis):
    """series: {short_district: {year: value}}; peer_avg: {year: value}; basis: {short: {year: basis}}"""
    key, unit = kpi["key"], kpi["unit"]
    W, H = 1000, 300
    x0, x1, y0, y1 = 48, 858, 16, 250
    def X(yr): return x0 + (x1-x0) * (yr-YEARS[0]) / (YEARS[-1]-YEARS[0])
    # data domain — robust to outliers: base on 5th–95th percentile of ALL values, but always
    # keep ICCSD and the peer average fully in view; individual peer spikes get clipped to the edge.
    vals = []
    for dd, ys in series.items():
        vals += [v for v in ys.values() if isinstance(v,(int,float))]
    vals += [v for v in peer_avg.values() if isinstance(v,(int,float))]
    if not vals: return ""
    def pct(xs, q):
        xs = sorted(xs); i = (len(xs)-1)*q; lo_i=int(i)
        return xs[lo_i] if lo_i+1>=len(xs) else xs[lo_i]+(xs[lo_i+1]-xs[lo_i])*(i-lo_i)
    keep = [v for v in series.get(SHORT[ICCSD],{}).values() if isinstance(v,(int,float))]
    keep += [v for v in peer_avg.values() if isinstance(v,(int,float))]
    lo = min([pct(vals,0.05)] + keep); hi = max([pct(vals,0.95)] + keep)
    if lo == hi: lo, hi = lo-1, hi+1
    pad = (hi-lo)*0.10; lo -= pad; hi += pad
    def Y(v):
        yy = y1 - (y1-y0) * (v-lo) / (hi-lo)
        return min(max(yy, y0), y1)   # clamp outliers to the plot area
    parts = [f'<svg viewBox="0 0 {W} {H}" class="lc" preserveAspectRatio="xMidYMid meet" role="img">']
    # rating band shading (clipped to domain) + right-edge labels
    bands = K.BANDS.get(key)
    if bands:
        for label, color, blo, bhi in bands:
            seg_lo = lo if blo is None else max(lo, blo)
            seg_hi = hi if bhi is None else min(hi, bhi)
            if seg_hi <= seg_lo: continue
            yt, yb = Y(seg_hi), Y(seg_lo)
            parts.append(f'<rect x="{x0}" y="{yt:.1f}" width="{x1-x0}" height="{yb-yt:.1f}" fill="{color}" opacity="0.16"/>')
            if yb - yt > 13:
                parts.append(f'<text x="{x1+5}" y="{(yt+yb)/2+3:.1f}" class="bl" fill="{color}">{label}</text>')
    # x-axis labels + light verticals
    for yr in YEARS:
        parts.append(f'<line x1="{X(yr):.1f}" y1="{y0}" x2="{X(yr):.1f}" y2="{y1}" stroke="#eef2f7"/>')
        parts.append(f'<text x="{X(yr):.1f}" y="{y1+15}" class="xl">{str(yr)[2:]}</text>')
    # y ticks (lo, mid, hi)
    for v in (lo+ (hi-lo)*0.0+pad, (lo+hi)/2, hi-pad):
        parts.append(f'<text x="{x0-6}" y="{Y(v)+3:.1f}" class="yl">{yfmt(v,unit)}</text>')
    def poly(pts, **kw):
        if len(pts) < 1: return ""
        d = " ".join(f"{x:.1f},{y:.1f}" for x,y in pts)
        attrs = " ".join(f'{k}="{v}"' for k,v in kw.items())
        return f'<polyline points="{d}" fill="none" {attrs}/>'
    # faint peer lines (skip ICCSD), broken at gaps
    for dd, ys in series.items():
        if dd == SHORT[ICCSD]: continue
        seg, segs = [], []
        for yr in YEARS:
            v = ys.get(yr)
            if isinstance(v,(int,float)): seg.append((X(yr), Y(v)))
            elif seg: segs.append(seg); seg=[]
        if seg: segs.append(seg)
        for s in segs: parts.append(poly(s, stroke="#cbd5e1", **{"stroke-width":"1.25"}))
    # peer average (bold neutral)
    pa = [(X(yr), Y(peer_avg[yr])) for yr in YEARS if isinstance(peer_avg.get(yr),(int,float))]
    if len(pa) > 1: parts.append(poly(pa, stroke="#475569", **{"stroke-width":"2.6","stroke-dasharray":"5 3"}))
    # ICCSD (highlight); split audited vs management(FY24-25 dashed)
    ic = series.get(SHORT[ICCSD], {})
    aud, mgmt = [], []
    for yr in YEARS:
        v = ic.get(yr)
        if not isinstance(v,(int,float)): continue
        b = basis.get(SHORT[ICCSD],{}).get(yr,"audited")
        (mgmt if (b and b!="audited") else aud).append((X(yr), Y(v), yr))
    audpts = [(x,y) for x,y,_ in aud]
    if len(audpts) > 1: parts.append(poly(audpts, stroke="#2563eb", **{"stroke-width":"3.4"}))
    # connect last audited to first mgmt + mgmt dashed
    if aud and mgmt:
        bridge = [(aud[-1][0],aud[-1][1]),(mgmt[0][0],mgmt[0][1])]
        parts.append(poly(bridge, stroke="#2563eb", **{"stroke-width":"2","stroke-dasharray":"4 3","opacity":"0.8"}))
    if len(mgmt) > 1:
        parts.append(poly([(x,y) for x,y,_ in mgmt], stroke="#2563eb", **{"stroke-width":"2.4","stroke-dasharray":"4 3"}))
    for x,y,_ in aud: parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="#2563eb"/>')
    for x,y,_ in mgmt: parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#fff" stroke="#2563eb" stroke-width="1.6"/>')
    # end labels for ICCSD + peer avg (nudge apart)
    endlabels = []
    allic = aud + mgmt
    if allic: endlabels.append((allic[-1][1], "#2563eb", "ICCSD"))
    if pa: endlabels.append((pa[-1][1], "#475569", "Peer avg"))
    endlabels.sort()
    if len(endlabels)==2 and endlabels[1][0]-endlabels[0][0] < 13:
        endlabels[0]=(endlabels[1][0]-13, endlabels[0][1], endlabels[0][2])
    for yy, col, txt in endlabels:
        parts.append(f'<text x="{x1+5}" y="{yy+3:.1f}" class="el" fill="{col}">{txt}</text>')
    parts.append("</svg>")
    return "".join(parts)

def band_legend(kpi):
    bands = K.BANDS.get(kpi["key"])
    if not bands:
        return f'<div class="blg ctx">Context measure — no rating band. <b>Benchmark:</b> {kpi["target"]}</div>'
    def rng(lo,hi):
        if lo is None: return f"&lt;{hi:g}"
        if hi is None: return f"≥{lo:g}"
        return f"{lo:g}–{hi:g}"
    chips = "".join(
        f'<span class="chip"><span class="sw" style="background:{c}"></span>{lab} <span class="rg">{rng(lo,hi)}</span></span>'
        for lab,c,lo,hi in bands)
    return f'<div class="blg">{chips}</div>'

def cat_color(key, val):
    v = (val or "").strip()
    if key == "opinion_type": return "#bbf7d0" if v.lower()=="unmodified" else ("#fecaca" if v else "")
    if key == "repeat_finding": return "#bbf7d0" if v.upper()=="N" else ("#fecaca" if v.upper()=="Y" else "")
    if key == "gfoa_award": return "#bbf7d0" if v.upper()=="Y" else ("#f1f5f9" if v.upper()=="N" else "")
    return ""

def exec_summary(series, peer_avg):
    """Data-driven headline: ICCSD's standing vs the 14 peers in its last audited year (FY2024)."""
    def stat(key, year, good):
        vals = {d: series[key][SHORT[d]].get(year) for d in ORDER}
        vals = {d:v for d,v in vals.items() if isinstance(v,(int,float))}
        ic = vals.get(ICCSD)
        if ic is None: return None
        better = sum(1 for v in vals.values() if (v>ic if good=="up" else v<ic))
        med = sorted(vals.values())[len(vals)//2]
        return dict(v=ic, rank=better+1, n=len(vals), med=round(med))
    def fy(key, year): return series[key][SHORT[ICCSD]].get(year)
    Y = 2024
    bl = []
    uab = stat("uab_pct_of_max", Y, "up")
    if uab: bl.append(f"<b>Spending authority is the thinnest in the group.</b> Iowa City's Unspent Authorized Budget — "
        f"Iowa's single most important health measure — clawed back to just <b>{uab['v']:g}%</b> of its limit in FY2024 "
        f"after dipping <b>below zero in FY2023</b> (the unlawful, state-review SBRC level). Even rebuilt, it is still the "
        f"lowest of {uab['n']} districts (peer median {uab['med']:g}%).")
    sol = stat("solvency_ratio", Y, "up"); fb = stat("moodys_avail_fb_ratio", Y, "up"); dc = stat("days_net_cash", Y, "up")
    sol25 = fy("solvency_ratio", 2025); dc25 = fy("days_net_cash", 2025)
    if sol and fb and dc:
        soft = (f" The cash-reserve levy drove the rebuild off the FY2023 trough (solvency 2.4%), but self-reported "
                f"FY2025 figures already slip back toward it (solvency ≈{sol25:g}%, ≈{dc25:g} days of cash).") if sol25 else ""
        bl.append(f"<b>Reserves and cash sit near the bottom of the group.</b> In FY2024 its solvency (<b>{sol['v']:g}%</b>, "
            f"rank {sol['rank']} of {sol['n']}), available fund balance (<b>{fb['v']:g}%</b> of revenue) and day's-cash "
            f"(<b>{dc['v']:g} days</b>) all rank in the bottom group (peer medians ≈{sol['med']:g}%, {fb['med']:g}% and "
            f"{dc['med']:g} days; the internal cash target is 90)." + soft)
    emp = stat("employee_cost_ratio", Y, "down")
    if emp: bl.append(f"<b>Staffing costs are near the highest of {emp['n']}.</b> Salaries and benefits were <b>{emp['v']:g}%</b> "
        f"of the General Fund in FY2024 (rank {emp['rank']} of {emp['n']}; peer median {emp['med']:g}%) — the classic Iowa "
        f"squeeze of personnel costs climbing as enrollment flattens, the leading pressure behind the spending-authority decline.")
    ltl = stat("moodys_ltl_ratio", Y, "down")
    if ltl: bl.append(f"<b>Leverage runs above the peer norm.</b> Long-term liabilities (debt + pension + OPEB) were "
        f"<b>{ltl['v']:g}%</b> of GF revenue in FY2024 vs a {ltl['med']:g}% peer median; the district carries both GO and "
        f"SAVE sales-tax debt from its Facilities Master Plan.")
    bl.append("<b>The books are finally moving, but still late and flagged.</b> ICCSD filed its long-overdue FY2024 audit "
        "in <b>June 2026 — about two years after year-end</b> — and it carries <b>five financial-statement material "
        "weaknesses</b> plus qualified opinions on two federal programs. Its FY2025 audit is still unfiled, so the district "
        "remains the furthest behind of the 15.")
    items = "".join(f"<li>{b}</li>" for b in bl)
    return ('<div class="exec"><h2>Executive summary</h2>'
      '<p>Across all three rating lenses, <b>Iowa City sits at or near the bottom of its 15-district peer group</b> on the '
      'measures that matter most — spending authority, reserves, liquidity, and staffing costs. The newly filed FY2024 audit '
      'confirms a partial rebuild in reserves off the FY2023 low, but the district stays in the bottom group on every core '
      'measure, and its FY2025 audit is still unfiled.</p>'
      f'<ul>{items}</ul>'
      '<p class="exfoot">All figures trace to audited ACFRs or Iowa state filings; ranks are among the 15 districts in '
      'FY2024 (ICCSD\'s most recent audited year). FY2025 figures are management/unaudited, with the FY2025 CAR '
      'balance sheet adjusted for the corrections the FY2024 audit made to the CAR (GF cash, SAVE cash, and '
      'fund-balance classification).</p></div>')

def build():
    data = load()
    kpi_keys = [k["key"] for k in K.KPIS]
    series = {k: {SHORT[d]: {} for d in ORDER} for k in kpi_keys}
    basis = {SHORT[d]: {} for d in ORDER}
    for (d, fy), r in data.items():
        if d not in SHORT: continue
        basis[SHORT[d]][fy] = r.get("data_basis","")
        for k in kpi_keys:
            v = r.get(k, "")
            if v in (None, ""): continue
            if k in CATEGORICAL: series[k][SHORT[d]][fy] = v
            else:
                fv = fnum(v)
                if fv is not None: series[k][SHORT[d]][fy] = fv
    # peer average (exclude ICCSD), numeric KPIs
    peer_avg = {k: {} for k in kpi_keys}
    for k in kpi_keys:
        if k in CATEGORICAL: continue
        for yr in YEARS:
            xs = [series[k][SHORT[d]].get(yr) for d in ORDER if d != ICCSD]
            xs = [x for x in xs if isinstance(x,(int,float))]
            if xs: peer_avg[k][yr] = round(sum(xs)/len(xs), 2)

    # JSON payload for the interactive table
    payload = dict(series=series, peer_avg=peer_avg, basis=basis,
                   districts=[SHORT[d] for d in ORDER], years=YEARS, iccsd=SHORT[ICCSD],
                   bands={k: K.BANDS.get(k) for k in kpi_keys}, cat=list(CATEGORICAL),
                   units={k["key"]: k["unit"] for k in K.KPIS}, good={k["key"]: k["good"] for k in K.KPIS})

    exec_html = exec_summary(series, peer_avg)

    # methodology overview
    meth = """
<div class="mcards">
  <div class="mc"><div class="mt" style="color:#7c3aed">① ICCSD Internal</div><div class="md">The district's own
   <b>Ten-Point Financial Condition Test</b> — Iowa-specific ratios (solvency, day's cash, employee-cost,
   unspent-balance) from its Annual Financial Health Report.</div></div>
  <div class="mc"><div class="mt" style="color:#c2410c">② Moody's</div><div class="md"><b>US K-12 Public School
   Districts</b> scorecard (Jul 2024). We compute the audit-derivable sub-factors and color each by its Moody's
   alpha band (Aaa–Caa).</div></div>
  <div class="mc"><div class="mt" style="color:#0369a1">③ S&amp;P</div><div class="md"><b>Methodology for Rating
   US Governments</b> (Sep 2024). Financial factors colored by S&amp;P's 1–6 assessment scale.</div></div>
</div>"""

    sections = []
    for gk, gl, gd in K.GROUPS:
        cards = []
        for kpi in [k for k in K.KPIS if k["group"] == gk]:
            key, src = kpi["key"], kpi["source"]
            note = f'<div class="note">⚠ {kpi["note"]}</div>' if kpi.get("note") else ""
            dirtxt = '↑ better' if kpi['good']=='up' else '↓ better' if kpi['good']=='down' else '◦ context'
            head = (f'<div class="kch"><h4>{kpi["label"]}</h4>'
                    f'<span class="badge" style="background:{BADGE[src]}">{src}</span>'
                    f'<span class="dir">{dirtxt}</span></div>'
                    f'<div class="frm"><b>Formula:</b> {kpi["formula"]}</div>{note}')
            if key in CATEGORICAL:
                body = f'<div class="blg ctx">{kpi["target"]}</div><button class="hbtn" data-kpi="{key}">Show all 15 districts ▸</button><div class="heat" id="heat-{key}"></div>'
            else:
                chart = line_chart(kpi, series[key], peer_avg[key], basis)
                body = (band_legend(kpi) + f'<div class="chartwrap">{chart}</div>'
                        f'<button class="hbtn" data-kpi="{key}">Show the 15-district table ▸</button>'
                        f'<div class="heat" id="heat-{key}"></div>')
            cards.append(f'<div class="kcard" id="kc-{key}">{head}{body}</div>')
        sections.append(f'<section class="grp" id="grp-{gk}"><h2>{gl}</h2><p class="gd">{gd}</p>{"".join(cards)}</section>')

    qrows = "".join(
        f'<tr><td><span class="badge" style="background:{BADGE.get(q["methodology"],"#64748b")}">{q["methodology"]}</span></td>'
        f'<td><b>{q["factor"]}</b></td><td>{q["weight"]}</td><td>{q["reason"]}</td></tr>' for q in K.QUALITATIVE)

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ICCSD — Three-Methodology KPI Benchmark (FY2015–FY2025)</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0}}
*{{box-sizing:border-box}}
body{{font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);margin:0;background:#f1f5f9}}
.wrap{{max-width:1060px;margin:0 auto;padding:30px 20px 70px}}
h1{{font-size:29px;margin:0 0 6px}} .sub{{color:var(--mut);margin:0 0 18px}}
.intro{{background:#fff;border:1px solid var(--line);border-left:4px solid #2563eb;border-radius:10px;padding:16px 20px;margin-bottom:16px}}
.intro p{{margin:7px 0}}
.exec{{background:#fff;border:1px solid #fecaca;border-left:4px solid #dc2626;border-radius:10px;padding:16px 22px;margin-bottom:16px}}
.exec h2{{font-size:20px;margin:0 0 8px;color:#0f172a}}
.exec p{{margin:6px 0;font-size:15px}} .exec ul{{margin:10px 0;padding-left:20px}} .exec li{{margin:8px 0;font-size:14.5px;line-height:1.55}}
.exec .exfoot{{color:#64748b;font-size:12.5px;margin-top:8px}}
.mcards{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin:14px 0 8px}}
@media(max-width:760px){{.mcards{{grid-template-columns:1fr}}}}
.mc{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
.mt{{font-weight:800;font-size:15px;margin-bottom:5px}} .md{{font-size:13.5px;color:#334155}}
.toc{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 18px;margin:8px 0 12px;font-size:14px}}
.toc a{{color:#2563eb;text-decoration:none;margin-right:14px;white-space:nowrap;display:inline-block;padding:3px 0}}
.hint{{font-size:13px;color:var(--mut);margin:6px 2px 20px}}
.hint b{{color:#2563eb}} .hint i{{color:#475569;font-style:normal;font-weight:700}}
.grp{{margin:28px 0}} .grp h2{{font-size:22px;margin:0 0 4px;border-bottom:2px solid #cbd5e1;padding-bottom:6px}}
.gd{{color:var(--mut);margin:4px 0 14px;font-size:14.5px}}
.kcard{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.kch{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:8px;margin-bottom:8px}}
.kch h4{{margin:0;font-size:18px}} .badge{{color:#fff;font-size:11px;font-weight:700;padding:2px 9px;border-radius:999px}}
.dir{{margin-left:auto;font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}}
.frm{{font-size:13.5px;color:#334155;margin:3px 0}} .frm b{{color:#0f172a}}
.note{{font-size:12.5px;color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:7px;padding:5px 9px;margin:6px 0}}
.blg{{display:flex;flex-wrap:wrap;gap:5px 12px;margin:8px 0 4px;font-size:12px;color:#475569}}
.blg.ctx{{color:#64748b;font-style:italic}}
.chip{{display:inline-flex;align-items:center;gap:4px;white-space:nowrap}} .chip .rg{{color:#94a3b8}}
.sw{{display:inline-block;width:11px;height:11px;border-radius:3px}}
.chartwrap{{width:100%;margin:4px 0 2px}}
svg.lc{{width:100%;height:auto;display:block}}
svg.lc .xl{{font:11px sans-serif;fill:#94a3b8;text-anchor:middle}}
svg.lc .yl{{font:10px sans-serif;fill:#94a3b8;text-anchor:end}}
svg.lc .bl{{font:10px sans-serif;font-weight:700;text-anchor:start;opacity:.9}}
svg.lc .el{{font:11.5px sans-serif;font-weight:700;text-anchor:start}}
.hbtn{{margin-top:8px;font:600 12.5px inherit;color:#2563eb;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:5px 11px;cursor:pointer}}
.hbtn:hover{{background:#dbeafe}}
.heat{{overflow-x:auto;margin-top:10px}}
table.hm{{border-collapse:collapse;font-size:12px;width:100%}}
table.hm th,table.hm td{{border:1px solid #e9eef5;padding:3px 6px;text-align:center;font-variant-numeric:tabular-nums;white-space:nowrap}}
table.hm th{{background:#f8fafc;color:#475569;font-weight:600}}
table.hm td.d{{text-align:left;font-weight:600;position:sticky;left:0;background:#fff}}
table.hm tr.me td{{outline:2px solid #2563eb;outline-offset:-2px}} table.hm tr.me td.d{{color:#1d4ed8}}
table.hm tr.pa td{{font-weight:700;background:#f1f5f9}} table.hm tr.pa td.d{{color:#334155}}
table.hm td.proj{{font-style:italic;opacity:.85}}
.qual,.appx{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 20px;margin:18px 0;font-size:14px}}
.qual table{{border-collapse:collapse;width:100%;font-size:13.5px;margin-top:8px}} .qual td{{border-top:1px solid var(--line);padding:7px 8px;vertical-align:top}}
.appx li{{margin:5px 0}}
footer{{color:var(--mut);font-size:12.5px;margin-top:30px;border-top:1px solid var(--line);padding-top:14px}}
</style></head><body>{nav("more")}<div class="wrap">

<h1>ICCSD Financial KPIs — Three Methodologies, FY2015–FY2025</h1>
<p class="sub">Iowa City CSD and 14 benchmarked peer districts, under the district's own internal ratios,
Moody's, and S&amp;P — grouped by financial area · audited ACFRs + official Iowa filings (ICCSD FY2025 from management reporting; its FY2024 audit was filed June 2026)</p>

<div class="intro">
<p>Each KPI is charted three ways' worth of context at once. The <b style="color:#2563eb">blue line is Iowa City</b>;
the <b style="color:#475569">dashed slate line is the 14-peer average</b>; faint gray lines are the individual peers.
The <b>shaded background is the rating band</b> the value sits in — Moody's <b>Aaa→Caa</b>, S&amp;P <b>1→6</b>, or the
internal target (green = strong, amber = caution, red = concern) — so you can read the grade by color. Use
<i>Show the 15-district table</i> for exact numbers.</p>
</div>
{exec_html}
{meth}
<div class="toc"><b>Jump to:</b> """ + " ".join(f'<a href="#grp-{gk}">{gl}</a>' for gk,gl,_ in K.GROUPS) + """
<a href="#qual">Qualitative factors</a> <a href="#appx">Notes</a></div>
<p class="hint">ICCSD's FY2025 (its most recent year) is <i>dashed with a hollow dot</i> — management/unaudited (that audit isn't filed yet; the FY2024 audit was filed June 2026).</p>
""" + "".join(sections) + f"""
<section id="qual"><div class="qual">
<h2 style="font-size:20px;margin:0 0 4px">Qualitative / external factors — named, not scored</h2>
<p style="color:#64748b;font-size:14px;margin:4px 0">Rating-agency factors that can't be derived from audited
financials. For all Iowa districts the institutional framework is the same: a <b>state-determined revenue
framework</b> (the foundation formula caps spending authority; local voters add ISL, PPEL, SAVE).</p>
<table><tr><td><b>Methodology</b></td><td><b>Factor</b></td><td><b>Weight</b></td><td><b>Why external/qualitative</b></td></tr>
{qrows}</table></div></section>

<section id="appx"><div class="appx">
<h2 style="font-size:20px;margin:0 0 8px">Notes</h2>
<ul>
<li><b>Sources.</b> Audited ACFRs (FY15–23 ICCSD; FY15–25 peers), Iowa DOM (UAB, enrollment, valuations, levies),
the Certified Annual Report (function detail FY17–23), and ICCSD's Annual Financial Health Report (FY15–19 internal
ratios, verbatim). ICCSD's FY2025 audit is <b>not filed</b>; that year uses management/unaudited actuals (PFM) and the FY2025 CAR
<b>adjusted for the corrections the FY2024 audit made to the FY2024 CAR</b>: the audit cut the CAR's governmental-funds
cash by $38.4M (General Fund −$3.4M, SAVE/PPEL −$34.4M — the unapproved-interfund-loan finding), trimmed the GF ending
balance by $0.31M, and reclassified $1.4M from restricted to unassigned. Carried into FY2025: adjusted GF balance
$17.98M (unassigned $13.67M), and GF current assets use management's GF cash ($19.4M) rather than the FY2025 CAR's
$43.7M, which repeats the misallocation pattern. Details: <code>data/iccsd-fy24-car-vs-audit-cash.csv</code>.
Its FY2024 audit was filed June 2026 and is included as audited.</li>
<li><b>GF cash</b> uses General-Fund cash (not all-funds), so day's-cash ties to the district's published series.</li>
<li><b>Operating revenue</b> for Moody's/S&amp;P ratios is proxied by General Fund revenue. Long-term-liabilities uses
<b>reported</b> GASB pension/OPEB, not Moody's discount-rate-adjusted figures.</li>
<li><b>Per-capita vs per-pupil.</b> Net direct debt / pension are scored <b>per capita</b> by the agencies; shown here
<b>per pupil</b> (context, no band) since audits don't carry population.</li>
<li><b>S&amp;P current cost</b> uses actual debt service, so refunding years spike; the Moody's fixed-costs ratio (implied debt service) is the refunding-robust comparator.</li>
<li><b>Reproduce:</b> <code>python3 scripts/build_kpi_dataset.py &amp;&amp; python3 scripts/build_kpi_report.py</code>. Data: <code>data/kpi-three-methodologies.csv</code>; definitions/bands: <code>scripts/kpi_catalog.py</code>.</li>
</ul></div></section>
</div>
<script>
const D = {json.dumps(payload)};
function ufmt(u,v){{ if(typeof v!=='number') return v||'';
  if(u==='usd_pp') return '$'+Math.round(v).toLocaleString();
  if(u==='pct'||u==='ratio_pct') return (Math.round(v*100)/100)+'%';
  return (Math.round(v*100)/100); }}
function bandColor(key,v){{ const bands=D.bands[key]; if(!bands||typeof v!=='number') return '';
  for(const [lab,c,lo,hi] of bands){{ if((lo===null||v>=lo)&&(hi===null||v<hi)) return c; }} return ''; }}
function catColor(key,v){{ v=(v||'').trim();
  if(key==='opinion_type') return v.toLowerCase()==='unmodified'?'#bbf7d0':(v?'#fecaca':'');
  if(key==='repeat_finding') return v.toUpperCase()==='N'?'#bbf7d0':(v.toUpperCase()==='Y'?'#fecaca':'');
  if(key==='gfoa_award') return v.toUpperCase()==='Y'?'#bbf7d0':(v.toUpperCase()==='N'?'#f1f5f9':''); return ''; }}
const isCat = k => D.cat.includes(k);
function cell(key,dd,y){{ const v=(D.series[key][dd]||{{}})[y];
  if(v===undefined) return '<td>·</td>';
  const proj=((D.basis[dd]||{{}})[y]||'').indexOf('audited')!==0?' proj':'';
  const col=isCat(key)?catColor(key,v):bandColor(key,v);
  const tint=col?'background:'+col+'55':'';
  return '<td class="'+proj.trim()+'" style="'+tint+'">'+(isCat(key)?v:ufmt(D.units[key],v))+'</td>'; }}
document.querySelectorAll('.hbtn').forEach(btn=>{{
  btn.addEventListener('click',()=>{{
    const key=btn.dataset.kpi, host=document.getElementById('heat-'+key);
    if(host.dataset.open==='1'){{host.innerHTML='';host.dataset.open='0';btn.textContent=btn.textContent.replace('Hide','Show').replace('▾','▸');return;}}
    let h='<table class="hm"><tr><th class="d">District</th>'+D.years.map(y=>'<th>FY'+String(y).slice(2)+'</th>').join('')+'</tr>';
    D.districts.forEach(dd=>{{ const me=dd===D.iccsd?' class="me"':'';
      h+='<tr'+me+'><td class="d">'+dd+'</td>'+D.years.map(y=>cell(key,dd,y)).join('')+'</tr>';
      if(dd===D.iccsd && !isCat(key)){{ // peer-average row right under ICCSD
        h+='<tr class="pa"><td class="d">Peer average</td>'+D.years.map(y=>{{const v=(D.peer_avg[key]||{{}})[y];
          const col=bandColor(key,v); return '<td style="'+(col?'background:'+col+'55':'')+'">'+(v===undefined?'·':ufmt(D.units[key],v))+'</td>';}}).join('')+'</tr>';
      }} }});
    h+='</table>'; host.innerHTML=h; host.dataset.open='1';
    btn.textContent=btn.textContent.replace('Show','Hide').replace('▸','▾');
  }});
}});
</script></body></html>"""
    open(p("kpi-three-methodologies.html"), "w").write(html)
    print(f"Wrote kpi-three-methodologies.html ({len(html):,} bytes)")

if __name__ == "__main__":
    build()
