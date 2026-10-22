"""Sheet "07_Top_Sources": the most productive sources (Biblioshiny "Most Relevant Sources").
Excel: PivotTable on Clean_Main_Data, rows = Source title, values = sum of Cited by (Total Citations) and count of EID (Documents), "Top 10" filter on Documents
(Excel keeps all sources that tie with the 10th, so there can be more than 10 rows); sorted by Documents. Upper/lower case is ignored. The Grand Total row is not written.
Input : 01_Clean_Data/clean_main_data.csv        Output: 07_Top_Sources.csv
Note  : papers without a Source title (missing in the export) are left out of every source table; their number is printed.
Run   : python3 07_Top_Sources.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "07_Top_Sources.csv"
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
table = d.groupby("Source title").agg(**{"Total Citations": ("Cited by", "sum")}, Documents=("EID", "size")).reset_index()
table = table.sort_values(["Documents", "Source title"], ascending=[False, True], kind="stable")
table = top_with_ties(table, "Documents", 10).reset_index(drop=True)
write(table)
