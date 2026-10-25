"""Sheet "23_Top_Cited" (query Top_Cited): the 20 most cited documents (Biblioshiny "Most global cited documents").
Excel: reference of Clean_Main_Data; keep Authors, Title, Year, Source title, Cited by, DOI, Document Type; sort by Cited by (largest first, ties keep their order);
keep the first 20; TC per Year = ROUND(Cited by / max(2026 - Year + 1, 1), 1) (floored at 1: early-access items dated after 2026 would otherwise divide by zero); First Author = the text of Authors before the first ";".
Input : 01_Clean_Data/clean_main_data.csv        Output: 23_Top_Cited.csv
Run   : python3 23_Top_Cited.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "23_Top_Cited.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


clean = read_csv(CLEAN)
t = clean.sort_values("Cited by", ascending=False, kind="stable").head(20).copy()
t["TC per Year"] = (t["Cited by"] / (2026 - t["Year"] + 1).clip(lower=1)).round(1)
t["First Author"] = t["Authors"].str.split(";").str[0]
write(t[["Title", "Year", "Source title", "Cited by", "DOI", "Document Type", "TC per Year", "First Author"]].reset_index(drop=True))
