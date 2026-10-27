"""Sheet "16_Author_Impact" (query Author_Impact): the leading authors with their local impact indicators (Biblioshiny's "Authors' Local Impact").
Excel: reference of Author_Summary; sort by h_index, then TC, then NP (all largest first; --rank-by h, the default) or by NP, then h_index, then TC
(--rank-by papers); equal rows by author name; keep the first N rows; columns Author, Author ID, h_index, g_index, m_index, TC, NP, PY_start
(the order of the "Top 10 authors" tables of published studies).
Your choices: --top N (how many authors, default 20), --rank-by h|papers (default h).
Input : Author_Summary/Author_Summary.csv        Output: 16_Author_Impact.csv
Run   : python3 16_Author_Impact.py [--top 20] [--rank-by h]
"""
import argparse
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "16_Author_Impact.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


ap = argparse.ArgumentParser(description="Sheet 16_Author_Impact")
ap.add_argument("--top", type=int, default=20, help="how many authors (default 20)")
ap.add_argument("--rank-by", choices=["h", "papers"], default="h", help="h = h-index (default), papers = number of documents (NP)")
args = ap.parse_args()

summary = read_csv(SHEETS / "Author_Summary" / "Author_Summary.csv")
keys = ["h_index", "TC", "NP"] if args.rank_by == "h" else ["NP", "h_index", "TC"]
table = summary.sort_values(keys + ["Author"], ascending=[False, False, False, True], kind="stable").head(max(1, args.top))
print(f"the top {len(table)} authors by {'h-index' if args.rank_by == 'h' else 'number of documents'}")
write(table[["Author", "Author ID", "h_index", "g_index", "m_index", "TC", "NP", "PY_start"]].reset_index(drop=True))
