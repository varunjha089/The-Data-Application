"""Sheet "05_Life_Cycle": logistic (S-shaped) growth model of the cumulative number of documents (Biblioshiny "Life cycle of scientific production").
Excel: Cumulative = running total of the yearly documents; Fitted = k / (1 + EXP(-r * (Year - t0))); Squared Error = (Cumulative - Fitted)^2; Solver minimises the sum of the
squared errors (SSE) by changing k, r and t0. Here k is found exactly for each (r, t0) by least squares and (r, t0) by a Nelder-Mead search (numpy only), which reaches the same minimum.
Also: R2 = 1 - SSE / DEVSQ(Cumulative); Peak annual output = k * r / 4; Year 90% of K is reached = t0 + LN(9) / r.
Incomplete years are left out of the fit: the current year is still being indexed and early-access papers carry next year's date, so their few papers would
bend the S-curve down and make the field look saturated. By default the fit uses the years up to the last complete year (the year before the current one);
--fit-to-year Y uses the years up to Y. The table keeps every year (column In Fit says which were used) and the fitted curve is drawn for all of them.
Saturation visible = yes only when the inflection point t0 lies within the fitted years. Before the curve has turned, the data cannot tell where it will level
off: K, t0, the peak and the 90% year are then extrapolations (they can run to absurd values) and the plot says so instead of printing them.
Input : 01_Clean_Data/clean_main_data.csv        Output: 05_Life_Cycle.csv (the table) and 05_Life_Cycle_parameters.csv (k, r, t0, SSE, R2, ...)
Run   : python3 05_Life_Cycle.py [--fit-to-year Y]
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "05_Life_Cycle.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


import argparse
import datetime
import math

import numpy as np


def sse_and_k(params, t, c):
    r, t0 = params
    f = 1.0 / (1.0 + np.exp(-r * (t - t0)))
    k = float(c @ f / (f @ f))
    return float(((c - k * f) ** 2).sum()), k


def nelder_mead(fun, x0, step, iterations=4000):
    n = len(x0)
    pts = [np.array(x0, float)] + [np.array(x0, float) + step * np.eye(n)[i] for i in range(n)]
    vals = [fun(p) for p in pts]
    for _ in range(iterations):
        order = np.argsort(vals)
        pts, vals = [pts[i] for i in order], [vals[i] for i in order]
        centre = np.mean(pts[:-1], axis=0)
        reflected = centre + (centre - pts[-1])
        fr = fun(reflected)
        if fr < vals[0]:
            expanded = centre + 2 * (centre - pts[-1])
            fe = fun(expanded)
            pts[-1], vals[-1] = (expanded, fe) if fe < fr else (reflected, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = reflected, fr
        else:
            contracted = centre + 0.5 * (pts[-1] - centre)
            fc = fun(contracted)
            if fc < vals[-1]:
                pts[-1], vals[-1] = contracted, fc
            else:
                pts = [pts[0]] + [pts[0] + 0.5 * (p - pts[0]) for p in pts[1:]]
                vals = [vals[0]] + [fun(p) for p in pts[1:]]
        if abs(vals[-1] - vals[0]) < 1e-12 * (1 + abs(vals[0])):
            break
    best = int(np.argmin(vals))
    return pts[best], vals[best]


ap = argparse.ArgumentParser()
ap.add_argument("--fit-to-year", type=int, default=0, help="last year used in the fit (0 = the last complete year, the year before the current one)")
clean = read_csv(CLEAN)
per_year = clean.groupby("Year").size()
years = np.arange(per_year.index.min(), per_year.index.max() + 1)
documents = per_year.reindex(years, fill_value=0).to_numpy()
cumulative = documents.cumsum().astype(float)
cut = ap.parse_args().fit_to_year or datetime.date.today().year - 1
use = years <= cut
if use.sum() < 5:                                                # too few complete years to fit three parameters: use them all, and say so
    print(f"only {int(use.sum())} years up to {cut}: the fit uses every year")
    use[:] = True
fy, fc = years[use], cumulative[use]
best = None
for r0 in (0.2, 0.35, 0.5, 0.8):
    for t00 in (fy[-1] - 2, fy[-1], fy[-1] + 2, fy[-1] + 5):
        p, v = nelder_mead(lambda q: sse_and_k(q, fy, fc)[0], [r0, float(t00)], [0.05, 0.5])
        if p[0] > 0 and (best is None or v < best[1]):
            best = (p, v)
(r, t0), sse = best
sse, k = sse_and_k((r, t0), fy, fc)
fitted = k / (1 + np.exp(-r * (years - t0)))
table = pd.DataFrame({"Year": years, "Documents": documents, "Cumulative": cumulative.astype(int), "Fitted": fitted, "Squared Error": (cumulative - fitted) ** 2,
                      "In Fit": np.where(use, "yes", "no")})
left = years[~use]
params = pd.DataFrame([("k", k), ("r", r), ("t0", t0), ("SSE", sse), ("R2", 1 - sse / ((fc - fc.mean()) ** 2).sum()),
                       ("Peak annual output", k * r / 4), ("Year 90% of K is reached", t0 + math.log(9) / r),
                       ("Last year in the fit", int(fy[-1])), ("Years left out of the fit", len(left)),
                       ("Saturation visible", "yes" if t0 <= fy[-1] else "no")], columns=["Parameter", "Value"])
print(f"fit on {fy[0]}-{fy[-1]}" + (f"; left out (incomplete): {', '.join(str(y) for y in left)}" if len(left) else ""))
print(params.to_string(index=False))
write(table)
write(params, HERE / "05_Life_Cycle_parameters.csv")
