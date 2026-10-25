"""Sheet "Author_Summary" (query Author_Summary): one row per Scopus Author ID with his or her production and impact.
Excel: reference of Authors; group by EID to get the number of authors n of each paper and give every author of it the fraction 1/n; group by Author ID:
NP = number of papers, NP_Frac = sum of the fractions (fractional counting), TC = total citations, PY_start = first year, Author = the name used most often
(of equally frequent names the last one), h_index, g_index, m_index = h / max(2026 - PY_start + 1, 1) (floored at 1: early-access items dated after 2026 would otherwise divide by zero); sorted by NP then NP_Frac, both descending.
Input : Authors/Authors.csv (run Authors.py first)        Output: Author_Summary.csv
Note  : entries without an Author ID form one group with an empty ID, as in Power Query.
Run   : python3 Author_Summary.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Author_Summary.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


def h_index(cites):
    """largest h such that h papers have at least h citations each"""
    s = sorted(cites, reverse=True)
    return sum(1 for i, v in enumerate(s) if v >= i + 1)


def g_index(cites):
    """largest g such that the g most cited papers together have at least g squared citations"""
    s = sorted(cites, reverse=True)
    total, best = 0, 0
    for i, v in enumerate(s, 1):
        total += v
        if total >= i * i:
            best = i
    return best


from collections import Counter

au = read_csv(SHEETS / "Authors" / "Authors.csv")
au["Frac"] = 1.0 / au.groupby("EID")["EID"].transform("size")
rows = []
for ident, g in au.groupby("Author ID", sort=False, dropna=False):
    cites = g["Cited by"].tolist()
    names = g["Author Name"].tolist()
    count = Counter(names)
    top = max(count.values())
    author = [n for n in names if count[n] == top][-1]
    h, py = h_index(cites), int(g["Year"].min())
    rows.append((ident, len(g), g["Frac"].sum(), int(sum(cites)), py, author, h, g_index(cites), round(h / max(2026 - py + 1, 1), 2)))
summary = pd.DataFrame(rows, columns=["Author ID", "NP", "NP_Frac", "TC", "PY_start", "Author", "h_index", "g_index", "m_index"])
summary = summary.sort_values(["NP", "NP_Frac"], ascending=False, kind="stable").reset_index(drop=True)
print(f"{len(summary)} authors; most papers: {summary.iloc[0]['Author']} ({summary.iloc[0]['NP']})")
write(summary)
