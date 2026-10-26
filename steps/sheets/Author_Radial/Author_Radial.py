"""Sheet "Author_Radial": the leading authors ranked by fractional score (or by publications), with the country they publish from (the data of the radial chart).
Fractional score = the sum over an author's papers of 1 / (number of authors of the paper) (fractional counting, column NP_Frac of Author_Summary): a paper
counts 1 in total, shared by its authors, so a single-author paper weighs more than one written by twenty.
Country of an author: in "Authors with affiliations" every author of a paper is listed once as "Surname, Given names, affiliation ..., Country"; Scopus lists the
authors in the same order as in "Author full names" ("Surname, Given names (ID)"), so an entry is matched to its Author ID by position (by name when the two
lists differ in length; older exports write "Surname I." there), and the country is read from the address (common/names.py). An author
takes the country named on most of his or her papers (equal counts: the one of the most recent paper); without any, "Unknown".
Excel: Author_Summary sorted by NP_Frac (or NP) descending, top N, plus a column Country from a PivotTable of (Author ID, Country) counts.
Your choices: --top N (how many authors, default 50), --rank-by frac|papers (default frac: fractional score; ties by publications, then citations).
Input : Author_Summary/Author_Summary.csv (run Author_Summary.py first), 01_Clean_Data/clean_main_data.csv
Output: Author_Radial.csv (Rank, Author, Author ID, Country, Publications, Fractional score, Citations)
Run   : python3 Author_Radial.py [--top 50] [--rank-by frac]
"""
import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Author_Radial.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}
sys.path.insert(0, str(SHEETS / "common"))                    # shared name rules, copied into the project by the application
from names import country_of_affiliation  # noqa: E402


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


def author_countries(d):
    """Author ID -> the country named on most of the author's papers"""
    seen = defaultdict(Counter)
    last = {}
    rows = d[["Author full names", "Authors with affiliations", "Year"]].itertuples(index=False, name=None) \
        if {"Author full names", "Authors with affiliations"} <= set(d.columns) else []
    for full, affil, year in rows:
        if not isinstance(full, str) or not isinstance(affil, str):
            continue
        ids, order = {}, []
        for part in full.split("; "):                         # "Crétaux, Jean François (6603121976)"
            m = re.match(r"^(.*?)\s*\((\d+)\)\s*$", part.strip())
            if m:
                ids[m.group(1).strip().lower()] = m.group(2)
                order.append(m.group(2))
        entries = affil.split("; ")                            # "Crétaux, Jean François, Laboratoire ..., France" (or the older "Crétaux J.-F., Laboratoire ...")
        for k, entry in enumerate(entries):
            bits = [b.strip() for b in entry.split(",")]
            aid = order[k] if len(entries) == len(order) else (ids.get(", ".join(bits[:2]).lower()) or ids.get(bits[0].lower()))
            country = country_of_affiliation(", ".join(bits[1:]))
            if aid and country:
                seen[aid][country] += 1
                if year >= last.get((aid, country), 0):
                    last[(aid, country)] = year
    return {aid: max(c, key=lambda k: (c[k], last[(aid, k)])) for aid, c in seen.items()}


ap = argparse.ArgumentParser(description="Sheet Author_Radial")
ap.add_argument("--top", type=int, default=50, help="how many authors (default 50)")
ap.add_argument("--rank-by", choices=["frac", "papers"], default="frac", help="frac = fractional score (default), papers = publications")
args = ap.parse_args()

summary = read_csv(SHEETS / "Author_Summary" / "Author_Summary.csv")
summary = summary[summary["Author ID"].fillna("").str.strip() != ""]
d = read_csv(CLEAN)
d["Year"] = pd.to_numeric(d.get("Year"), errors="coerce").fillna(0).astype(int)
countries = author_countries(d)
keys = ["NP_Frac", "NP", "TC"] if args.rank_by == "frac" else ["NP", "NP_Frac", "TC"]
t = summary.sort_values(keys + ["Author"], ascending=[False, False, False, True], kind="stable").head(max(1, args.top)).reset_index(drop=True)
t["Country"] = t["Author ID"].map(countries).fillna("Unknown")
t.insert(0, "Rank", range(1, len(t) + 1))
t = t.rename(columns={"NP": "Publications", "NP_Frac": "Fractional score", "TC": "Citations"})
t = t[["Rank", "Author", "Author ID", "Country", "Publications", "Fractional score", "Citations"]]
known = sum(1 for a in summary["Author ID"] if a in countries)
print(f"{len(summary):,} authors; a country was found for {known:,} ({100 * known / max(len(summary), 1):.1f}%). The top {len(t)} by "
      f"{'fractional score' if args.rank_by == 'frac' else 'publications'}:")
print(t.head(15).to_string(index=False))
print("countries of the top authors: " + ", ".join(f"{c} {n}" for c, n in t["Country"].value_counts().items()))
write(t)
