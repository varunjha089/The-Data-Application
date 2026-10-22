"""Sheet "09_Bradford": Bradford's law: sources ranked by productivity and divided into three zones that each hold about a third of the documents.
Excel formulas on the sorted pivot: Rank = ROWS; Cumulative Documents = running sum; Cumulative Share = Cumulative / total documents;
Zone = "Zone 1" if the share is up to 1/3, "Zone 2" up to 2/3, otherwise "Zone 3"; the summary counts sources and documents per zone.
Input : 09_Pivot/09_Pivot.csv (run 09_Pivot.py first)        Output: 09_Bradford.csv and 09_Bradford_zones.csv
Note  : sources with the same number of documents are ordered by name (Excel's order among ties is arbitrary); ranks, shares and zones do not depend on it.
Run   : python3 09_Bradford.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "09_Bradford.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


pivot = read_csv(SHEETS / "09_Pivot" / "09_Pivot.csv")
table = pivot.rename(columns={"Source title": "Source"}).copy()
table["Rank"] = range(1, len(table) + 1)
table["Cumulative Documents"] = table["Documents"].cumsum()
table["Cumulative Share"] = table["Cumulative Documents"] / table["Documents"].sum()
table["Zone"] = table["Cumulative Share"].map(lambda s: "Zone 1" if s <= 1 / 3 else ("Zone 2" if s <= 2 / 3 else "Zone 3"))
zones = table.groupby("Zone").agg(Sources=("Source", "size"), Documents=("Documents", "sum")).reset_index()
print(zones.to_string(index=False))
write(table)
write(zones, HERE / "09_Bradford_zones.csv")
