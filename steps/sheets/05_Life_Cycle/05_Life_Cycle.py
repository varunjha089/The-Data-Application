"""Sheet "05_Life_Cycle": logistic (S-shaped) growth model of the cumulative number of documents (Biblioshiny "Life cycle of scientific production").
Excel: Cumulative = running total of the yearly documents; Fitted = k / (1 + EXP(-r * (Year - t0))); Squared Error = (Cumulative - Fitted)^2; Solver minimises the sum of the
squared errors (SSE) by changing k, r and t0. Here k is found exactly for each (r, t0) by least squares and (r, t0) by a Nelder-Mead search (numpy only), which reaches the same minimum.
Also: R2 = 1 - SSE / DEVSQ(Cumulative); Peak annual output = k * r / 4; Year 90% of K is reached = t0 + LN(9) / r.
Input : 01_Clean_Data/clean_main_data.csv        Output: 05_Life_Cycle.csv (the table) and 05_Life_Cycle_parameters.csv (k, r, t0, SSE, R2, ...)
Run   : python3 05_Life_Cycle.py
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
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


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


clean = read_csv(CLEAN)
per_year = clean.groupby("Year").size()
years = np.arange(per_year.index.min(), per_year.index.max() + 1)
documents = per_year.reindex(years, fill_value=0).to_numpy()
cumulative = documents.cumsum().astype(float)
best = None
for r0 in (0.2, 0.35, 0.5, 0.8):
    for t00 in (years[-1] - 2, years[-1], years[-1] + 2, years[-1] + 5):
        p, v = nelder_mead(lambda q: sse_and_k(q, years, cumulative)[0], [r0, float(t00)], [0.05, 0.5])
        if p[0] > 0 and (best is None or v < best[1]):
            best = (p, v)
(r, t0), sse = best
sse, k = sse_and_k((r, t0), years, cumulative)
fitted = k / (1 + np.exp(-r * (years - t0)))
table = pd.DataFrame({"Year": years, "Documents": documents, "Cumulative": cumulative.astype(int), "Fitted": fitted, "Squared Error": (cumulative - fitted) ** 2})
params = pd.DataFrame([("k", k), ("r", r), ("t0", t0), ("SSE", sse), ("R2", 1 - sse / ((cumulative - cumulative.mean()) ** 2).sum()),
                       ("Peak annual output", k * r / 4), ("Year 90% of K is reached", t0 + math.log(9) / r)], columns=["Parameter", "Value"])
print(params.to_string(index=False))
write(table)
write(params, HERE / "05_Life_Cycle_parameters.csv")
