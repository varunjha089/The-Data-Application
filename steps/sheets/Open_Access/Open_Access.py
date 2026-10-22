"""Sheet "Open_Access": the papers by open access status (EDA of the study: pie chart "Open Access Status").
Scopus writes a compound text ("All Open Access; Gold Open Access; Green ..."): each paper gets ONE class, the first that applies in this order:
Hybrid Gold, Gold OA, Bronze OA, Green OA; a paper with no open access text is "Closed / Unknown".
Input : 01_Clean_Data/clean_main_data.csv        Output: Open_Access.csv
Run   : python3 Open_Access.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Open_Access.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")



def classify_oa(raw):
    s = "" if pd.isna(raw) else str(raw).strip()
    if not s:
        return "Closed / Unknown"
    if "Hybrid Gold" in s:
        return "Hybrid Gold"
    if "Gold Open Access" in s:
        return "Gold OA"
    if "Bronze Open Access" in s:
        return "Bronze OA"
    if "Green" in s:
        return "Green OA"
    return "Closed / Unknown"


ORDER = ["Gold OA", "Hybrid Gold", "Bronze OA", "Green OA", "Closed / Unknown"]
d = read_csv(CLEAN, usecols=["Open Access"])
d["Open access class"] = d["Open Access"].map(classify_oa)
t = d["Open access class"].value_counts().reindex(ORDER).dropna().astype(int).rename("Papers").reset_index()
t["Share %"] = (t["Papers"] / t["Papers"].sum() * 100).round(1)
print(t.to_string(index=False))
write(t)
