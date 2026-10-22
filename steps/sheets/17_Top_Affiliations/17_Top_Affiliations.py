"""Sheet "17_Top_Affiliations": the most productive institutions (Biblioshiny "Most Relevant Affiliations").
Excel: PivotTable on Affiliations, rows = Institution (Top 10 filter on Documents, ties kept), values = count of EID (Documents) and sum of Cited by (Total Citations);
sorted by Documents. Upper/lower case is ignored. The Grand Total row is not written.
Input : Affiliations/Affiliations.csv (run Affiliations.py first)        Output: 17_Top_Affiliations.csv
Run   : python3 17_Top_Affiliations.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "17_Top_Affiliations.csv"
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
table = aff.groupby("Institution").agg(Documents=("EID", "size"), **{"Total Citations": ("Cited by", "sum")}).reset_index()
table = table.sort_values(["Documents", "Institution"], ascending=[False, True], kind="stable")
write(top_with_ties(table, "Documents", 10).reset_index(drop=True))
