"""Sheet "14_Author_Over_Time": papers per year of the most productive authors (how many: your choice, default 15) (Biblioshiny "Authors' production over time").
Excel: PivotTable on Authors, rows = Author ID (Top 10 filter on the number of papers, ties kept), columns = Year, values = count of EID; Grand Total column;
column Author = the name from Author_Summary (INDEX/MATCH on the Author ID). Authors are counted by Scopus Author ID.
Second table 14_Author_Timeline.csv (for the timeline plot): the 15 most productive authors (ties kept), one row per author and year with papers, citations (TC) and
TC per year = TC / (reference year - year + 1), reference year = last year of the data + 1 (the Biblioshiny definition).
Options: --top-authors N (default 15) and --keep-ties / --cut-ties (default cut): how many authors the timeline table holds. Without ties kept the
         authors at the end of the list that tie are cut at exactly N (most papers first, then the lower Author ID).
Input : Authors/Authors.csv, Author_Summary/Author_Summary.csv        Output: 14_Author_Over_Time.csv
Note  : entries without an Author ID are left out.
Run   : python3 14_Author_Over_Time.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "14_Author_Over_Time.csv"
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


au = read_csv(SHEETS / "Authors" / "Authors.csv").dropna(subset=["Author ID"])
summary = read_csv(SHEETS / "Author_Summary" / "Author_Summary.csv")
totals = au.groupby("Author ID").size().rename("Total").reset_index()
ap = argparse.ArgumentParser()
ap.add_argument("--top-authors", type=int, default=15)
g = ap.add_mutually_exclusive_group()
g.add_argument("--keep-ties", dest="keep_ties", action="store_true", default=False)
g.add_argument("--cut-ties", dest="keep_ties", action="store_false")
opt = ap.parse_args()
ranked = totals.sort_values(["Total", "Author ID"], ascending=[False, True], kind="stable")
top = (top_with_ties(ranked, "Total", opt.top_authors) if opt.keep_ties else ranked.head(opt.top_authors))["Author ID"].tolist()


years = range(int(au["Year"].min()), int(au["Year"].max()) + 1)
p = au[au["Author ID"].isin(top)].pivot_table(index="Author ID", columns="Year", values="EID", aggfunc="count", fill_value=0).reindex(index=top, columns=years, fill_value=0)
p["Grand Total"] = p.sum(axis=1)
names = summary.drop_duplicates("Author ID").set_index("Author ID")["Author"]
p["Author"] = p.index.map(names)
write(p.reset_index())

# timeline table: author, year, papers, citations of those papers, citations per year
print(f"{len(top)} authors (asked for {opt.top_authors}, ties {'kept' if opt.keep_ties else 'cut'})")
ref_year = int(au["Year"].max()) + 1
t = au[au["Author ID"].isin(top)].drop_duplicates(["Author ID", "EID"])
t = t.assign(TC=pd.to_numeric(t["Cited by"], errors="coerce").fillna(0))
tl = t.groupby(["Author ID", "Year"]).agg(Papers=("EID", "count"), TC=("TC", "sum")).reset_index()
tl["TC per year"] = (tl["TC"] / (ref_year - tl["Year"].astype(int) + 1)).round(3)
tl["Author"] = tl["Author ID"].map(names)
tl["order"] = tl["Author ID"].map({a: i for i, a in enumerate(top)})
tl = tl.sort_values(["order", "Year"]).drop(columns="order")[["Author", "Author ID", "Year", "Papers", "TC", "TC per year"]]
write(tl, HERE / "14_Author_Timeline.csv")
