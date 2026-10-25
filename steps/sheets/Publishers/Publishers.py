"""Sheet "Publishers": the publishers of the sources, and how each publisher's documents are spread over its sources (the data of the treemaps).
Excel: add a column "Publisher group" to Clean_Main_Data (the publisher names cleaned, see below), then PivotTables: rows = Publisher group, values = count of EID
and sum of Cited by; and rows = Publisher group, Source title, values = count of EID.
The export writes one publisher in many ways ("MDPI", "MDPI AG" with an address and an e-mail, "Multidisciplinary Digital Publishing Institute (MDPI)"),
so the names are cleaned before counting: e-mail addresses are removed, the big publishers are recognised by a word of their name (Elsevier with Academic Press,
Pergamon and Cell Press; Springer Nature with Nature Research and BioMed Central; Wiley with Blackwell; Taylor & Francis with Routledge and CRC Press; IEEE; ...),
and for the others the company form at the end (Inc., Ltd, B.V., GmbH, AG, S.A., ...) is dropped. A source belongs to the publisher named most often on its papers.
Papers without a Source title (mostly books) are counted as the source "(no source title)" of their publisher; papers without a publisher as "Unknown publisher".
Input : 01_Clean_Data/clean_main_data.csv
Output: Publishers.csv (Rank, Publisher, Sources, Documents, Share of Documents (%), Citations, Citations per Document, Names in the export)
        Publishers_sources.csv (Publisher, Source title, Abbreviation, Documents, Share of Publisher (%), Citations)
Run   : python3 Publishers.py
"""
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Publishers.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}
UNKNOWN, NO_SOURCE = "Unknown publisher", "(no source title)"
FAMILIES = [                                                 # publisher group <- words that name it (lower case, part of the name)
    ("MDPI", ["mdpi", "multidisciplinary digital publishing"]),
    ("Elsevier", ["elsevier", "academic press", "pergamon", "cell press", "north-holland", "saunders", "mosby"]),
    ("Springer Nature", ["springer", "nature research", "nature publishing", "nature portfolio", "biomed central", "palgrave", "birkh"]),
    ("Wiley", ["wiley", "blackwell"]),
    ("Taylor & Francis", ["taylor and francis", "taylor & francis", "routledge", "crc press", "informa"]),
    ("IEEE", ["institute of electrical and electronics engineers", "ieee"]),
    ("SPIE", ["spie"]),
    ("Copernicus", ["copernicus"]),
    ("Frontiers", ["frontiers media"]),
    ("IOP Publishing", ["institute of physics", "iop publishing"]),
    ("SAGE", ["sage publications", "sage ltd"]),
    ("Oxford University Press", ["oxford university press"]),
    ("Cambridge University Press", ["cambridge university press"]),
    ("American Chemical Society", ["american chemical society"]),
    ("IWA Publishing", ["iwa publishing"]),
    ("Science Press", ["science press"]),
    ("Hindawi", ["hindawi"]),
    ("De Gruyter", ["de gruyter"]),
    ("Emerald", ["emerald"]),
    ("Inderscience", ["inderscience"]),
    ("IGI Global", ["igi global"]),
    ("World Scientific", ["world scientific"])]
FORMS = r"(,|\s)+(inc|ltd|llc|limited|b\.?v|gmbh|ag|sa|s\.\s?a|s\.r\.l|co|corp|plc)\.?$"           # company forms dropped at the end of a name


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


def plain(name):
    """the publisher name without e-mail addresses and extra spaces"""
    return re.sub(r"\s+", " ", re.sub(r"\S+@\S+", " ", str(name))).strip(" ,;")


def group(name):
    """the publisher group of a name as written in the export"""
    if not isinstance(name, str) or not plain(name):
        return UNKNOWN
    low = plain(name).lower()
    for g, words in FAMILIES:
        if any(w in low for w in words):
            return g
    short = plain(name)
    while (new := re.sub(FORMS, "", short, flags=re.I).strip(" ,;")) and new != short:     # "Foo Publishing Ltd." -> "Foo"
        short = new
    return short or plain(name)


d = read_csv(CLEAN)
if "Publisher" not in d.columns:
    print("SKIPPED: the export has no Publisher column, so the publishers cannot be counted and nothing was written.")
    print("Export again from Scopus with the column Publisher (in the group Bibliographical information).")
    raise SystemExit(0)

d["Group"] = d["Publisher"].map(group)
d["Source"] = d["Source title"].fillna(NO_SOURCE) if "Source title" in d.columns else NO_SOURCE
d["Cites"] = pd.to_numeric(d.get("Cited by", 0), errors="coerce").fillna(0).astype(int)
known = d[d["Group"] != UNKNOWN]
owner = known.groupby(["Source", "Group"]).size().reset_index(name="n").sort_values(["Source", "n", "Group"], ascending=[True, False, True])
owner = owner.drop_duplicates("Source").set_index("Source")["Group"]       # a source belongs to the publisher named most often on its papers
d["Publisher group"] = [owner.get(s, g) if s != NO_SOURCE else g for s, g in zip(d["Source"], d["Group"])]
abbr = d.dropna(subset=["Abbreviated Source Title"]).groupby("Source")["Abbreviated Source Title"].agg(lambda s: s.mode().iloc[0]) \
    if "Abbreviated Source Title" in d.columns else pd.Series(dtype=str)

src = d.groupby(["Publisher group", "Source"]).agg(Documents=("EID", "size"), Citations=("Cites", "sum")).reset_index()
src["Abbreviation"] = src["Source"].map(abbr)
pub = d.groupby("Publisher group").agg(Sources=("Source", "nunique"), Documents=("EID", "size"), Citations=("Cites", "sum")).reset_index()
pub["Names in the export"] = pub["Publisher group"].map(d.groupby("Publisher group")["Publisher"].agg(
    lambda s: "; ".join(sorted({plain(x) for x in s.dropna()} - {""}))))
pub = pub.sort_values(["Documents", "Publisher group"], ascending=[False, True]).reset_index(drop=True)
pub = pub[pub["Publisher group"] != UNKNOWN].pipe(lambda p: pd.concat([p, pub[pub["Publisher group"] == UNKNOWN]])).reset_index(drop=True)
pub.insert(0, "Rank", range(1, len(pub) + 1))
pub.insert(4, "Share of Documents (%)", pub["Documents"] / len(d) * 100)
pub["Citations per Document"] = pub["Citations"] / pub["Documents"]
pub = pub.rename(columns={"Publisher group": "Publisher"})[["Rank", "Publisher", "Sources", "Documents", "Share of Documents (%)", "Citations",
                                                            "Citations per Document", "Names in the export"]]
src = src.merge(pub[["Publisher", "Rank", "Documents"]].rename(columns={"Publisher": "Publisher group", "Documents": "All"}), on="Publisher group")
src["Share of Publisher (%)"] = src["Documents"] / src["All"] * 100
src = src.sort_values(["Rank", "Documents", "Source"], ascending=[True, False, True])
src = src.rename(columns={"Publisher group": "Publisher", "Source": "Source title"})[["Publisher", "Source title", "Abbreviation", "Documents", "Share of Publisher (%)", "Citations"]]

print(f"{len(d):,} documents from {len(pub) - (pub['Publisher'] == UNKNOWN).sum()} publishers ({d['Publisher'].nunique()} names in the export); "
      f"{(d['Group'] == UNKNOWN).sum()} documents without a publisher. The largest:")
print(pub.head(10).drop(columns="Names in the export").round(2).to_string(index=False))
write(pub)
write(src, HERE / "Publishers_sources.csv")
