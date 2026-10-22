"""Sheet "15_Lotka": Lotka's law: how many authors wrote 1, 2, 3 ... papers.
Excel: N. of Authors = COUNTIF(Author_Summary[NP], n); Proportion of Authors = N / total; Lotka (beta = 2) = 0.6079 / n^2;
beta (slope) = minus the slope of LN(proportion) against LN(n); C = EXP(intercept); R2 of that straight line.
Input : Author_Summary/Author_Summary.csv (run Author_Summary.py first)        Output: 15_Lotka.csv and 15_Lotka_parameters.csv
Run   : python3 15_Lotka.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "15_Lotka.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


import numpy as np

summary = read_csv(SHEETS / "Author_Summary" / "Author_Summary.csv")
counts = summary["NP"].value_counts().sort_index()
table = pd.DataFrame({"Documents written": counts.index, "N. of Authors": counts.values})
table["Proportion of Authors"] = table["N. of Authors"] / table["N. of Authors"].sum()
table["Lotka (β = 2)"] = 0.6079 / table["Documents written"] ** 2
x, y = np.log(table["Documents written"].astype(float)), np.log(table["Proportion of Authors"])
slope, intercept = np.polyfit(x, y, 1)
r2 = float(np.corrcoef(x, y)[0, 1] ** 2)
params = pd.DataFrame([("β (slope)", -slope), ("C", float(np.exp(intercept))), ("R²", r2)], columns=["Parameter", "Value"])
print(params.to_string(index=False))
write(table)
write(params, HERE / "15_Lotka_parameters.csv")
