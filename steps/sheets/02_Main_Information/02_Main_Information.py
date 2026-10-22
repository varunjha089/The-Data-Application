"""Sheet "02_Main_Information": the main numbers of the data set (Biblioshiny "Main Information").
Excel formulas: Timespan = MIN(Year):MAX(Year); Sources = number of different Source titles (case ignored); Documents = number of rows of Clean_Main_Data;
Annual Growth Rate % = ((documents in the last year / documents in the first year) ^ (1 / (last year - first year)) - 1) * 100; Document Average Age = 2026 - average Year;
Average citations per doc = average of Cited by; References = rows of References; Authors = rows of Author_Summary; Single-authored docs = papers that appear once in Authors;
Co-Authors per Doc = rows of Authors / documents; International co-authorships % = MCP / (MCP + SCP) * 100 (Collaboration Type of the papers); Countries = different countries in Countries;
Document types = number of papers of each Document Type.
Input : 01_Clean_Data/clean_main_data.csv, Authors/, Author_Summary/, Countries/, References/        Output: 02_Main_Information.csv (Section, Parameter, Value)
Note  : papers without a Source title (missing in the export) are not counted as a source.
Run   : python3 02_Main_Information.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "02_Main_Information.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


clean = read_csv(CLEAN)
authors = read_csv(SHEETS / "Authors" / "Authors.csv")
summary = read_csv(SHEETS / "Author_Summary" / "Author_Summary.csv")
countries = read_csv(SHEETS / "Countries" / "Countries.csv")
references = read_csv(SHEETS / "References" / "References.csv")

year = clean["Year"]
first, last = int(year.min()), int(year.max())
growth = round((((year == last).sum() / (year == first).sum()) ** (1 / (last - first)) - 1) * 100, 2)
collab = clean["Collaboration Type"]
mcp, scp = (collab == "MCP").sum(), (collab == "SCP").sum()
missing_source = int(clean["Source title"].isna().sum())

rows = [
    ("Main information", "Timespan", f"{first}:{last}"),
    ("Main information", "Sources (Journals, Books, etc)", clean["Source title"].str.lower().nunique()),
    ("Main information", "Documents", len(clean)),
    ("Main information", "Annual Growth Rate %", growth),
    ("Main information", "Document Average Age", round(2026 - year.mean(), 2)),
    ("Main information", "Average citations per doc", round(clean["Cited by"].mean(), 2)),
    ("Main information", "References", len(references)),
    ("Main information", "Authors", len(summary)),
    ("Main information", "Single-authored docs", int((authors.groupby("EID").size() == 1).sum())),
    ("Main information", "Co-Authors per Doc", round(len(authors) / len(clean), 2)),
    ("Main information", "International co-authorships %", round(mcp / (mcp + scp) * 100, 2)),
    ("Main information", "Countries", countries["Country"].nunique()),
]
types = clean["Document Type"].value_counts()
rows += [("Document types", t, int(n)) for t, n in types.items()] + [("Document types", "Total", int(types.sum()))]
print(f"papers without a Source title (not counted as a source): {missing_source}")
write(pd.DataFrame(rows, columns=["Section", "Parameter", "Value"]))
