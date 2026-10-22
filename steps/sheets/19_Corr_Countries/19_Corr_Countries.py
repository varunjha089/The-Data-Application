"""Sheet "19_Corr_Countries": the countries of the corresponding authors, with single-country (SCP) and multi-country (MCP) papers (Biblioshiny "Corresponding Author's Country").
Excel: PivotTable on Clean_Main_Data, rows = Corresponding Country (Top 10 filter on the number of papers, ties kept), columns = Collaboration Type, values = count of EID;
Grand Total column; MCP ratio = MCP / Grand Total. Papers without a corresponding country are left out; the Grand Total row is not written.
Input : 01_Clean_Data/clean_main_data.csv        Output: 19_Corr_Countries.csv
Run   : python3 19_Corr_Countries.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "19_Corr_Countries.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


import unicodedata


def pivot_labels(s):
    """a PivotTable ignores upper/lower case: 'Water' and 'WATER' are one item, labelled with the spelling met first"""
    return s.groupby(s.str.lower()).transform("first")


def sort_key(s):
    """sort like Excel: ignore accents and case ('Université' sorts as 'universite')"""
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch)).casefold()


def top_with_ties(df, col, n):
    """Excel's 'Top 10' filter keeps every item that ties with the n-th one"""
    cut = df[col].nlargest(n).min()
    return df[df[col] >= cut]


clean = read_csv(CLEAN)
d = clean.dropna(subset=["Corresponding Country"]).copy()
print(f"papers without a corresponding country (left out): {len(clean) - len(d)}")
d["Corresponding Country"] = pivot_labels(d["Corresponding Country"])
p = d.pivot_table(index="Corresponding Country", columns="Collaboration Type", values="EID", aggfunc="count", fill_value=0)
for c in ("MCP", "SCP"):
    if c not in p:
        p[c] = 0
p["Grand Total"] = d.groupby("Corresponding Country").size()
p = p.reset_index().sort_values(["Grand Total", "SCP"], ascending=[False, False], kind="stable")
p = top_with_ties(p, "Grand Total", 10)
p["MCP ratio"] = p["MCP"] / p["Grand Total"]
write(p[["Corresponding Country", "MCP", "SCP", "Grand Total", "MCP ratio"]].reset_index(drop=True))
