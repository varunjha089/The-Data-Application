"""Sheet "20_22_Countries": production and citations of the countries (Biblioshiny "Countries' scientific production" and "Most cited countries").
Excel: PivotTable on Countries, rows = Country (Top 10 filter on Documents, ties kept), values = count of EID (Documents) and sum of Cited by (Total Citations);
Avg per paper = Total Citations / Documents. A paper counts once for each of its countries. The Grand Total row is not written.
Input : Countries/Countries.csv (run Countries.py first)        Output: 20_22_Countries.csv
Run   : python3 20_22_Countries.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "20_22_Countries.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
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


c = read_csv(SHEETS / "Countries" / "Countries.csv")
c["Country"] = pivot_labels(c["Country"])
table = c.groupby("Country").agg(Documents=("EID", "size"), **{"Total Citations": ("Cited by", "sum")}).reset_index()
table = top_with_ties(table.sort_values(["Documents", "Country"], ascending=[False, True], kind="stable"), "Documents", 10).reset_index(drop=True)
table["Avg per paper"] = table["Total Citations"] / table["Documents"]
write(table.rename(columns={"Country": "Countries"}))
