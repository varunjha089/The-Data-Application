"""Sheet "17_Top_Affiliations": the most productive institutions (Biblioshiny "Most Relevant Affiliations").
Excel: PivotTable on Affiliations, rows = Institution (Top 10 filter on Documents, ties kept), values = count of EID (Documents) and sum of Cited by (Total Citations);
sorted by Documents. Upper/lower case is ignored. The Grand Total row is not written.
--by parent counts by Parent Organisation instead (the institutes of the Chinese Academy of Sciences, CNRS, CSIC, ... together; a paper counts once per parent);
the first column is then called "Parent Organisation" and a column Institutes says how many of its institutes are in the data.
Input : Affiliations/Affiliations.csv (run Affiliations.py first)        Output: 17_Top_Affiliations.csv
Run   : python3 17_Top_Affiliations.py [--by institution|parent]
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
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
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


ap = argparse.ArgumentParser()
ap.add_argument("--by", choices=["institution", "parent"], default="institution")
BY = ap.parse_args().by
aff = read_csv(SHEETS / "Affiliations" / "Affiliations.csv")
aff["Institution"] = pivot_labels(aff["Institution"])
if BY == "parent":
    if "Parent Organisation" not in aff.columns:
        raise SystemExit("Affiliations.csv has no Parent Organisation column: generate the Affiliations sheet again.")
    aff["Parent Organisation"] = pivot_labels(aff["Parent Organisation"])
    aff = aff.drop_duplicates(["Parent Organisation", "EID"]).assign(Institutes=aff.groupby("Parent Organisation")["Institution"].transform("nunique"))
    col = "Parent Organisation"
    table = aff.groupby(col).agg(Documents=("EID", "size"), **{"Total Citations": ("Cited by", "sum")}, Institutes=("Institutes", "first")).reset_index()
else:
    col = "Institution"
    table = aff.groupby(col).agg(Documents=("EID", "size"), **{"Total Citations": ("Cited by", "sum")}).reset_index()
table = table.sort_values(["Documents", col], ascending=[False, True], kind="stable")
write(top_with_ties(table, "Documents", 10).reset_index(drop=True))
