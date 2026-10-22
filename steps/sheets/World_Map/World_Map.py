"""Sheet "World_Map" (new): the number of documents of every country, the table behind the world map.
Excel: PivotTable on Countries, rows = Country, values = count of EID; sorted by Documents (largest first). A paper counts once for each of its countries.
Input : Countries/Countries.csv (run Countries.py first)        Output: World_Map.csv (Country, Documents, Share of papers %)
Option: --top-countries N (default 15): the column "In map" is 1 for the N most productive countries (the map shows those).
Run   : python3 World_Map.py
"""
import argparse
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "World_Map.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


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


c = read_csv(SHEETS / "Countries" / "Countries.csv")
c["Country"] = pivot_labels(c["Country"])
ap = argparse.ArgumentParser()
ap.add_argument("--top-countries", type=int, default=15)
opt = ap.parse_args()
papers = read_csv(CLEAN, usecols=["EID"]).shape[0]
table = c.groupby("Country").size().rename("Documents").reset_index().sort_values(["Documents", "Country"], ascending=[False, True], kind="stable").reset_index(drop=True)
table["Share of papers %"] = (table["Documents"] / papers * 100).round(2)
table["In map"] = (table.index < opt.top_countries).astype(int)
print(f"{len(table)} countries; the {opt.top_countries} most productive hold {int(table['Documents'].head(opt.top_countries).sum())} paper-country entries")
write(table)
