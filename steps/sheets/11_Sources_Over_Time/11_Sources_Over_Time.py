"""Sheet "11_Sources_Over_Time": cumulative production of the five most productive sources (Biblioshiny "Source production over time").
Excel: PivotTable on Clean_Main_Data, rows = Year, columns = Source title (Top 5 filter on Documents, ties kept), values = count of EID shown as a running total over the years;
the pivot adds a Grand Total column (written here as the sum of the sources).
Second table 11_Source_Timeline.csv (for the timeline plot, your choice of how many sources: --top-sources N, default 10, and --keep-ties / --cut-ties, default cut):
one row per source and year with papers, citations (TC) and TC per year = TC / (reference year - year + 1), reference year = last year of the data + 1.
Input : 01_Clean_Data/clean_main_data.csv        Output: 11_Sources_Over_Time.csv
Note  : papers without a Source title (missing in the export) are left out; their number is printed.
Run   : python3 11_Sources_Over_Time.py
"""
import argparse
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "11_Sources_Over_Time.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


import unicodedata


def pivot_labels(s):
    """a PivotTable ignores upper/lower case: 'Water' and 'WATER' are one item, labelled with the spelling met first"""
    return s.groupby(s.str.lower()).transform("first")


def sort_key(s):
    """sort like Excel: ignore accents and case ('Université' sorts as 'universite')"""
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch)).casefold()


def top_with_ties(df, col, n):
    """Excel's 'Top 10' filter keeps every item that ties with the n-th one"""
    cut = df[col].nlargest(n).min()
    return df[df[col] >= cut]


clean = read_csv(CLEAN)
print(f"left out: {int(clean['Source title'].isna().sum())} papers without a Source title")
d = clean.dropna(subset=["Source title"]).copy()
d["Source title"] = pivot_labels(d["Source title"])
totals = d.groupby("Source title").size().rename("Documents").reset_index()
top = top_with_ties(totals.sort_values(["Documents", "Source title"], ascending=[False, True], kind="stable"), "Documents", 5)["Source title"]
years = range(int(clean["Year"].min()), int(clean["Year"].max()) + 1)
p = d[d["Source title"].isin(top)].pivot_table(index="Year", columns="Source title", values="EID", aggfunc="count", fill_value=0).reindex(years, fill_value=0)
p = p[sorted(p.columns, key=sort_key)].cumsum()
p["Grand Total"] = p.sum(axis=1)
write(p.reset_index())

# timeline table: source, year, papers, citations of those papers, citations per year
ap = argparse.ArgumentParser()
ap.add_argument("--top-sources", type=int, default=10)
g = ap.add_mutually_exclusive_group()
g.add_argument("--keep-ties", dest="keep_ties", action="store_true", default=False)
g.add_argument("--cut-ties", dest="keep_ties", action="store_false")
opt = ap.parse_args()
N = opt.top_sources
ranked = totals.sort_values(["Documents", "Source title"], ascending=[False, True], kind="stable")
chosen = (top_with_ties(ranked, "Documents", N) if opt.keep_ties else ranked.head(N))["Source title"].tolist()
print(f"timeline: {len(chosen)} sources (asked for {N}, ties {'kept' if opt.keep_ties else 'cut'})")
ref_year = int(clean["Year"].max()) + 1
t = d[d["Source title"].isin(chosen)].assign(TC=lambda x: pd.to_numeric(x["Cited by"], errors="coerce").fillna(0))
tl = t.groupby(["Source title", "Year"]).agg(Papers=("EID", "count"), TC=("TC", "sum")).reset_index()
tl["TC per year"] = (tl["TC"] / (ref_year - tl["Year"].astype(int) + 1)).round(3)
tl["order"] = tl["Source title"].map({a: i for i, a in enumerate(chosen)})
tl = tl.sort_values(["order", "Year"]).drop(columns="order")[["Source title", "Year", "Papers", "TC", "TC per year"]]
write(tl, HERE / "11_Source_Timeline.csv")
