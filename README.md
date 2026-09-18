# Iowa City Schools — Follow the Money

A plain-English look at the financial health of the **Iowa City Community School District (ICCSD)**,
measured against other large Iowa school districts. Every number here comes from official sources — the
districts' own audited financial reports and the State of Iowa's public filings. Nothing is guessed or
made up.

The goal is simple: make it easy for any resident — parent, taxpayer, board member, reporter — to see
how Iowa City's schools are doing with money, in context, without needing an accounting background.

---

## 👉 See it online

**[View the website →](https://michael480th.github.io/ICCSD_Financial_Benchmarking/)**

That link opens an easy-to-read site. A row of buttons across the top lets you jump between the
different views. You don't need to download anything — it works on a phone or a computer.

---

## What you'll find

The site is organized as four pages — the questions a resident asks, in order. Each answers one question
in plain language, with a short explanation of why it matters.

| Page | The question it answers |
|---|---|
| **1. [How ICCSD compares](https://michael480th.github.io/ICCSD_Financial_Benchmarking/)** | The starting point. How does Iowa City stack up against similar-sized Iowa districts, one measure at a time? |
| **2. [Does it have a cushion?](https://michael480th.github.io/ICCSD_Financial_Benchmarking/iccsd-cushion.html)** | Does the district keep a financial safety margin — and is it shrinking? Three ways to measure it (spending room, reserves, and days of cash), all in one place. |
| **3. [Dig into the data](https://michael480th.github.io/ICCSD_Financial_Benchmarking/iowa-district-financial-benchmark.html)** | The complete picture: all 15 of Iowa's largest districts, scored side by side, with a deep-dive tool for any one district. |

One more, worth its own line:

- **[Where did the money go?](https://michael480th.github.io/ICCSD_Financial_Benchmarking/iccsd-labor-waterfall.html)** — labor is roughly nine of every ten dollars a district spends, so this is very nearly the whole spending story. FY2005–FY2025 payroll split into teachers, paraeducators, school support, school administration and central administration, set against enrollment growth.

Two more, kept off to the side:

- **[Other analyses](https://michael480th.github.io/ICCSD_Financial_Benchmarking/other-analyses.html)** — the narrower and older pieces, including **"Can we trust the numbers?"** (the reporting-integrity / CAR-vs-audited screen), the student-activities fund, point-in-time FY24 snapshots, filing-timeliness, and a neighboring district, plus the detailed single-topic versions behind the main pages.
- **[Oversight committee](https://michael480th.github.io/ICCSD_Financial_Benchmarking/making-the-foc-work.html)** — practical templates for the kind of regular financial reporting that keeps a district on track.

---

## A note on one important idea

Iowa is unusual: the state caps how much a district is *allowed to spend* each year, separately from how
much *cash* it actually has. That means a district can have money in the bank and still be in trouble —
or look fine on cash while quietly running out of room to spend. Much of this analysis comes back to that
distinction, and the pages explain it as they go.

---

## Where the numbers come from

Two kinds of official records, and the site is always clear about which one a number comes from:

- **Audited financial reports.** Each district hires independent auditors who verify its books and publish
  a yearly report. These are the gold standard — but a district only has one once it finishes and files
  its audit (and Iowa City is currently running behind on that).
- **State filings.** The State of Iowa collects and publishes its own figures for every district every
  year — spending limits, enrollment, tax and levy data, and more. These aren't independently audited, but
  they exist even when a district's audit is late, which is how Iowa City still shows up in recent years.

Every figure can be traced back to one of these official records. Where something couldn't be confirmed,
it's flagged or left blank rather than filled in with a guess.

A couple of things worth knowing when you read the charts:

- A negative "unrestricted net position" looks alarming but is **normal** for Iowa schools — it reflects
  long-term pension obligations, not a district about to run out of money.
- One figure people often ask about — staff salaries and benefits — isn't broken out in the audited
  reports, so the benchmark pages note it rather than score it. It *can* be recovered from two other
  official records, and ["Where did the money go?"](https://michael480th.github.io/ICCSD_Financial_Benchmarking/iccsd-labor-waterfall.html)
  does exactly that: twenty years of payroll, split by the jobs it pays for.

---

## Want the numbers in a spreadsheet?

Download **[`data/iowa-district-benchmark.xlsx`](data/iowa-district-benchmark.xlsx)** — the whole benchmark
as an Excel file, with the scores, the year-by-year history, the underlying source data, and a sheet that
defines every term. Good for anyone who wants to check the math or slice it their own way.

---

## For the technically curious

This repository holds both the public website and the code that builds it. Everything is generated from
the data files under `data/`, so the analysis can be reproduced and checked end to end.

```bash
python3 scripts/build_analysis.py        # combine the source data and score every district
python3 scripts/build_report.py          # "Dig into the data" — full 15-district report
python3 scripts/build_iccsd_report.py    # "How ICCSD compares" landing page (index.html)
python3 scripts/build_cushion.py         # "Does it have a cushion?" (reserves + cash)
python3 scripts/build_integrity_report.py # "Can we trust the numbers?" reporting screen
python3 scripts/build_other_analyses.py  # the "Other analyses" index
python3 scripts/build_workbook.py        # build the Excel spreadsheet

# "Where did the money go?" — the 20-year labor decomposition (fetch, then build)
python3 scripts/fetch_f33_labor.py       # Census F-33 salaries/benefits by function, FY2005-FY2023
python3 scripts/fetch_car_labor.py       # Iowa DE CAR workbooks, FY2019-FY2025
python3 scripts/fetch_staff_fte.py       # NCES staff counts by role, FY2005-FY2025
python3 scripts/fetch_cpi.py             # BLS CPI-U, for the constant-dollar view
python3 scripts/build_labor_waterfall.py # -> iccsd-labor-waterfall.html
```

The site is published with **GitHub Pages** straight from this repository — the landing page is
`index.html`, and the page files (`*.html`) are self-contained, so each one also works if you simply
download it and open it in a browser, or email it to someone.

How the analysis is built up:

- **source folders → `scripts/extract_*.py` → `data/*.csv`** — the original state spreadsheets and audit
  reports are read in and turned into clean, tidy data tables. (Folders like `UAB/` and `PropertyValuation/`
  hold the original state files; each has a `source.txt` noting where it was downloaded from.)
- **`data/*.csv` → `scripts/build_*.py` → the web pages and spreadsheet** — those clean tables are scored
  and rendered into everything you see.

Each folder under `data/` has its own short README explaining its columns and where they came from. The
methodology — how each district is scored and the Iowa-specific reasoning behind every measure — is in
[`iowa-district-financial-analysis-framework.md`](iowa-district-financial-analysis-framework.md).
