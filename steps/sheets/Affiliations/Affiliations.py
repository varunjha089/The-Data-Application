"""Sheet "Affiliations" (query Affiliations): one row per paper and affiliation, with its country and its institution.
Excel: reference of Clean_Main_Data; keep Year, Source title, Cited by, Affiliations, Document Type, EID; drop papers without affiliations; split "Affiliations" at "; " into rows;
one row per (affiliation, EID); Country = the last comma part when it is a known country (aliases such as USA, FRG, UK; a US state + ZIP means United States), otherwise the nearest earlier part that is one, otherwise empty (common/names.py);
Institution = the first part that contains "univ" (a cut "Univ of" is joined with the next part), otherwise the first part with an institution keyword that is not a department, otherwise the first plain part;
spelling variants of one institution get one name; rows with no institution (country-only text, "Equal contributor") are dropped; one row per (institution, EID).
Input : 01_Clean_Data/clean_main_data.csv        Output: Affiliations.csv
Run   : python3 Affiliations.py
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Affiliations.csv"
sys.path.insert(0, str(SHEETS / "common"))                    # shared name rules, copied into the project by the application
from names import canonical_names, country_of_affiliation, institution_of_affiliation  # noqa: E402
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


d = read_csv(CLEAN)[["Year", "Source title", "Cited by", "Affiliations", "Document Type", "EID"]].dropna(subset=["Affiliations"])
rows = []
for year, source, cited, affiliations, dtype, eid in d.itertuples(index=False):
    for a in affiliations.split("; "):
        a = a.strip()
        if a:
            rows.append((year, source, cited, a, dtype, eid))
aff = pd.DataFrame(rows, columns=["Year", "Source title", "Cited by", "Affiliation", "Document Type", "EID"]).drop_duplicates(["Affiliation", "EID"])
aff["Country"] = aff["Affiliation"].map(country_of_affiliation)
aff["Institution"] = aff["Affiliation"].map(institution_of_affiliation)
aff = aff.dropna(subset=["Institution"])                                  # country-only text and notes such as "Equal contributor" are not institutions
aff["Institution"] = aff["Institution"].map(canonical_names(aff["Institution"]))     # one name for every spelling of an institution
aff = aff.drop_duplicates(["Institution", "EID"]).reset_index(drop=True)
print(f"{aff['EID'].nunique()} papers with affiliations -> {len(aff)} rows, {aff['Institution'].nunique()} different institutions")
write(aff)
