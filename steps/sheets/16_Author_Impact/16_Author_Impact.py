"""Sheet "16_Author_Impact" (query Author_Impact): the 20 authors with the highest h-index.
Excel: reference of Author_Summary; sort by h_index then TC (both largest first); keep the first 20 rows; columns Author, Author ID, NP, TC, PY_start, h_index, g_index, m_index.
Input : Author_Summary/Author_Summary.csv        Output: 16_Author_Impact.csv
Run   : python3 16_Author_Impact.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "16_Author_Impact.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


summary = read_csv(SHEETS / "Author_Summary" / "Author_Summary.csv")
table = summary.sort_values(["h_index", "TC"], ascending=False, kind="stable").head(20)
write(table[["Author", "Author ID", "NP", "TC", "PY_start", "h_index", "g_index", "m_index"]].reset_index(drop=True))
