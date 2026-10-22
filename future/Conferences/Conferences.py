"""Sheet "Conferences": conferences held at least n times (n = your choice) and how many papers each had, as a table and two plots.
A paper belongs to a conference when its export has a Conference name and a Conference date.
Which papers belong to the same conference (the "series"): the Conference name is cleaned so that the editions of one conference get the same name: ordinal numbers (23rd), years (2016, '16),
Roman numerals (XVIII), "Vol. 3" and a subtitle after ":" are removed; letters are compared in lower case, punctuation is ignored.
  example: "36th IEEE International Geoscience and Remote Sensing Symposium, IGARSS 2016" and "40th IEEE ... Symposium, IGARSS 2020" are one series.
Edition = one conference year (the year at the start of the Conference date); Editions = number of different conference years of the series in the data.
Conferences.csv          : every series with Editions, Papers, Citations, first and last conference year, the source titles it was published in; "In plots" = 1 when Editions >= n
Conferences_timeline.csv : for the series with Editions >= n: one row per series and conference year with papers, citations (TC) and TC per year = TC / (reference year - year + 1), reference year = last year of the data + 1
Your choices: --min-editions N (default 3); --by-source: group by the Source title (e.g. "Proceedings of SPIE") instead of the cleaned conference name (default: by conference name).
Input : 01_Clean_Data/clean_main_data.csv        Run   : python3 Conferences.py [--min-editions N] [--by-source]
"""
import argparse
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Conferences.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")




ROMAN = re.compile(r"\b(?=[ivxlc]+\b)m{0,3}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})\b", re.IGNORECASE)


def series_name(raw):
    """the name of a conference without ordinal, year, volume number and subtitle: (key for comparing, name to show)"""
    s = raw.split(":")[0]
    s = re.sub(r"\b\d+(st|nd|rd|th)\b", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"['‘’]?\b(19|20)\d{2}\b|['’]\d{2}\b", " ", s)
    s = ROMAN.sub(" ", s)
    s = re.sub(r"\b(vol(ume)?|part|no)\.?\s*\d+\b", " ", s, flags=re.IGNORECASE)
    shown = re.sub(r"\s+", " ", re.sub(r"\s+([,;)])", r"\1", s)).strip(" ,;-")
    key = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", shown.lower())).strip()
    return key, shown


ap = argparse.ArgumentParser()
ap.add_argument("--min-editions", type=int, default=3)
ap.add_argument("--by-source", action="store_true")
opt = ap.parse_args()
n_min = max(opt.min_editions, 1)
c = read_csv(CLEAN, usecols=["EID", "Year", "Cited by", "Source title", "Conference name", "Conference date"]).dropna(subset=["Conference name", "Conference date"]).copy()
c["Conf year"] = pd.to_numeric(c["Conference date"].str[:4], errors="coerce")
c = c.dropna(subset=["Conf year"]).copy()
c["Conf year"] = c["Conf year"].astype(int)
c["Cited by"] = pd.to_numeric(c["Cited by"], errors="coerce").fillna(0)
if opt.by_source:
    c = c.dropna(subset=["Source title"]).copy()
    c["key"] = c["Source title"].str.lower().str.strip()
    c["shown"] = c["Source title"]
else:
    pairs = c["Conference name"].map(series_name)
    c["key"] = [p[0] for p in pairs]
    c["shown"] = [p[1] for p in pairs]
print(f"{len(c)} conference papers; grouped by {'source title' if opt.by_source else 'cleaned conference name'}")
shown = c.groupby("key")["shown"].agg(lambda s: s.value_counts().index[0])                   # the most frequent spelling of a series
g = c.groupby("key")
table = pd.DataFrame({"Editions": g["Conf year"].nunique(), "Papers": g["EID"].nunique(), "Citations": g["Cited by"].sum().astype(int),
                      "First year": g["Conf year"].min(), "Last year": g["Conf year"].max(),
                      "Published in": g["Source title"].agg(lambda s: "; ".join(sorted(set(s.dropna()))))})
table.insert(0, "Conference", shown)
table = table.sort_values(["Editions", "Papers", "Conference"], ascending=[False, False, True], kind="stable").reset_index()
table["In plots"] = (table["Editions"] >= n_min).astype(int)
print(f"{int(table['In plots'].sum())} of {len(table)} conferences have at least {n_min} editions")
write(table.drop(columns="key"))
chosen = table[table["In plots"] == 1]["key"].tolist()
ref_year = int(pd.to_numeric(read_csv(CLEAN, usecols=["Year"])["Year"]).max()) + 1
t = c[c["key"].isin(chosen)].drop_duplicates(["key", "EID"])
tl = t.groupby(["key", "Conf year"]).agg(Papers=("EID", "count"), TC=("Cited by", "sum")).reset_index()
tl["TC"] = tl["TC"].astype(int)
tl["TC per year"] = (tl["TC"] / (ref_year - tl["Conf year"] + 1).clip(lower=1)).round(3)
tl["order"] = tl["key"].map({k: i for i, k in enumerate(chosen)})
tl["Conference"] = tl["key"].map(shown)
tl = tl.sort_values(["order", "Conf year"]).rename(columns={"Conf year": "Year"})[["Conference", "Year", "Papers", "TC", "TC per year"]]
write(tl, HERE / "Conferences_timeline.csv")
