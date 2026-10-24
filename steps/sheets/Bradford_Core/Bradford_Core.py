"""Sheet "Bradford_Core": who publishes in the Bradford core sources - countries, authors and institutions.
The core is Zone 1 of Bradford's law as the Bradford plot draws it: the most productive sources, added up until they hold a third of the documents (the source that crosses
the line completes the zone). For every country, author and institution:
  Papers, Core_Papers = papers (each counted once) in all sources / in the core sources;   Core_Share_pct = Core_Papers / Papers * 100
  Citations, CPP_all = total citations and citations per paper;   CPP_core / CPP_outside = citations per paper of its core papers / of its other papers
Papers without a Source title cannot be placed in a zone and are left out. A paper counts once for each of its countries, authors or institutions.
Core_Papers measures where an actor publishes (the venues that carry most of the field), not how good the work is: the core can hold proceedings and mega-journals.
CPP_core against CPP_outside is the quality side; citations are not corrected for age, so compare the two numbers of one actor, not actors with different years of activity.
Input : 09_Bradford/09_Bradford.csv, Authors/Authors.csv, Affiliations/Affiliations.csv, Countries/Countries.csv
Output: Bradford_Core.csv (the 200 actors of each kind with most core papers), Bradford_Core_baseline.csv (the whole corpus, core against the rest),
        Bradford_Core_matrix.csv (papers of the plotted actors in each core source)
Run   : python3 Bradford_Core.py [--top N]     (N = actors per kind in the matrix and the plots, default 15)
"""
import argparse
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
OUT = HERE / "Bradford_Core.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}
KEEP = 200


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


def pivot_labels(s):
    """a PivotTable ignores upper/lower case: 'Water' and 'WATER' are one item, labelled with the spelling met first"""
    return s.groupby(s.str.lower()).transform("first")


ap = argparse.ArgumentParser()
ap.add_argument("--top", type=int, default=15)
TOP = min(max(ap.parse_args().top, 3), 40)

# the core, as the Bradford plot draws it
b = read_csv(SHEETS / "09_Bradford" / "09_Bradford.csv")[["Source", "Documents"]]
core, cum = [], 0
for s, n in zip(b["Source"], b["Documents"]):
    core.append(s)
    cum += n
    if cum >= b["Documents"].sum() / 3:
        break
core_key = {s.lower(): i + 1 for i, s in enumerate(core)}
print(f"core: {len(core)} sources holding {cum} of {b['Documents'].sum()} documents")


def prepare(df, entity, label=None):
    """one row per (actor, paper) with its source, citations and whether the source is in the core"""
    d = df.dropna(subset=[entity, "Source title"]).copy()
    d["Cited by"] = pd.to_numeric(d["Cited by"], errors="coerce").fillna(0)
    d["Entity"] = d[entity]
    d["Label"] = d.groupby("Entity")[label].transform("first") if label else d["Entity"]
    d = d.drop_duplicates(["Entity", "EID"])
    d["Core_rank"] = d["Source title"].str.lower().map(core_key)
    d["In_core"] = d["Core_rank"].notna()
    return d[["Entity", "Label", "Source title", "Cited by", "EID", "Core_rank", "In_core"]]


authors = prepare(read_csv(SHEETS / "Authors" / "Authors.csv"), "Author ID", "Author Name")
c = read_csv(SHEETS / "Countries" / "Countries.csv")
c["Country"] = pivot_labels(c["Country"].where(c["Country"].notna(), None).fillna("")).replace("", pd.NA)
countries = prepare(c, "Country")
a = read_csv(SHEETS / "Affiliations" / "Affiliations.csv")
a["Institution"] = pivot_labels(a["Institution"].fillna("")).replace("", pd.NA)
institutions = prepare(a, "Institution")
KINDS = {"Countries": countries, "Authors": authors, "Institutions": institutions}


def summary(d):
    g = d.groupby("Entity")
    t = g.agg(Label=("Label", "first"), Papers=("EID", "size"), Core_Papers=("In_core", "sum"), Citations=("Cited by", "sum")).reset_index(drop=True)
    cc = d[d["In_core"]].groupby("Entity")["Cited by"].mean()
    co = d[~d["In_core"]].groupby("Entity")["Cited by"].mean()
    ent = g["Label"].first().reset_index()
    t["Entity"] = ent["Entity"].to_numpy()
    t["Core_Share_pct"] = (100 * t["Core_Papers"] / t["Papers"]).round(1)
    t["CPP_all"] = (t["Citations"] / t["Papers"]).round(2)
    t["CPP_core"] = t["Entity"].map(cc).round(2)
    t["CPP_outside"] = t["Entity"].map(co).round(2)
    t = t.sort_values(["Core_Papers", "Papers", "Label"], ascending=[False, False, True], kind="stable").reset_index(drop=True)
    t["Rank"] = range(1, len(t) + 1)
    return t[["Rank", "Label", "Papers", "Core_Papers", "Core_Share_pct", "Citations", "CPP_all", "CPP_core", "CPP_outside", "Entity"]].rename(columns={"Label": "Name"})


tables, matrix, base = [], [], []
papers = countries.drop_duplicates("EID")
for kind, d in KINDS.items():
    t = summary(d)
    print(f"{kind}: {len(t)} actors, {int((t['Core_Papers'] > 0).sum())} with a core paper")
    top = t.head(TOP)
    tables.append(t.head(KEEP).assign(Kind=kind))
    m = d[d["Entity"].isin(top["Entity"]) & d["In_core"]].groupby(["Entity", "Core_rank", "Source title"]).size().rename("Papers").reset_index()
    m["Name"] = m["Entity"].map(dict(zip(top["Entity"], top["Name"])))
    m["Kind"] = kind
    matrix.append(m)
    inside, outside = d[d["In_core"]], d[~d["In_core"]]
    base.append({"Kind": kind, "Actor-paper pairs": len(d), "In core": len(inside), "Core share %": round(100 * len(inside) / len(d), 1),
                 "CPP core": round(inside["Cited by"].mean(), 2), "CPP outside": round(outside["Cited by"].mean(), 2)})
allp = pd.concat(KINDS.values()).drop_duplicates("EID")
base.append({"Kind": "All papers", "Actor-paper pairs": len(allp), "In core": int(allp["In_core"].sum()), "Core share %": round(100 * allp["In_core"].mean(), 1),
             "CPP core": round(allp[allp["In_core"]]["Cited by"].mean(), 2), "CPP outside": round(allp[~allp["In_core"]]["Cited by"].mean(), 2)})
out = pd.concat(tables)[["Kind", "Rank", "Name", "Papers", "Core_Papers", "Core_Share_pct", "Citations", "CPP_all", "CPP_core", "CPP_outside", "Entity"]]
write(out)
write(pd.DataFrame(base), HERE / "Bradford_Core_baseline.csv")
write(pd.concat(matrix)[["Kind", "Name", "Core_rank", "Source title", "Papers", "Entity"]].rename(columns={"Core_rank": "Core source no.", "Source title": "Source"}), HERE / "Bradford_Core_matrix.csv")
print(pd.DataFrame(base).to_string(index=False))
