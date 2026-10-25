"""Sheet "Subject_Areas": documents by Scopus subject area, as in the "Documents by subject area" chart of Scopus.
Method: Scopus classifies SOURCES (journals, book series, conference proceedings), not papers. Every source has one or more ASJC codes (four digits, e.g.
        1907 = Geology); the first two digits give one of the 27 subject areas (19.. = Earth and Planetary Sciences). A paper takes the subject areas of its
        source, each area once, so one paper can count in several areas, exactly as in Scopus.
        The source of a paper is looked up in the Scopus Source List (an Excel file Elsevier publishes free of charge), in this order:
          1. the paper's ISSN is the ISSN or EISSN of a source (journals, book series, serial conference proceedings)
          2. the paper's Source title is the title of such a source (compared in lower case, letters and digits only)
          3. one of the paper's ISBNs is the ISBN of a conference proceedings volume (sheet "All Conf. Proceedings")
          4. the paper's Source title is the title of a conference proceedings volume
        When a key belongs to several rows of the list (e.g. a renamed journal), their codes are taken together.
        A paper found nowhere is "Not matched" (mostly books and book chapters): it is counted in its own row and left out of the shares.
Input : 01_Clean_Data/clean_main_data.csv and the Scopus Source List (option --source-list FILE: the .xlsx from Elsevier, or a CSV with its columns;
        default: the newest .xlsx / .csv in the project's data/source_list/, where the application keeps the file you choose on the sheet's page).
        The sheets of the .xlsx are found by their column headings (Source Title, ISSN, EISSN, ISBN, ASJC), not by their names, which carry a date.
        Without a source list the sheet is SKIPPED with a message: no CSV is written and the script ends normally.
Output: Subject_Areas.csv         one row per subject area: Papers; Share of Assignments (%) = Papers / all (paper, area) pairs, the percentages of the
                                  Scopus pie chart (they add up to 100); Share of Matched Papers (%) = Papers / matched papers (they add up to more than 100)
        Subject_Areas_papers.csv  one row per paper: how its source was found, its ASJC codes and subject areas
Run   : python3 Subject_Areas.py [--source-list FILE]      (needs pandas; openpyxl for an .xlsx)
"""
import argparse
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Subject_Areas.csv"
OUT_PAPERS = HERE / "Subject_Areas_papers.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}
NOT_MATCHED = "Not matched (source not in the list)"

# the 27 subject areas of Scopus: the first two digits of an ASJC code
AREAS = {"10": "Multidisciplinary", "11": "Agricultural and Biological Sciences", "12": "Arts and Humanities",
         "13": "Biochemistry, Genetics and Molecular Biology", "14": "Business, Management and Accounting", "15": "Chemical Engineering", "16": "Chemistry",
         "17": "Computer Science", "18": "Decision Sciences", "19": "Earth and Planetary Sciences", "20": "Economics, Econometrics and Finance", "21": "Energy",
         "22": "Engineering", "23": "Environmental Science", "24": "Immunology and Microbiology", "25": "Materials Science", "26": "Mathematics",
         "27": "Medicine", "28": "Neuroscience", "29": "Nursing", "30": "Pharmacology, Toxicology and Pharmaceutics", "31": "Physics and Astronomy",
         "32": "Psychology", "33": "Social Sciences", "34": "Veterinary", "35": "Dentistry", "36": "Health Professions"}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


def issn_key(v):
    """'0304-3894', '0304389X', 3043894 (a number that lost its leading zero) -> '03043894'; '' when it is not an ISSN"""
    if v is None or v == "":
        return ""
    s = f"{v:08d}" if isinstance(v, int) else re.sub(r"[^0-9X]", "", str(v).upper())
    return s if len(s) == 8 else ""


def isbn_keys(v):
    """all ISBNs of a cell ('978-1-5106-8053-1; 1510680532', or a number) as digits only"""
    if v is None or v == "":
        return []
    parts = [str(v)] if isinstance(v, (int, float)) else re.split(r"[;,]", str(v))
    keys = [re.sub(r"[^0-9X]", "", p.upper().split(".")[0] if isinstance(v, float) else p.upper()) for p in parts]
    return [k for k in keys if len(k) in (10, 13)]


def title_key(v):
    return re.sub(r"[\W_]+", "", str(v).casefold()) if v not in (None, "") else ""


def asjc_codes(v):
    return re.findall(r"\b\d{4}\b", str(v)) if v not in (None, "") else []


def role(header):
    """what a column of the source list holds, from its heading"""
    h = re.sub(r"\s+", " ", str(header or "")).strip().lower()
    if h in ("source title", "proceedings title", "proceedinds title") or h.startswith("source title ("):
        return "title"
    if h in ("issn", "eissn", "e-issn"):
        return "issn"
    if h == "isbn":
        return "isbn"
    if "asjc" in h:
        return "asjc"
    return None


def tables(path):
    """(headings, rows) of every table in the source list that has an ASJC column; the heading row may be below a few lines of notes"""
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        yield list(df.columns), df.itertuples(index=False, name=None)
        return
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            rows = ws.iter_rows(values_only=True)
            for _, head in zip(range(6), rows):
                roles = [role(h) for h in head]
                if "asjc" in roles and ("title" in roles or "issn" in roles):
                    yield list(head), rows
                    break
    finally:
        wb.close()


def load_source_list(path):
    """three look-ups from the source list to sets of ASJC codes: ISSN, title, ISBN"""
    by_issn, by_title, by_isbn = {}, {}, {}
    n_tables = n_rows = 0
    for head, rows in tables(path):
        roles = [role(h) for h in head]
        cols = {r: [i for i, x in enumerate(roles) if x == r] for r in ("title", "issn", "isbn", "asjc")}
        n_tables += 1
        for row in rows:
            codes = set()
            for i in cols["asjc"]:
                codes.update(asjc_codes(row[i] if i < len(row) else None))
            if not codes:
                continue
            n_rows += 1
            cell = lambda i: row[i] if i < len(row) else None
            for i in cols["issn"]:
                k = issn_key(cell(i))
                if k:
                    by_issn.setdefault(k, set()).update(codes)
            for i in cols["title"]:
                k = title_key(cell(i))
                if k:
                    by_title.setdefault(k, set()).update(codes)
            for i in cols["isbn"]:
                for k in isbn_keys(cell(i)):
                    by_isbn.setdefault(k, set()).update(codes)
    print(f"source list {path.name}: {n_tables} tables with ASJC codes, {n_rows:,} rows; {len(by_issn):,} ISSNs, {len(by_title):,} titles, {len(by_isbn):,} ISBNs")
    return by_issn, by_title, by_isbn


def find(paper, by_issn, by_title, by_isbn):
    """(how it was found, ASJC codes) for one paper"""
    for k in [issn_key(x) for x in re.split(r"[;,]", str(paper.get("ISSN") or ""))]:
        if k in by_issn:
            return "ISSN", by_issn[k]
    k = title_key(paper.get("Source title"))
    if k and k in by_title:
        return "Source title", by_title[k]
    for k in isbn_keys(paper.get("ISBN") or ""):
        if k in by_isbn:
            return "ISBN", by_isbn[k]
    return "not matched", set()


ap = argparse.ArgumentParser(description="Sheet Subject_Areas")
ap.add_argument("--source-list", help="the Scopus Source List (.xlsx or .csv); default: the newest file in data/source_list/ of the project")
args = ap.parse_args()
if args.source_list:
    SOURCE_LIST = Path(args.source_list)
else:
    found = [p for p in (SHEETS / "data" / "source_list").glob("*") if p.suffix.lower() in (".xlsx", ".csv") and not p.name.startswith("~$")]
    SOURCE_LIST = max(found, key=lambda p: p.stat().st_mtime) if found else None
if SOURCE_LIST is None or not SOURCE_LIST.is_file():
    print("SKIPPED: no Scopus Source List was given, so the Subject_Areas sheet was not built and no Subject_Areas.csv was written.")
    print("Download the Source List (an Excel file) from Elsevier's Scopus content page and choose it on this sheet's page, then generate the data again.")
    raise SystemExit(0)

by_issn, by_title, by_isbn = load_source_list(SOURCE_LIST)
if not (by_issn or by_title or by_isbn):
    raise SystemExit(f"{SOURCE_LIST.name} has no table with the columns Source Title / ISSN and an ASJC column: is it the Scopus Source List?")

d = read_csv(CLEAN)
rows = []
for paper in d.to_dict("records"):
    how, codes = find(paper, by_issn, by_title, by_isbn)
    areas = sorted({c[:2] for c in codes if c[:2] in AREAS})
    rows.append({"EID": paper.get("EID"), "Title": paper.get("Title"), "Year": paper.get("Year"), "Source title": paper.get("Source title"),
                 "Document Type": paper.get("Document Type"), "ISSN": paper.get("ISSN"), "ISBN": paper.get("ISBN"), "Matched By": how,
                 "ASJC Codes": "; ".join(sorted(codes)), "Subject Areas": "; ".join(AREAS[a] for a in areas), "_areas": areas})
p = pd.DataFrame(rows)

pairs = p.explode("_areas").dropna(subset=["_areas"])
matched = int((p["Matched By"] != "not matched").sum())
counts = pairs.groupby("_areas").size()
t = pd.DataFrame({"Subject Area": [AREAS[a] for a in counts.index], "ASJC": [f"{a}00" for a in counts.index], "Papers": counts.values})
t["Share of Assignments (%)"] = (t["Papers"] / t["Papers"].sum() * 100).round(2)
t["Share of Matched Papers (%)"] = (t["Papers"] / max(matched, 1) * 100).round(2)
t = t.sort_values(["Papers", "Subject Area"], ascending=[False, True]).reset_index(drop=True)
missing = len(p) - matched
if missing:
    t = pd.concat([t, pd.DataFrame([{"Subject Area": NOT_MATCHED, "ASJC": "", "Papers": missing}])], ignore_index=True)

print(f"{len(p)} papers: {matched} matched ({', '.join(f'{k} {v}' for k, v in p['Matched By'].value_counts().items())}); "
      f"{len(pairs)} (paper, subject area) pairs, {len(counts)} subject areas")
if missing:
    print("not matched by document type: " + ", ".join(f"{k} {v}" for k, v in p.loc[p["Matched By"] == "not matched", "Document Type"].value_counts().items()))
write(t)
write(p.drop(columns="_areas"), OUT_PAPERS)
