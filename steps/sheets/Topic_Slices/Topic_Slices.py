"""Sheet "Topic_Slices": the same bibliometrics as the other sheets, but cut by SEARCH (Query_IDs), plus a gap audit on titles, abstracts, keywords and reference lists.
The other sheets describe the whole union of searches (dominated by Q05, a broad filter). This one answers topic questions: what do the papers of one search look like,
who is cited by them, and does anything in the corpus combine flood / water mapping with conformal prediction or calibration?
Input : 01_Clean_Data/clean_main_data.csv (needs Query_IDs), References/References.csv, Countries/Countries.csv
Output: Topic_Slices.csv (the overview), Topic_Slices_top_cited.csv, Topic_Slices_top_references.csv, Topic_Slices_keywords.csv, Topic_Slices_term_trend.csv,
        Topic_Slices_gap_audit.csv (every paper that matches an uncertainty term AND a flood/water-mapping term), Topic_Slices_reference_audit.csv, Topic_Slices_report.md
Run   : python3 Topic_Slices.py
The slices are defined in SLICES by search ID (Q07, Q19, ...): they belong to one study; edit them for another.
"""
import re
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def md_table(df):
    """a GitHub table without the tabulate package"""
    cols = list(df.columns)
    return "\n".join(["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(str(v).replace("|", "/") for v in r) + " |" for r in df.itertuples(index=False)])


def write(df, name):
    df.to_csv(HERE / name, index=False, encoding="utf-8-sig")
    print(f"written {name}: {len(df)} rows, {df.shape[1]} columns")


d = read_csv(SHEETS / "01_Clean_Data" / "clean_main_data.csv")
refs = read_csv(SHEETS / "References" / "References.csv")
countries = read_csv(SHEETS / "Countries" / "Countries.csv")[["EID", "Country"]].drop_duplicates()
if "Query_IDs" not in d.columns:
    raise SystemExit("Topic_Slices needs the columns Query_IDs and N_Queries (made by merging several Scopus search exports). This data set does not have them.")
d["qs"] = d["Query_IDs"].fillna("").str.split(";")
d["text"] = (d["Title"].fillna("") + " . " + d["Abstract"].fillna("") + " . " + d["Author Keywords"].fillna("") + " . " + d["Index Keywords"].fillna("")).str.lower()

SLICES = {
    "Q07 RS x water x transformer": lambda r: "Q07" in r.qs,
    "Q19 ViT-family, water or flood": lambda r: "Q19" in r.qs,
    "Q20/Q21 transformer & FM benchmarks": lambda r: bool({"Q20", "Q21"} & set(r.qs)),
    "Q08/Q14/Q15/Q16 uncertainty angles": lambda r: bool({"Q08", "Q14", "Q15", "Q16"} & set(r.qs)),
    "Q22 watershed hydrology + ViT/FM": lambda r: "Q22" in r.qs,
    "Core (matched by 4+ searches)": lambda r: r.N_Queries >= 4,
    "All papers (reference)": lambda r: True,
}
member = {k: d[d.apply(f, axis=1)] for k, f in SLICES.items()}

# ------------------------------------------------------------------ overview
rows, kw_rows = [], []
for name, s in member.items():
    c = countries[countries["EID"].isin(s["EID"])]["Country"].value_counts()
    src = s["Source title"].value_counts()
    rows.append({"Slice": name, "Papers": len(s), "2023": int((s.Year == 2023).sum()), "2024": int((s.Year == 2024).sum()), "2025": int((s.Year == 2025).sum()),
                 "2026": int((s.Year == 2026).sum()), "Median citations": float(s["Cited by"].median()), "Share 2025-26 %": round(100 * s.Year.isin([2025, 2026]).mean(), 1),
                 "Top countries": "; ".join(f"{k} {v}" for k, v in c.head(5).items()), "Top sources": "; ".join(f"{k} {v}" for k, v in src.head(4).items())})
    kws = Counter(k.strip() for v in s["Author Keywords"].dropna() for k in v.split(";") if k.strip())
    for k, n in kws.most_common(15):
        kw_rows.append({"Slice": name, "Keyword": k, "Papers": n})
overview = pd.DataFrame(rows)
write(overview, "Topic_Slices.csv")
top = []
for name, s in member.items():
    for _, r in s.sort_values("Cited by", ascending=False).head(10).iterrows():
        top.append({"Slice": name, "Year": r["Year"], "Cited by": r["Cited by"], "Title": r["Title"], "Source title": r["Source title"], "DOI": r["DOI"]})
write(pd.DataFrame(top), "Topic_Slices_top_cited.csv")
write(pd.DataFrame(kw_rows), "Topic_Slices_keywords.csv")

# ------------------------------------------------------------------ what the slices cite (reference lists)
def ref_key(ref):
    body = ref.split(", ", 1)[1] if ", " in ref else ref
    body = re.sub(r"\(\d{4}\)\s*$", "", body)
    return re.sub(r"[^a-z0-9]", "", body.lower())[:45]


refs["key"] = refs["Reference"].map(ref_key)
label = refs.groupby("key")["Reference"].agg(lambda x: x.value_counts().index[0])
tops = []
for name in ["Q19 ViT-family, water or flood", "Q20/Q21 transformer & FM benchmarks", "Q07 RS x water x transformer", "Core (matched by 4+ searches)"]:
    sub = refs[refs["EID"].isin(member[name]["EID"])].drop_duplicates(["EID", "key"])
    for key, n in sub["key"].value_counts().head(25).items():
        if key:
            tops.append({"Slice": name, "Citing papers": n, "Reference": label[key][:200]})
write(pd.DataFrame(tops), "Topic_Slices_top_references.csv")

# ------------------------------------------------------------------ term trend (share of papers per year, whole corpus)
TERMS = {"transformer": r"transformer", "vision transformer / ViT": r"vision transformer|\bvit\b", "SegFormer / Swin": r"segformer|swin", "foundation model": r"foundation model|geospatial foundation|prithvi|clay\b",
         "SAM / Segment Anything": r"segment anything|\bsam\b", "Sentinel-1 / SAR": r"sentinel-1|\bsar\b|synthetic aperture", "flood": r"flood|inundation", "Sen1Floods11": r"sen1floods11",
         "uncertainty": r"uncertaint", "conformal prediction": r"conformal prediction", "calibration error / calibrated": r"calibration error|well.calibrated|miscalibrat|confidence calibration|model calibration"}
trend = []
for y in range(2018, 2027):
    s = d[d.Year == y]
    trend.append({"Year": y, "Papers": len(s)} | {k: round(100 * s["text"].str.contains(p, regex=True).mean(), 1) if len(s) else 0 for k, p in TERMS.items()})
write(pd.DataFrame(trend), "Topic_Slices_term_trend.csv")

# ------------------------------------------------------------------ gap audit: uncertainty AND flood/water mapping, in the text of the paper
UNC = re.compile(r"conformal prediction|prediction set|prediction interval|coverage guarantee|calibration error|well.calibrated|miscalibrat|confidence calibration|model calibration|"
                 r"uncertainty quantification|epistemic|aleatoric|monte.carlo dropout|mc dropout|deep ensemble|bayesian neural|predictive uncertainty|uncertainty estimation|uncertainty map")
MAP = re.compile(r"flood|inundation|surface water|water bod|water extraction|water mapping|water segmentation|sen1floods11")
SEG = re.compile(r"segmentation|mapping|extraction|detection|delineat")
hit = d[d["text"].map(lambda t: bool(UNC.search(t) and MAP.search(t) and SEG.search(t)))].copy()
hit["Uncertainty terms"] = hit["text"].map(lambda t: "; ".join(sorted(set(UNC.findall(t)))))
hit["Transformer"] = hit["text"].str.contains(r"transformer|segformer|swin|\bvit\b|foundation model|prithvi")
hit["Conformal/calibration (strict)"] = hit["text"].str.contains(r"conformal|calibration error|well.calibrated|miscalibrat|confidence calibration|prediction set")
hit = hit.sort_values(["Conformal/calibration (strict)", "Transformer", "Year"], ascending=False)
write(hit[["Year", "Cited by", "Title", "Source title", "DOI", "Uncertainty terms", "Transformer", "Conformal/calibration (strict)", "Query_IDs"]], "Topic_Slices_gap_audit.csv")

# ------------------------------------------------------------------ reference audit: who cites the conformal / calibration literature
LIT = {"conformal (Vovk, Angelopoulos, Romano, Barber, Tibshirani)": r"conformal|vovk|angelopoulos|algorithmic learning in a random world|tibshirani.*covariate shift",
       "calibration (Guo 2017 'On calibration of modern neural networks', ECE)": r"on calibration of modern neural networks|expected calibration error",
       "deep ensembles / MC dropout (Lakshminarayanan, Gal)": r"simple and scalable predictive uncertainty|dropout as a bayesian approximation",
       "Sen1Floods11 (Bonafilia)": r"sen1floods11",
       "SegFormer (Xie)": r"segformer", "Prithvi / GFM": r"prithvi|pangaea|geospatial foundation"}
low = refs.assign(r=refs["Reference"].str.lower())
audit = []
for name, pat in LIT.items():
    eids = set(low.loc[low["r"].str.contains(pat, regex=True), "EID"])
    sub = d[d["EID"].isin(eids)]
    audit.append({"Cited literature": name, "Citing papers": len(sub), "of which flood/water mapping (text)": sum(1 for t in sub["text"] if MAP.search(t) and SEG.search(t)),
                  "of which 2025-26": int(sub.Year.isin([2025, 2026]).sum())})
write(pd.DataFrame(audit), "Topic_Slices_reference_audit.csv")
both = set(low.loc[low["r"].str.contains(LIT[list(LIT)[0]], regex=True), "EID"])
ci = d[d["EID"].isin(both) & d["text"].map(lambda t: bool(MAP.search(t) and SEG.search(t)))][["Year", "Cited by", "Title", "Source title", "DOI"]].sort_values("Year", ascending=False)
write(ci, "Topic_Slices_cites_conformal_and_maps_water.csv")

# ------------------------------------------------------------------ short report
md = ["# Topic_Slices report (generated by Topic_Slices.py)", "", "## Slices", md_table(overview), "", "## Share of papers per year that mention a term (whole corpus, %)",
      md_table(pd.DataFrame(trend)), "", "## Gap audit: uncertainty term AND flood/water mapping term",
      f"{len(hit)} papers match; {int(hit['Conformal/calibration (strict)'].sum())} also match a strict conformal/calibration term; {int((hit['Transformer'] & hit['Conformal/calibration (strict)']).sum())} of those use a transformer.", "",
      md_table(hit[hit["Conformal/calibration (strict)"]][["Year", "Cited by", "Title", "Uncertainty terms"]]) if hit["Conformal/calibration (strict)"].any() else "(none)", "",
      "## Who cites the conformal / calibration literature", md_table(pd.DataFrame(audit)), ""]
(HERE / "Topic_Slices_report.md").write_text("\n".join(md), encoding="utf-8")
print("written Topic_Slices_report.md")

# the papers that cite the conformal literature, whatever their topic (the reading candidates)
conf = set(low.loc[low["r"].str.contains(LIT[list(LIT)[0]], regex=True), "EID"])
write(d[d["EID"].isin(conf)][["Year", "Cited by", "Title", "Source title", "DOI", "Query_IDs"]].sort_values("Year", ascending=False), "Topic_Slices_cites_conformal_any_topic.csv")
