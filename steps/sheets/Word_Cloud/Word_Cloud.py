"""Sheet "Word_Cloud": how many papers use each keyword (the counts behind the word cloud).
Excel: split the keyword cell of every paper at "; " into rows (Power Query: Split Column by Delimiter, into Rows), remove duplicate (paper, keyword) rows,
then a PivotTable: rows = keyword, values = count of EID; largest first. Share of Papers (%) = Papers / all papers * 100.
The cleaning has already written the keywords in lower case with "-" and "_" as spaces, so "Deep-Learning" and "deep learning" are one keyword.
Spelling variants are merged (switch off with --no-merge), using only what this data shows:
  - an abbreviation in brackets: "retrieval augmented generation (rag)" is "retrieval augmented generation", and teaches that "rag" means it too
    (only when the abbreviation is one word that starts with the same letter; when it stands for several things, the most used meaning is taken)
  - a plural: "large language models" is "large language model" and "llms" is "llm", when the singular is also a keyword of the data
  A paper counts once for the merged keyword. Its name is the full name (the more used of singular and plural), else the most used variant
  without brackets; column "Variants" lists the others.
Your choice: --field author (Author Keywords, the default), index (Index Keywords, added by Scopus) or both (a keyword in both lists counts once per paper).
Input : 01_Clean_Data/clean_main_data.csv        Output: Word_Cloud.csv (Keyword, Papers, Share of Papers (%), Variants)
Run   : python3 Word_Cloud.py [--field author|index|both] [--no-merge]
"""
import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Word_Cloud.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}
FIELDS = {"author": ["Author Keywords"], "index": ["Index Keywords"], "both": ["Author Keywords", "Index Keywords"]}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def merge_variants(papers):
    """{keyword: merged keyword} from {keyword: number of papers}"""
    def bracket(k):                                          # "full name (abbr)" -> ("full name", "abbr"), else (k, None)
        m = re.fullmatch(r"(.+?)\s*\(([^()\s]+)\)", k)
        return (m.group(1), m.group(2)) if m and m.group(2)[0] == m.group(1)[0] and len(m.group(2)) < len(m.group(1)) else (k, None)
    bases = {bracket(k)[0] for k in papers}
    single = lambda k: k[:-1] if k.endswith("s") and not k.endswith("ss") and len(k) > 3 and k[:-1] in bases else k
    meaning = defaultdict(Counter)                           # abbreviation -> {full name: papers}
    for k, n in papers.items():
        full, abbr = bracket(k)
        if abbr:
            meaning[single(abbr)][single(full)] += n
    means = {a: c.most_common(1)[0][0] for a, c in meaning.items()}
    return {k: means.get(single(bracket(k)[0]), single(bracket(k)[0])) for k in papers}


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


ap = argparse.ArgumentParser(description="Sheet Word_Cloud")
ap.add_argument("--field", choices=sorted(FIELDS), default="author", help="which keywords: author (default), index or both")
ap.add_argument("--merge", action=argparse.BooleanOptionalAction, default=True, help="merge plurals and abbreviations in brackets (default: yes)")
args = ap.parse_args()
d = read_csv(CLEAN)
cols = [c for c in FIELDS[args.field] if c in d.columns]
if not cols:
    print(f"SKIPPED: the export has no {' / '.join(FIELDS[args.field])} column, so there are no keywords for a word cloud and nothing was written.")
    print("Export again from Scopus with the keywords, or choose another kind of keywords on this sheet's page.")
    raise SystemExit(0)

pairs = []
for eid, *cells in d[["EID"] + cols].itertuples(index=False, name=None):
    for cell in cells:
        if isinstance(cell, str):
            pairs += [(eid, k.strip()) for k in cell.split(";") if k.strip()]
p = pd.DataFrame(pairs, columns=["EID", "Keyword"]).drop_duplicates()
raw = p.groupby("Keyword").size()
p["Group"] = p["Keyword"].map(merge_variants(raw.to_dict())) if args.merge else p["Keyword"]
names, variants = {}, {}
for g, ks in p.groupby("Group")["Keyword"]:
    used = raw[sorted(set(ks))].sort_values(ascending=False, kind="stable")
    full = [k for k in used.index if k in (g, g + "s")]           # the full name (singular or plural) rather than "rag" or "llms"
    plain = [k for k in used.index if "(" not in k]
    names[g] = (full or plain or list(used.index))[0]
    variants[g] = "; ".join(k for k in used.index if k != names[g])
t = p.drop_duplicates(["EID", "Group"]).groupby("Group").size().rename("Papers").reset_index()
t["Keyword"] = t["Group"].map(names)
t["Variants"] = t["Group"].map(variants)
t = t[["Keyword", "Papers", "Variants"]]
t = t.sort_values(["Papers", "Keyword"], ascending=[False, True]).reset_index(drop=True)
t.insert(2, "Share of Papers (%)", t["Papers"] / len(d) * 100)
merged = f" ({len(raw):,} before merging spelling variants)" if args.merge else ""
print(f"{', '.join(cols)}: {len(t):,} different keywords{merged} in {p['EID'].nunique():,} of {len(d):,} papers; the most used:")
print(t.head(15).drop(columns="Variants").to_string(index=False))
write(t)
