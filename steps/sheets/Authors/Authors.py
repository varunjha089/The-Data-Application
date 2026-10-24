"""Sheet "Authors" (query Authors): one row per paper and author.
Excel: reference of Clean_Main_Data; keep Author full names, Title, Year, Source title, Cited by, Document Type, EID; split "Author full names" at "; " into rows;
split each entry at its last " (" into Author Name and Author ID (the ID is what is counted, never the name).
The name is written "First Last" ("Smith, Jane" -> "Jane Smith"); an entry without a comma stays as it is.
Input : 01_Clean_Data/clean_main_data.csv        Output: Authors.csv
Run   : python3 Authors.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Authors.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


d = read_csv(CLEAN)[["Author full names", "Title", "Year", "Source title", "Cited by", "Document Type", "EID"]]
def first_last(name):
    """'Kuenzer, Claudia' -> 'Claudia Kuenzer' (split at the first comma)"""
    if name and ", " in name:
        last, first = name.split(", ", 1)
        return f"{first} {last}"
    return name


rows = []
for names, title, year, source, cited, dtype, eid in d.itertuples(index=False):
    for entry in ([None] if pd.isna(names) else names.split("; ")):
        entry = None if pd.isna(entry) else (entry.strip() or None)
        if entry is None:
            name = ident = None
        elif " (" in entry:
            name, ident = entry.rsplit(" (", 1)
            ident = ident.replace(")", "")
        else:
            name, ident = entry, None
        rows.append((first_last(name), ident, title, year, source, cited, dtype, eid))
authors = pd.DataFrame(rows, columns=["Author Name", "Author ID", "Title", "Year", "Source title", "Cited by", "Document Type", "EID"])
print(f"{len(d)} papers -> {len(authors)} author entries, {authors['Author ID'].nunique()} different Scopus Author IDs, {authors['Author ID'].isna().sum()} entries without an ID")
write(authors)
