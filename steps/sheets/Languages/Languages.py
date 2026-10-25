"""Sheet "Languages": the number of papers in each language of the original document (EDA of the study: pie chart of the languages).
Excel: PivotTable on Clean_Main_Data, rows = Language of Original Document, values = count of EID; largest first. A paper without a language is counted as "Not stated".
Your choice: --top-languages N (default 8): the N most frequent languages keep their own slice in the pie, all others are grouped as "Other languages" (column "Shown as").
Input : 01_Clean_Data/clean_main_data.csv        Output: Languages.csv (Language, Papers, Share %, Shown as)
Run   : python3 Languages.py [--top-languages N]
"""
import argparse
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Languages.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")



ap = argparse.ArgumentParser()
ap.add_argument("--top-languages", type=int, default=8)
N = max(ap.parse_args().top_languages, 1)
d = read_csv(CLEAN, usecols=["Language of Original Document"])
d["Language"] = d["Language of Original Document"].fillna("Not stated").str.strip().replace("", "Not stated")
t = d["Language"].value_counts().rename_axis("Language").reset_index(name="Papers")
t["Share %"] = (t["Papers"] / t["Papers"].sum() * 100).round(1)
t["Shown as"] = [lang if i < N else "Other languages" for i, lang in enumerate(t["Language"])]
print(t.to_string(index=False))
write(t)
