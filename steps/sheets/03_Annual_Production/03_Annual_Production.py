"""Sheet "03_Annual_Production": documents and total citations per year (Biblioshiny "Annual Scientific Production").
Excel: PivotTable on Clean_Main_Data, rows = Year, values = count of EID (Documents) and sum of Cited by (Total Citations); the pivot adds a Grand Total row, not written here.
Input : 01_Clean_Data/clean_main_data.csv        Output: 03_Annual_Production.csv
Run   : python3 03_Annual_Production.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "03_Annual_Production.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


clean = read_csv(CLEAN)
table = clean.groupby("Year").agg(Documents=("EID", "size"), **{"Total Citations": ("Cited by", "sum")}).reset_index()
print(f"{table['Documents'].sum()} documents, {table['Total Citations'].sum()} citations")
write(table)
