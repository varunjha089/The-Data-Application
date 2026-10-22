"""Sheet "18_Affil_Over_Time": cumulative production of the five most productive institutions.
Excel: PivotTable on Affiliations, rows = Year, columns = Institution (Top 5 filter on Documents, ties kept), values = count of EID as a running total; Grand Total column.
Second table 18_Affil_Timeline.csv (for the timeline plot, your choice of how many institutions: --top-affiliations N, default 10, and --keep-ties / --cut-ties, default cut):
one row per institution and year with papers (a paper counts once for an institution), citations (TC) and TC per year = TC / (reference year - year + 1), reference year = last year of the data + 1.
Input : Affiliations/Affiliations.csv        Output: 18_Affil_Over_Time.csv
Run   : python3 18_Affil_Over_Time.py
"""
import argparse
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "18_Affil_Over_Time.csv"
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


aff = read_csv(SHEETS / "Affiliations" / "Affiliations.csv")
aff["Institution"] = pivot_labels(aff["Institution"])
totals = aff.groupby("Institution").size().rename("Documents").reset_index().sort_values(["Documents", "Institution"], ascending=[False, True], kind="stable")
top = top_with_ties(totals, "Documents", 5)["Institution"]
years = range(int(aff["Year"].min()), int(aff["Year"].max()) + 1)
p = aff[aff["Institution"].isin(top)].pivot_table(index="Year", columns="Institution", values="EID", aggfunc="count", fill_value=0).reindex(years, fill_value=0)
p = p[sorted(p.columns, key=sort_key)].cumsum()
p["Grand Total"] = p.sum(axis=1)
write(p.reset_index())

# timeline table: institution, year, papers, citations of those papers, citations per year
ap = argparse.ArgumentParser()
ap.add_argument("--top-affiliations", type=int, default=10)
g = ap.add_mutually_exclusive_group()
g.add_argument("--keep-ties", dest="keep_ties", action="store_true", default=False)
g.add_argument("--cut-ties", dest="keep_ties", action="store_false")
opt = ap.parse_args()
N = opt.top_affiliations
ranked = totals
chosen = (top_with_ties(ranked, "Documents", N) if opt.keep_ties else ranked.head(N))["Institution"].tolist()
print(f"timeline: {len(chosen)} institutions (asked for {N}, ties {'kept' if opt.keep_ties else 'cut'})")
ref_year = int(aff["Year"].max()) + 1
t = aff[aff["Institution"].isin(chosen)].drop_duplicates(["Institution", "EID"]).assign(TC=lambda x: pd.to_numeric(x["Cited by"], errors="coerce").fillna(0))
tl = t.groupby(["Institution", "Year"]).agg(Papers=("EID", "count"), TC=("TC", "sum")).reset_index()
tl["TC per year"] = (tl["TC"] / (ref_year - tl["Year"].astype(int) + 1)).round(3)
tl["order"] = tl["Institution"].map({a: i for i, a in enumerate(chosen)})
tl = tl.sort_values(["order", "Year"]).drop(columns="order")[["Institution", "Year", "Papers", "TC", "TC per year"]]
write(tl, HERE / "18_Affil_Timeline.csv")
