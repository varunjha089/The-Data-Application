"""Sheet "04_Avg_Citations": average citations per paper and per year of age (Biblioshiny "Average Article Citations per Year").
Excel formulas, for every year: Documents = COUNTIFS(Year); Total Citations = SUMIFS(Cited by); Mean Citations per Document = Total / Documents;
Citable Years = max(2026 - Year + 1, 1) (floored at 1: early-access items dated after 2026 would otherwise divide by zero); Mean Citations per Year = Mean per Document / Citable Years.
Input : 01_Clean_Data/clean_main_data.csv        Output: 04_Avg_Citations.csv
Run   : python3 04_Avg_Citations.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "04_Avg_Citations.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


clean = read_csv(CLEAN)
years = range(int(clean["Year"].min()), int(clean["Year"].max()) + 1)
table = pd.DataFrame({"Year": list(years)})
table["Documents"] = table["Year"].map(clean.groupby("Year").size()).fillna(0).astype(int)
table["Total Citations"] = table["Year"].map(clean.groupby("Year")["Cited by"].sum()).fillna(0).astype(int)
table["Mean Citations per Document"] = table["Total Citations"] / table["Documents"]
table["Citable Years"] = (2026 - table["Year"] + 1).clip(lower=1)
table["Mean Citations per Year"] = table["Mean Citations per Document"] / table["Citable Years"]
write(table)
