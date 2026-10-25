"""Sheet "Affiliations" (query Affiliations): one row per paper and affiliation, with its country and its institution.
Excel: reference of Clean_Main_Data; keep Year, Source title, Cited by, Affiliations, Document Type, EID; drop papers without affiliations; split "Affiliations" at "; " into rows;
one row per (affiliation, EID); Country = the last comma part when it is a known country (aliases such as USA, FRG, UK; a US state + ZIP means United States), otherwise the nearest earlier part that is one, otherwise empty (common/names.py);
Institution = the first part that contains "univ" (a cut "Univ of" is joined with the next part), otherwise the first part with an institution keyword that is not a department, otherwise the first plain part;
spelling variants of one institution get one name; rows with no institution (country-only text, "Equal contributor") are dropped; one row per (institution, EID).
Country Source = "address" when the address names the country, "institution" when it was taken from the same institution elsewhere in the data (the table the
cleaning wrote, 01_Clean_Data/institution_countries.csv; without that file no country is filled in).
Parent Organisation = the large organisation the institution belongs to (an institute of the Chinese Academy of Sciences, CNRS, CSIC, Max Planck, ...; common/names.py),
otherwise the institution itself.
Input : 01_Clean_Data/clean_main_data.csv (and institution_countries.csv)        Output: Affiliations.csv
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
from names import canonical_names, country_with_fallback, institution_of_affiliation, parent_of_affiliation  # noqa: E402
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
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
LEARNED = SHEETS / "01_Clean_Data" / "institution_countries.csv"
learned = {k: (c, None, None) for k, c in read_csv(LEARNED)[["Key", "Country"]].itertuples(index=False)} if LEARNED.exists() else {}
found = aff["Affiliation"].map(lambda a: country_with_fallback(a, learned))
aff["Country"], aff["Country Source"] = found.map(lambda x: x[0]), found.map(lambda x: x[1])
aff["Institution"] = aff["Affiliation"].map(institution_of_affiliation)
aff = aff.dropna(subset=["Institution"])                                  # country-only text and notes such as "Equal contributor" are not institutions
aff["Institution"] = aff["Institution"].map(canonical_names(aff["Institution"]))     # one name for every spelling of an institution
aff["Parent Organisation"] = aff["Affiliation"].map(parent_of_affiliation).fillna(aff["Institution"])
print(f"countries taken from the same institution elsewhere: {int((aff['Country Source'] == 'institution').sum())} rows; "
      f"institutions with a parent organisation: {int((aff['Parent Organisation'] != aff['Institution']).sum())} rows")
aff = aff.drop_duplicates(["Institution", "EID"]).reset_index(drop=True)
print(f"{aff['EID'].nunique()} papers with affiliations -> {len(aff)} rows, {aff['Institution'].nunique()} different institutions")
write(aff)
