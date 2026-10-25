"""Sheet "Country_Radar": five indicators of the most productive countries, the data of the radar chart (the October chart "Charts/08_Radar").
Indicators of a country (a paper counts once for each of its countries):
  Documents         = number of papers
  Citations         = total citations of those papers
  Citations_per_doc = Citations / Documents
  h_index           = country-level h-index (the largest h such that h of the country's papers have at least h citations)
  MCP_pct           = share of the country's papers written with 2 or more countries (multi-country papers, MCP), in %
Country_Radar.csv        : the 10 most productive countries (by documents) with the five indicators; "On radar" = 1 for the countries drawn (your choice: --top-countries N, default 5, from 2 to 10)
Country_Radar_scaled.csv : the same indicators scaled 0 to 100 (the largest value among the 10 countries = 100), the numbers the radar draws
Input : Countries/Countries.csv (run Countries.py first)        Run   : python3 Country_Radar.py [--top-countries N]
"""
import argparse
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Country_Radar.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
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



def h_index(cites):
    """largest h such that h papers have at least h citations each"""
    s = sorted(cites, reverse=True)
    return sum(1 for i, v in enumerate(s) if v >= i + 1)


ap = argparse.ArgumentParser()
ap.add_argument("--top-countries", type=int, default=5)
N = min(max(ap.parse_args().top_countries, 2), 10)
c = read_csv(SHEETS / "Countries" / "Countries.csv").dropna(subset=["Country"]).drop_duplicates(["Country", "EID"])
c["Country"] = pivot_labels(c["Country"])
c["Cited by"] = pd.to_numeric(c["Cited by"], errors="coerce").fillna(0)
g = c.groupby("Country")
t = pd.DataFrame({"Documents": g["EID"].nunique(), "Citations": g["Cited by"].sum(), "h_index": g["Cited by"].agg(lambda s: h_index(list(s))),
                  "MCP_pct": g["Collaboration Type"].agg(lambda x: (x == "MCP").mean() * 100)})
t["Citations_per_doc"] = t["Citations"] / t["Documents"]
t = t.sort_values(["Documents", "Citations"], ascending=[False, False], kind="stable").head(10)
t = t[["Documents", "Citations", "Citations_per_doc", "h_index", "MCP_pct"]]
raw = t.round(1).reset_index()
raw["On radar"] = (raw.index < N).astype(int)
scaled = (t / t.max() * 100).round(0).reset_index()
print(raw.to_string(index=False))
write(raw)
write(scaled, HERE / f"Country_Radar_scaled.csv")
