"""Sheet "10_Source_Impact" (query Source_Impact): production and impact of every source (Biblioshiny "Sources' Local Impact").
Excel: reference of Clean_Main_Data; keep Year, Source title, Cited by, EID; group by Source title: NP = number of papers, TC = total citations, PY_start = first year,
h_index, g_index, m_index = h / max(2026 - PY_start + 1, 1) (floored at 1: early-access items dated after 2026 would otherwise divide by zero); sorted by h_index (largest first).
Option: --top-sources N (default 15): the column "In plots" is 1 for the N sources with the highest h-index (then most citations, then name); the plots show those.
Input : 01_Clean_Data/clean_main_data.csv        Output: 10_Source_Impact.csv
Note  : papers without a Source title (missing in the export) are left out; their number is printed.
Run   : python3 10_Source_Impact.py
"""
import argparse
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "10_Source_Impact.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


def h_index(cites):
    """largest h such that h papers have at least h citations each"""
    s = sorted(cites, reverse=True)
    return sum(1 for i, v in enumerate(s) if v >= i + 1)


def g_index(cites):
    """largest g such that the g most cited papers together have at least g squared citations"""
    s = sorted(cites, reverse=True)
    total, best = 0, 0
    for i, v in enumerate(s, 1):
        total += v
        if total >= i * i:
            best = i
    return best


clean = read_csv(CLEAN)
print(f"left out: {int(clean['Source title'].isna().sum())} papers without a Source title")
rows = []
for source, g in clean.dropna(subset=["Source title"]).groupby("Source title", sort=False):
    cites = g["Cited by"].tolist()
    h, py = h_index(cites), int(g["Year"].min())
    rows.append((source, len(g), int(sum(cites)), py, h, g_index(cites), round(h / max(2026 - py + 1, 1), 3)))
table = pd.DataFrame(rows, columns=["Source title", "NP", "TC", "PY_start", "h_index", "g_index", "m_index"])
table = table.sort_values("h_index", ascending=False, kind="stable").reset_index(drop=True)
ap = argparse.ArgumentParser()
ap.add_argument("--top-sources", type=int, default=15)
opt = ap.parse_args()
ranked = table.sort_values(["h_index", "TC", "Source title"], ascending=[False, False, True], kind="stable").index[: opt.top_sources]
table["In plots"] = table.index.isin(ranked).astype(int)
write(table)
