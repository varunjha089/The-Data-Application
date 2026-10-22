"""Sheet "Document_Types": the number of papers of each document type (EDA of the study: pie chart "Document Types").
Excel: PivotTable on Clean_Main_Data, rows = Document Type, values = count of EID; largest first.
Input : 01_Clean_Data/clean_main_data.csv        Output: Document_Types.csv
Run   : python3 Document_Types.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Document_Types.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")



d = read_csv(CLEAN, usecols=["Document Type"]).dropna()
d["Document Type"] = d["Document Type"].str.strip().str.title()
t = d["Document Type"].value_counts().rename_axis("Document Type").reset_index(name="Papers")
t["Share %"] = (t["Papers"] / t["Papers"].sum() * 100).round(1)
print(t.to_string(index=False))
write(t)
