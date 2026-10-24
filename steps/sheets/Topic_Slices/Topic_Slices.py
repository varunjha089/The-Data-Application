"""Sheet "Topic_Slices": the same bibliometrics as the other sheets, but cut by SEARCH (Query_IDs), plus an optional gap audit on titles, abstracts, keywords and reference lists.
The other sheets describe the whole union of searches (often dominated by one broad search). This one answers topic questions: what do the papers of one search look like,
who do they cite, how do terms rise and fall, and (if you define it) does anything in the corpus combine two topics you care about?
Input : 01_Clean_Data/clean_main_data.csv (needs Query_IDs and N_Queries, made by merging several Scopus search exports), References/References.csv, Countries/Countries.csv
        and, in the PROJECT folder (next to 01_Clean_Data), topic_slices.json: what to cut and what to look for. If it is missing, the first run writes one for you to edit.
Output: Topic_Slices.csv (the overview), Topic_Slices_top_cited.csv, Topic_Slices_top_references.csv, Topic_Slices_keywords.csv, Topic_Slices_term_trend.csv, Topic_Slices_report.md,
        and, when topic_slices.json defines an "audit": Topic_Slices_gap_audit.csv; when it defines "literature": Topic_Slices_reference_audit.csv and the two "cites" lists
Run   : python3 Topic_Slices.py
topic_slices.json (every key optional; patterns are regular expressions, matched in lower case on title + abstract + keywords, or on reference text):
  slices            [{"name": ..., "searches": ["Q02", ...], "min_searches": 4}]  a slice = papers found by any listed search, or by at least min_searches searches
  overview_years    years that get their own column in the overview;  recent_years: years whose share is reported;  trend_years: [first, last] of the term trend
  reference_slices  names of the slices whose reference lists are summed up
  term_trend        {"label": "pattern"}  share of the papers per year that mention the term
  audit             {"title", "terms_column", "topic_column" (names of two output columns), "all_of": [patterns that must ALL match], "terms_from": index of the pattern whose matches are listed, "topic": [indexes of the patterns that
                     define the topic in the literature table], "flags": {"column": "pattern"}}   (the gap audit)
  literature        {"label": "pattern"}  papers whose reference lists match, with how many of them are about the audit topic
  cites_files       {"topic": file name, "any": file name}  names of the two lists of papers that cite the FIRST literature entry (about the audit topic / on any topic)
Without the file the slices are the biggest searches, the term trend uses the most frequent keywords, and there is no audit.
"""
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the project folder: holds 01_Clean_Data, one folder per sheet and topic_slices.json
CONFIG = SHEETS / "topic_slices.json"
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


def remove(name):
    """an output that this configuration does not make is deleted, so an older result is never mistaken for a current one"""
    if (HERE / name).exists():
        (HERE / name).unlink()
        print(f"removed {name} (not made with this configuration)")


d = read_csv(SHEETS / "01_Clean_Data" / "clean_main_data.csv")
refs = read_csv(SHEETS / "References" / "References.csv")
countries = read_csv(SHEETS / "Countries" / "Countries.csv")[["EID", "Country"]].drop_duplicates()
if "Query_IDs" not in d.columns:
    raise SystemExit("Topic_Slices needs the columns Query_IDs and N_Queries (made by merging several Scopus search exports). This data set does not have them.")
d["qs"] = d["Query_IDs"].fillna("").str.split(";")
d["text"] = (d["Title"].fillna("") + " . " + d["Abstract"].fillna("") + " . " + d["Author Keywords"].fillna("") + " . " + d["Index Keywords"].fillna("")).str.lower()

# ------------------------------------------------------------------ the configuration (written for you on the first run)
this_year = date.today().year
last = min(int(d["Year"].max()), this_year)
if CONFIG.exists():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    print(f"configuration: {CONFIG.name}")
else:
    searches = Counter(q for qs in d["qs"] for q in qs if q)
    kws = Counter(k.strip() for v in d["Author Keywords"].dropna() for k in v.split(";") if k.strip())
    cfg = {"_help": "Edit and run the sheet again. slices: papers found by any of the listed searches (or by at least min_searches searches). term_trend: label -> regular expression. "
                    "Add an \"audit\" and a \"literature\" to look for papers that combine topics; see the top of Topic_Slices.py for the format.",
           "slices": [{"name": f"Search {q} ({n} papers)", "searches": [q]} for q, n in searches.most_common(6)] + ([{"name": "Core (found by 4+ searches)", "min_searches": 4}] if d["N_Queries"].max() >= 4 else []),
           "term_trend": {k: re.escape(k.lower()) for k, _ in kws.most_common(10)}}
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"no {CONFIG.name} yet: wrote one with automatic choices in the project folder; edit it to cut the data your way")
YEARS = cfg.get("overview_years") or list(range(max(last - 3, int(d["Year"].min())), last + 1))
RECENT = cfg.get("recent_years") or YEARS[-2:]
t0, t1 = (cfg.get("trend_years") or [last - 8, last])


def selector(spec):
    qs, n = set(spec.get("searches") or []), spec.get("min_searches")
    return lambda r: bool(qs & set(r.qs)) or (n is not None and r.N_Queries >= n)


member = {s["name"]: d[d.apply(selector(s), axis=1)] for s in cfg.get("slices", [])}
member["All papers (reference)"] = d

# ------------------------------------------------------------------ overview
rows, kw_rows = [], []
for name, s in member.items():
    c = countries[countries["EID"].isin(s["EID"])]["Country"].value_counts()
    src = s["Source title"].value_counts()
    rows.append({"Slice": name, "Papers": len(s), **{str(y): int((s.Year == y).sum()) for y in YEARS}, "Median citations": float(s["Cited by"].median()) if len(s) else 0,
                 f"Share {RECENT[0]}-{str(RECENT[-1])[-2:]} %": round(100 * s.Year.isin(RECENT).mean(), 1) if len(s) else 0,
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
for name in [n for n in (cfg.get("reference_slices") or list(member)[:4]) if n in member]:
    sub = refs[refs["EID"].isin(member[name]["EID"])].drop_duplicates(["EID", "key"])
    for key, n in sub["key"].value_counts().head(25).items():
        if key:
            tops.append({"Slice": name, "Citing papers": n, "Reference": label[key][:200]})
write(pd.DataFrame(tops), "Topic_Slices_top_references.csv")

# ------------------------------------------------------------------ term trend (share of papers per year, whole corpus)
trend = []
for y in range(int(t0), int(t1) + 1):
    s = d[d.Year == y]
    trend.append({"Year": y, "Papers": len(s)} | {k: round(100 * s["text"].str.contains(p, regex=True).mean(), 1) if len(s) else 0 for k, p in (cfg.get("term_trend") or {}).items()})
write(pd.DataFrame(trend), "Topic_Slices_term_trend.csv")

# ------------------------------------------------------------------ gap audit: papers whose text matches all the audit patterns
audit_cfg, lit = cfg.get("audit"), cfg.get("literature") or {}
CITES = {"topic": "Topic_Slices_cites_first_literature_and_audit_topic.csv", "any": "Topic_Slices_cites_first_literature_any_topic.csv", **(cfg.get("cites_files") or {})}
md = ["# Topic_Slices report (generated by Topic_Slices.py)", "", "## Slices", md_table(overview), "", "## Share of papers per year that mention a term (whole corpus, %)", md_table(pd.DataFrame(trend)), ""]
low = refs.assign(r=refs["Reference"].str.lower())
topic = None
if audit_cfg:
    pats = [re.compile(p) for p in audit_cfg["all_of"]]
    TERMS_COL = audit_cfg.get("terms_column", "Matched terms")
    flags = audit_cfg.get("flags") or {}
    hit = d[d["text"].map(lambda t: all(p.search(t) for p in pats))].copy()
    hit[TERMS_COL] = hit["text"].map(lambda t: "; ".join(sorted(set(pats[audit_cfg.get("terms_from", 0)].findall(t)))))
    for fl, p in flags.items():
        hit[fl] = hit["text"].str.contains(p, regex=True)
    fl_names = list(flags)
    if fl_names:
        hit = hit.sort_values(fl_names[::-1] + ["Year"], ascending=False)
    write(hit[["Year", "Cited by", "Title", "Source title", "DOI", TERMS_COL] + fl_names + ["Query_IDs"]], "Topic_Slices_gap_audit.csv")
    topic = [pats[i] for i in audit_cfg.get("topic", [])]
    strict = fl_names[-1] if fl_names else None
    summary = f"{len(hit)} papers match all {len(pats)} patterns" + (f"; {int(hit[strict].sum())} also match '{strict}'" if strict else "") + "."
    md += [f"## Gap audit: {audit_cfg.get('title', 'papers matching all the patterns')}", summary, "",
           md_table(hit[hit[strict]][["Year", "Cited by", "Title", TERMS_COL]]) if strict and hit[strict].any() else "(none flagged)", ""]
else:
    for n in ("Topic_Slices_gap_audit.csv",):
        remove(n)


def about_topic(t):
    return all(p.search(t) for p in topic) if topic else False


# ------------------------------------------------------------------ reference audit: who cites the literature listed under "literature"
if lit:
    audit = []
    for name, pat in lit.items():
        eids = set(low.loc[low["r"].str.contains(pat, regex=True), "EID"])
        sub = d[d["EID"].isin(eids)]
        audit.append({"Cited literature": name, "Citing papers": len(sub), **({(audit_cfg or {}).get("topic_column", "of which about the audit topic (text)"): sum(1 for t in sub["text"] if about_topic(t))} if topic else {}),
                      f"of which {RECENT[0]}-{str(RECENT[-1])[-2:]}": int(sub.Year.isin(RECENT).sum())})
    write(pd.DataFrame(audit), "Topic_Slices_reference_audit.csv")
    first = set(low.loc[low["r"].str.contains(next(iter(lit.values())), regex=True), "EID"])
    if topic:
        write(d[d["EID"].isin(first) & d["text"].map(about_topic)][["Year", "Cited by", "Title", "Source title", "DOI"]].sort_values("Year", ascending=False), CITES["topic"])
    md += [f"## Who cites the literature listed in topic_slices.json", md_table(pd.DataFrame(audit)), ""]
    # the papers that cite the first literature, whatever their topic (the reading candidates)
    write(d[d["EID"].isin(first)][["Year", "Cited by", "Title", "Source title", "DOI", "Query_IDs"]].sort_values("Year", ascending=False), CITES["any"])
else:
    for n in ("Topic_Slices_reference_audit.csv", CITES["topic"], CITES["any"]):
        remove(n)
(HERE / "Topic_Slices_report.md").write_text("\n".join(md), encoding="utf-8")
print("written Topic_Slices_report.md")
