"""Sheet "Institution_Bursts": the institutions with the strongest bursts of publication, like the "citation burst history" of CiteSpace (that page, a table, PNG and SVG).
A burst is a stretch of years in which the institution has more papers than its overall share predicts. Method: Kleinberg's burst detection (two states, a burst is a share of
s = 2 times the overall share), run on the yearly paper counts of every institution that has at least --min-papers papers; the strength of a burst is the sum of the cost
differences over its years; a institution is shown with its strongest burst. "Year" = first year with a paper of the institution.
A paper counts once for each institution of its affiliations.
Your choices: --top N (how many institutions are shown, default 10), --gamma G (cost of starting a burst = G * ln(number of years); a smaller value finds more and longer bursts, default 0.7),
--min-papers M (the institutions with fewer papers are not tested, default 5).
Check: on the Country data of this study gamma = 0.7 gives the same 10 countries with the same begin and end years as the CiteSpace table (strengths within about 0.4 of it).
Input : Affiliations/Affiliations.csv (run Affiliations.py first)
Output: Institution_Bursts.csv (Institution, First year, Papers, Strength, Begin, End), Institution_Bursts_yearly.csv (papers per year of the institutions shown), Institution_Bursts.html (the page).
Run   : python3 Institution_Bursts.py [--top N] [--gamma G] [--min-papers M]
"""
import argparse
import html
import math
import unicodedata
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Institution_Bursts.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


def pivot_labels(s):
    """a PivotTable ignores upper/lower case: 'Water' and 'WATER' are one item, labelled with the spelling met first"""
    return s.groupby(s.str.lower()).transform("first")


def ln_comb(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def bursts_of(r, total, years, s=2.0, gamma=0.7):
    """Kleinberg's burst detection (two states) for one series. r = papers of the item in every year, total = all papers in every year.
    State 0: the item appears with its overall share p0 of the papers; state 1 (burst): with the share s * p0. Moving up costs gamma * ln(number of years), moving down is free.
    The cheapest path is found by dynamic programming; the strength of a burst = sum over its years of cost(state 0) - cost(state 1).
    Returns [(begin year, end year, strength), ...]."""
    n = len(r)
    p0 = r.sum() / total.sum()
    p1 = min(s * p0, 0.999)

    def cost(p, t):
        return -(ln_comb(total[t], r[t]) + r[t] * math.log(p) + (total[t] - r[t]) * math.log(1 - p))
    tau, inf = gamma * math.log(n), 1e18
    dp = [[inf, inf] for _ in range(n)]
    back = [[0, 0] for _ in range(n)]
    dp[0] = [cost(p0, 0), tau + cost(p1, 0)]
    for t in range(1, n):
        for q, p in ((0, p0), (1, p1)):
            v, prev = min((dp[t - 1][a] + (tau if (q == 1 and a == 0) else 0), a) for a in (0, 1))
            dp[t][q] = v + cost(p, t)
            back[t][q] = prev
    q = 0 if dp[-1][0] <= dp[-1][1] else 1
    state = [0] * n
    for t in range(n - 1, -1, -1):
        state[t] = q
        q = back[t][q]
    out, t = [], 0
    while t < n:
        if state[t]:
            u = t
            while u + 1 < n and state[u + 1]:
                u += 1
            out.append((years[t], years[u], sum(cost(p0, i) - cost(p1, i) for i in range(t, u + 1))))
            t = u + 1
        else:
            t += 1
    return out


def html_table(rows, years, title, head):
    """the same layout as the 'citation burst history' page of CiteSpace: a table with a strip of years (pale = before the first year, teal = after it, red = burst)"""
    y0, y1 = years[0], years[-1]
    lines = [f'<html><head><meta charset="UTF-8"></head><title>{html.escape(title)}</title><body><div align=center><h1>{html.escape(title)}</h1><table>'
             f"<th>{head}</th><th>Year</th><th>Strength</th><th>Begin</th><th>End</th><th>{y0} - {y1}</th>"]
    for name, first, strength, b, e in rows:
        pale = "".join("\u2582" for y in years if y < first)
        mid = "".join("\u2582" for y in years if first <= y < b)
        red = "".join("\u2583" for y in years if b <= y <= e)
        tail = "".join("\u2582" for y in years if y > e)
        lines.append(f"<tr><td>{html.escape(str(name))}</td><td>{first}</td><td align=right>{strength:.2f}</td><td><b>{b}</b></td><td>{e}</td><td>"
                     f'<span style="color:#CFECEC">{pale}</span><span style="color:#46C7C7">{mid}</span><span style="color:#FF0000">{red}</span><span style="color:#46C7C7">{tail}</span></td></tr>')
    lines.append("</table></div></body></html>")
    return "".join(lines)


ap = argparse.ArgumentParser()
ap.add_argument("--top", type=int, default=10)
ap.add_argument("--gamma", type=float, default=0.7)
ap.add_argument("--min-papers", type=int, default=5)
opt = ap.parse_args()

clean = read_csv(CLEAN, usecols=["Year"])
items = read_csv(SHEETS / "Affiliations" / "Affiliations.csv").dropna(subset=["Institution"]).drop_duplicates(["Institution", "EID"]).rename(columns={"Institution": "Name"})
items["Name"] = pivot_labels(items["Name"])

years = list(range(int(clean["Year"].min()), int(clean["Year"].max()) + 1))
total = clean.groupby("Year").size().reindex(years).fillna(0).to_numpy(float)                     # all papers of every year
counts = items.groupby(["Name", "Year"]).size().unstack(fill_value=0).reindex(columns=years, fill_value=0)
print(f"{len(counts)} institutions, {int((counts.sum(axis=1) >= opt.min_papers).sum())} with at least {opt.min_papers} papers are tested for bursts")
rows = []
for name, r in counts.iterrows():
    if r.sum() < opt.min_papers:
        continue
    found = bursts_of(r.to_numpy(float), total, years, gamma=opt.gamma)
    if found:
        b, e, w = max(found, key=lambda x: x[2])                                    # the strongest burst of the item
        rows.append((name, int(next(y for y in years if r[y] > 0)), int(r.sum()), w, b, e))
rows.sort(key=lambda x: (-x[3], -x[2], str(x[0])))
rows = rows[: opt.top]
table = pd.DataFrame(rows, columns=["Institution", "First year", "Papers", "Strength", "Begin", "End"]).round({"Strength": 2})
print(table.to_string(index=False))
write(table)
yearly = []
for name, first, papers, w, b, e in rows:
    for y in years:
        yearly.append((name, y, int(counts.loc[name, y]), "burst" if b <= y <= e else ("after the first year" if y >= first else "before the first year")))
write(pd.DataFrame(yearly, columns=["Institution", "Year", "Papers", "Phase"]), HERE / "Institution_Bursts_yearly.csv")
(HERE / "Institution_Bursts.html").write_text(html_table([(n, f, w, b, e) for n, f, p, w, b, e in rows], years, f"Top {len(rows)} Institutions with the Strongest Bursts", "Institution"), encoding="utf-8")
print("written Institution_Bursts.html")
