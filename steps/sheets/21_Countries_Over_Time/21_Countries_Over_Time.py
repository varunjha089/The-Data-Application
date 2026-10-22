"""Sheet "21_Countries_Over_Time": papers per year of the most productive countries (Biblioshiny "Countries' production over time"), and a timeline table.
Excel: PivotTable on Countries, rows = Country (Top N filter on the number of papers), columns = Year, values = count of EID; Grand Total column. A paper counts once for each of its countries.
Your choice: --top-countries N (default 10) and --keep-ties / --cut-ties (default cut): how many countries both tables hold.
Second table 21_Country_Timeline.csv (for the timeline plot): one row per country and year with papers, citations (TC) and TC per year = TC / (reference year - year + 1),
reference year = last year of the data + 1 (the Biblioshiny definition).
Input : Countries/Countries.csv (run Countries.py first)        Output: 21_Countries_Over_Time.csv (Country, one column per year, Grand Total), 21_Country_Timeline.csv
Run   : python3 21_Countries_Over_Time.py
"""
import argparse
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "21_Countries_Over_Time.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


import argparse
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


c = read_csv(SHEETS / "Countries" / "Countries.csv").dropna(subset=["Country"]).drop_duplicates(["Country", "EID"])
c["Country"] = pivot_labels(c["Country"])
totals = c.groupby("Country").size().rename("Total").reset_index()
ap = argparse.ArgumentParser()
ap.add_argument("--top-countries", type=int, default=10)
g = ap.add_mutually_exclusive_group()
g.add_argument("--keep-ties", dest="keep_ties", action="store_true", default=False)
g.add_argument("--cut-ties", dest="keep_ties", action="store_false")
opt = ap.parse_args()
N = opt.top_countries
ranked = totals.sort_values(["Total", "Country"], ascending=[False, True], kind="stable")
top = (top_with_ties(ranked, "Total", N) if opt.keep_ties else ranked.head(N))["Country"].tolist()
print(f"{len(top)} countries (asked for {N}, ties {'kept' if opt.keep_ties else 'cut'})")
years = range(int(c["Year"].min()), int(c["Year"].max()) + 1)
sel = c[c["Country"].isin(top)]
p = sel.pivot_table(index="Country", columns="Year", values="EID", aggfunc="count", fill_value=0).reindex(index=top, columns=years, fill_value=0)
p["Grand Total"] = p.sum(axis=1)
write(p.reset_index())

# timeline table: country, year, papers, citations of those papers, citations per year
ref_year = int(c["Year"].max()) + 1
t = sel.assign(TC=lambda x: pd.to_numeric(x["Cited by"], errors="coerce").fillna(0))
tl = t.groupby(["Country", "Year"]).agg(Papers=("EID", "count"), TC=("TC", "sum")).reset_index()
tl["TC per year"] = (tl["TC"] / (ref_year - tl["Year"].astype(int) + 1)).round(3)
tl["order"] = tl["Country"].map({a: i for i, a in enumerate(top)})
tl = tl.sort_values(["order", "Year"]).drop(columns="order")[["Country", "Year", "Papers", "TC", "TC per year"]]
write(tl, HERE / "21_Country_Timeline.csv")
