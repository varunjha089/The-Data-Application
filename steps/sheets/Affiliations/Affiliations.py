"""Sheet "Affiliations" (query Affiliations): one row per paper and affiliation, with its country and its institution.
Excel: reference of Clean_Main_Data; keep Year, Source title, Cited by, Affiliations, Document Type, EID; drop papers without affiliations; split "Affiliations" at "; " into rows;
one row per (affiliation, EID); Country = text after the last comma (the whole text when there is no comma);
Institution = the first part that contains "univ"; otherwise the first part that contains one of the keywords below; otherwise the first part; one row per (institution, EID).
Input : 01_Clean_Data/clean_main_data.csv        Output: Affiliations.csv
Run   : python3 Affiliations.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Affiliations.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


KEYS = ["institut", "academy", "cnrs", "cnes", "nasa", "noaa", "consiglio", "council", "agency", "ministry", "survey", "observator", "laborator", "college",
        "polytechn", "school of", "center", "centre", "research"]


def institution(affiliation):
    parts = [p.strip() for p in affiliation.split(",")]
    universities = [p for p in parts if "univ" in p.lower()]
    others = [p for p in parts if any(k in p.lower() for k in KEYS)]
    return universities[0] if universities else (others[0] if others else parts[0])


d = read_csv(CLEAN)[["Year", "Source title", "Cited by", "Affiliations", "Document Type", "EID"]].dropna(subset=["Affiliations"])
rows = []
for year, source, cited, affiliations, dtype, eid in d.itertuples(index=False):
    for a in affiliations.split("; "):
        a = a.strip()
        if a:
            rows.append((year, source, cited, a, dtype, eid))
aff = pd.DataFrame(rows, columns=["Year", "Source title", "Cited by", "Affiliation", "Document Type", "EID"]).drop_duplicates(["Affiliation", "EID"])
aff["Country"] = aff["Affiliation"].map(lambda a: a.rsplit(",", 1)[1].strip() if "," in a else a)
aff["Institution"] = aff["Affiliation"].map(institution)
aff = aff.drop_duplicates(["Institution", "EID"]).reset_index(drop=True)
print(f"{aff['EID'].nunique()} papers with affiliations -> {len(aff)} rows, {aff['Institution'].nunique()} different institutions")
write(aff)
