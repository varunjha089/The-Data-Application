"""Sheet "Countries" (query Countries): one row per paper and country (a paper counts once for each of its countries).
Excel: reference of Clean_Main_Data; keep Year, Source title, Cited by, Document Type, EID, Countries, Corresponding Country, Country Count, Collaboration Type;
split "Countries" at "; " into rows; remove empty values; rename Countries to Country.
Input : 01_Clean_Data/clean_main_data.csv        Output: Countries.csv
Run   : python3 Countries.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Countries.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


d = read_csv(CLEAN)[["Year", "Source title", "Cited by", "Document Type", "EID", "Countries", "Corresponding Country", "Country Count", "Collaboration Type"]]
rows = []
for year, source, cited, dtype, eid, countries, corr, count, collab in d.itertuples(index=False):
    if pd.isna(countries):
        continue
    for c in countries.split("; "):
        c = c.strip()
        if c:
            rows.append((year, source, cited, dtype, eid, c, corr, count, collab))
countries = pd.DataFrame(rows, columns=["Year", "Source title", "Cited by", "Document Type", "EID", "Country", "Corresponding Country", "Country Count", "Collaboration Type"])
print(f"{countries['EID'].nunique()} papers with a country -> {len(countries)} paper-country rows, {countries['Country'].nunique()} different countries")
write(countries)
