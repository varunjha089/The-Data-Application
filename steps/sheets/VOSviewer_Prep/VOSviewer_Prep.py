"""Sheet "VOSviewer_Prep": prepares the VOSviewer maps (https://www.vosviewer.com) of the project's export. It writes the folder VOS/ in the project,
with one folder per map and, in each, a STEPS.md (every screen and choice of VOSviewer, with thresholds worked out from THIS data and the numbers to
expect) and the thesaurus that map needs, ready to load. VOS/README.md lists the folders and the order to make them in.
Thesauri (tab-separated CSV, as VOSviewer reads them: a name with a quote is quoted and the quote doubled):
  organizations  every affiliation string -> its institution (rules of common/names.py), when two or more strings name the same institution, when the
                 institution is a university, or when the string starts with it (only the place is cut); --org-level parent joins institutes into
                 their parent (CAS, CNRS, CSIC, ...)
  keywords       author keywords that differ only in case, hyphens, spaces or a plural "s", and "long form (ACRONYM)" pairs -> the most used form
  cited sources  journal names that differ only in case, accents, punctuation, "&", "The" or a "(Switzerland)"-type suffix -> the most used form
  terms          "long form (ACRONYM)" pairs found in the abstracts -> the acronym; plus terms_to_untick.txt (months, units, general words)
Data checks written into the STEPS: Scopus subscript markup <inf>..</inf> (VOSviewer turns it into the term "inf": then VOS/VOSviewer_ready.csv is
written without the tags), references in Scopus' newer style or cut to about 10 per paper (citation maps then lose links), papers with many authors.
A file of VOS/ that was changed after the application wrote it is never overwritten: the new version is written next to it as <name>.new.<ext>.
Excel: none (VOSviewer is a separate program).
Your choices: --org-level institution|parent (default institution).
Input : --raw the project's copy of the export (the file VOSviewer must read too), common/names.py
Output: VOSviewer_Prep.csv (one row per folder: map, files, suggested threshold, notes) and the folder ../VOS/
Run   : python3 VOSviewer_Prep.py --raw ../data/raw/<export>.csv [--org-level institution]
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the project folder: 01_Clean_Data, one folder per sheet, data/raw
OUT = HERE / "VOSviewer_Prep.csv"
VOS = SHEETS / "VOS"
MANIFEST = VOS / ".generated.json"                           # sha-256 of every file as the application wrote it (to see edits by the user)
sys.path.insert(0, str(SHEETS / "common"))                    # shared name rules, copied into the project by the application
from names import canonical_names, country_of_affiliation, institution_key, institution_of_affiliation, parent_of_affiliation  # noqa: E402

csv.field_size_limit(10**9)
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
GENERAL = ["study", "paper", "article", "review", "author", "accordance", "approach", "method", "result", "analysis", "data", "model", "use", "case",
           "area", "region", "research", "application", "performance", "accuracy", "help", "great significance", "last decade", "recent year",
           "art", "life", "increase", "estimate", "opportunity", "solution", "gap", "cost", "consistency", "agreement", "study site", "high precision",
           "effective monitoring", "practice", "implementation", "technology", "loss", "chapter", "prospect", "attention", "difficulty",
           "experimental result", "good agreement", "wide range", "total", "average", "object", "scene", "aspect", "advance", "advancement"]
UNITS = ["inf", "sup", "g l", "mg l", "km2", "m resolution", "km", "m2"]
# the institution is missing from some addresses, so the rules take the city; individuals are never institutions
CITY_FIX = {"Hanover": "Dartmouth College (Hanover, NH)", "Mansoura": "Mansoura University", "Fayoum": "Fayoum University",
            "Enschede": "University of Twente (ITC)", "Cookeville": "Tennessee Technological University", "Minneapolis": "University of Minnesota",
            "Mississippi State": "Mississippi State University", "Princeton": "Princeton University", "Merced": "University of California, Merced",
            "Institute of Industrial Science, Tokyo": "The University of Tokyo (IIS)"}
NOT_INSTITUTIONS = {"Citizen Scientist", "Independent Consultant", "Ministry of Education"}
GENERIC_COMPANY = {"ltd", "ltd.", "co.", "co", "inc", "inc.", "llc", "gmbh", "corp", "corp.", "s.a.", "srl", "s.r.l.", "pvt. ltd.", "limited", "company"}
REF_NUM = re.compile(r"^(\d+|\(\d{4}\)|\d+-\d+|pp\..*)$")


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


# ---------------------------------------------------------------- writing VOS/ without overwriting the user's edits
manifest = {}
kept = []


def put(rel, text):
    """write VOS/<rel> unless the user changed the file since the application wrote it (then write <name>.new.<ext> next to it)"""
    path = VOS / rel
    data = text.encode("utf-8")
    new = hashlib.sha256(data).hexdigest()
    if path.exists():
        cur = hashlib.sha256(path.read_bytes()).hexdigest()
        if cur == new:
            manifest[rel] = new
            return
        if manifest.get(rel) != cur:                          # not the application's last version: the user's file
            alt = path.with_name(f"{path.stem}.new{path.suffix}")
            alt.write_bytes(data)
            kept.append(rel)
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    manifest[rel] = new


def tsv(pairs):
    """a VOSviewer thesaurus: label <tab> replace by, quoted CSV-style where needed"""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    w.writerow(["label", "replace by"])
    for a, b in pairs:
        w.writerow([a.replace("\t", " "), b.replace("\t", " ")])
    return buf.getvalue()


def ladder(counts, steps):
    """'3 -> 297, 4 -> 192, ...': how many items have at least t (documents, occurrences, citations)"""
    return ", ".join(f"{t} → {sum(1 for v in counts.values() if v >= t):,}" for t in steps)


def suggest(counts, steps, most):
    """the smallest threshold that leaves at most `most` items (else the largest one)"""
    for t in steps:
        if sum(1 for v in counts.values() if v >= t) <= most:
            return t
    return steps[-1]


def split(value, sep=";"):
    return [p.strip() for p in (value or "").split(sep) if p.strip()]


# ---------------------------------------------------------------- the thesauri
def organization_thesaurus(rows, level):
    affs = Counter(a for r in rows for a in split(r.get("Affiliations")))
    inst = {a: institution_of_affiliation(a) for a in affs}
    canon = canonical_names([i for a, i in inst.items() for _ in range(affs[a]) if i])
    target = {}
    for a in affs:
        t = (level == "parent" and parent_of_affiliation(a)) or (canon.get(inst[a]) if inst[a] else None)
        if t and t.strip().lower() not in GENERIC_COMPANY:
            t = CITY_FIX.get(t, t)
            if t not in NOT_INSTITUTIONS:
                target[a] = t
    group = Counter(target.values())
    pairs = []
    for a in sorted(affs):
        t = target.get(a)
        if not t or t == a:
            continue
        first = a.split(",")[0].strip()
        safe = ((institution_key(first) == institution_key(inst[a] or "") and not first[:1].isdigit())
                or "univ" in (inst[a] or "").lower() or t in CITY_FIX.values())
        if group[t] >= 2 or safe:
            pairs.append((a, t))
    mapped = dict(pairs)
    per_paper = Counter(n for r in rows for n in {mapped.get(a, a) for a in split(r.get("Affiliations"))})
    return pairs, len(affs), per_paper


def norm_keyword(k):
    s = unicodedata.normalize("NFKD", k)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    key = re.sub(r"[^a-z0-9]", "", s)
    return key or k.lower().strip()                         # a keyword in another script (Chinese, ...) keeps its own key: never merged with others


def keyword_thesaurus(rows):
    kw = Counter(k.lower() for r in rows for k in split(r.get("Author Keywords")))
    groups = defaultdict(list)
    for k in kw:
        groups[norm_keyword(k)].append(k)
    for key in list(groups):                                  # plural "s": only when the singular is used too ("floods" + "flood")
        if key.endswith("s") and not key.endswith(("ss", "is", "us")) and key[:-1] in groups and len(key) > 4:
            groups[key[:-1]] += groups.pop(key)
    to = {}
    for v in groups.values():
        if len(v) > 1:
            best = max(v, key=lambda k: (kw[k], -len(k)))
            to.update({k: best for k in v if k != best})
    acr = defaultdict(Counter)                                # "synthetic aperture radar (sar)" -> long form and acronym
    for k in kw:
        m = re.fullmatch(r"(.+?)\s*\(([a-z0-9\-]{2,8})\)", k)
        if m and m.group(2).replace("-", "")[:1] == m.group(1)[:1]:
            acr[m.group(2)][m.group(1).strip()] += kw[k]
    for a, longs in acr.items():
        long = longs.most_common(1)[0][0]
        forms = [f for f in (a, long, f"{long} ({a})") if f in kw]
        best = max(forms, key=lambda f: (kw[f] + sum(n for k, n in kw.items() if to.get(k) == f), -len(f)))
        for f in forms:
            if f != best:
                to[f] = best
    for k in list(to):                                        # follow chains (a -> b -> c)
        seen = set()
        while to[k] in to and to[k] not in seen:
            seen.add(to[k])
            to[k] = to[to[k]]
    pairs = sorted((k, b) for k, b in to.items() if k != b)
    per_paper = Counter(m for r in rows for m in {to.get(k.lower(), k.lower()) for k in split(r.get("Author Keywords"))})
    return pairs, len(kw), per_paper


def source_of(ref):
    parts = [p.strip() for p in ref.split(", ")]
    for i, p in enumerate(parts):
        if i >= 1 and REF_NUM.match(p):
            return parts[i - 1]
    return None


def source_key(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().replace("&", " and ")
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r"\((switzerland|basel|united kingdom|netherlands)\)", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def cited_source_thesaurus(rows):
    count = Counter(s for r in rows for ref in split(r.get("References"), "; ") for s in [source_of(ref)] if s)
    groups = defaultdict(list)
    for s, n in count.items():
        groups[source_key(s)].append((n, s))
    pairs = []
    for v in groups.values():
        if len(v) > 1:
            best = sorted(v, key=lambda t: (-t[0], len(t[1].split()), t[1]))[0][1]
            pairs += [(s, best) for _, s in v if s != best]
    merged = Counter()
    to = dict(pairs)
    for s, n in count.items():
        merged[to.get(s, s)] += n
    return sorted(pairs), len(count), merged


def term_thesaurus(rows):
    """'root mean square error (RMSE)' in the abstracts: the long form and the acronym become one term, named by the form the abstracts use more often
    (rmse, sar, ndwi stay acronyms; "overall accuracy" stays written out); only pairs seen 3 times or more, one long form per acronym"""
    pairs = defaultdict(Counter)
    texts = []
    for r in rows:
        text = re.sub(r"</?(inf|sup)>", "", f"{r.get('Title', '')}. {r.get('Abstract', '')}")
        texts.append(text)
        for m in re.finditer(r"((?:[A-Za-z][A-Za-z\-]*\s+){1,7})\(([A-Z][A-Za-z0-9\-]{1,9})\)", text):
            acro = m.group(2)
            letters = [c for c in acro if c.isupper()]
            words = m.group(1).split()
            if not 2 <= len(letters) <= 7 or len(words) < len(letters):
                continue
            long = words[-len(letters):]
            if [w[0].lower() for w in long] == [c.lower() for c in letters]:
                pairs[acro.lower()][" ".join(long).lower()] += 1
    whole = "\n".join(texts)
    low = whole.lower()
    out = []
    for a, longs in sorted(pairs.items()):
        long, n = longs.most_common(1)[0]
        if n >= 3 and long != a:
            n_acr = len(re.findall(rf"(?<![A-Za-z0-9]){re.escape(a)}(?![A-Za-z0-9])", whole, re.I))
            n_long = low.count(long)
            out.append((long, a) if n_acr >= n_long else (a, long))
    return out


# ---------------------------------------------------------------- facts about the export
def reference_facts(rows):
    refs = [split(r.get("References"), "; ") for r in rows]
    with_refs = [x for x in refs if x]
    flat = [x for r in with_refs for x in r]
    newer = sum(1 for x in flat for p in [x.split(", ")] if len(p) >= 3 and not p[0].endswith(".") and re.match(r"^[A-ZÀ-Þ][a-zà-ÿ]{2,}", p[1])
                and not any(c.isdigit() for c in p[1]) and len(p[1]) <= 40)
    return {"papers_with_refs": len(with_refs), "max_refs": max((len(x) for x in with_refs), default=0),
            "mean_refs": sum(len(x) for x in with_refs) / max(len(with_refs), 1), "refs": len(flat), "newer_share": newer / max(len(flat), 1)}


def classic_refs(rows):
    """a copy of the rows with every reference's first author in the classic style ("Camici, Stefania," -> "Camici S.,")"""
    name = re.compile(r"^[A-ZÀ-ÖØ-Þ][\w'’.\- ]*$")

    def initials(given):
        return "".join("-".join(p[0] + "." for p in w.split("-") if p) for w in given.replace(".", ". ").split())

    def one(ref):
        p = ref.split(", ", 2)
        if len(p) == 3 and name.match(p[1]) and len(p[1]) <= 40 and not any(c.isdigit() for c in p[1]):
            return f"{p[0]} {initials(p[1])}, {p[2]}"
        return ref
    return [{**r, "References": "; ".join(one(x) for x in (r.get("References") or "").split("; "))} for r in rows]


def csv_text(rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


# ---------------------------------------------------------------- the STEPS texts
BIB = """1. **Create...** → *Create a map based on bibliographic data* → **Next** → *Read data from bibliographic database files* → **Next**.
2. Tab **Scopus** → choose `{data}` → **Next**."""
SAVE = """**Screenshot → Save** (PNG) → `{png}`; tab *Overlay visualization* (Scores: *Avg. pub. year*) → **Screenshot → Save** → `{overlay}`.
   **Save...** → tab **VOSviewer** → map file `{stem}_map.txt`, network file `{stem}_network.txt` (with the **...** buttons, this folder) → **OK**."""
RECORD = """## Record here after the run

- Items: ___ passing the threshold, ___ on the map (largest connected set), clusters: ___, links: ___
- Notes: ___
"""


def steps_file(title, shows, body, watch, check=""):
    text = f"# {title}\n\n**Shows:** {shows}\n**Input:** {{input_note}}\n\n## Steps in VOSviewer\n\n{body}\n\n## Watch out\n\n{watch}\n"
    if check:
        text += f"\n## Check after the run\n\n{check}\n"
    return text + "\n" + RECORD


def main():
    ap = argparse.ArgumentParser(description="Sheet VOSviewer_Prep")
    ap.add_argument("--raw", required=True, help="the project's copy of the export (the file VOSviewer reads)")
    ap.add_argument("--org-level", choices=["institution", "parent"], default="institution")
    args = ap.parse_args()
    raw = Path(args.raw).resolve()
    with open(raw, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys()) if rows else []
    if not rows:
        raise SystemExit(f"{raw.name} has no rows.")
    VOS.mkdir(exist_ok=True)
    if MANIFEST.exists():
        manifest.update(json.loads(MANIFEST.read_text(encoding="utf-8")))
    try:
        data = Path("..") / ".." / raw.relative_to(SHEETS)
    except ValueError:
        data = raw
    n = len(rows)
    inf = sum(1 for r in rows if re.search(r"<(inf|sup)>", r.get("Title", "") + r.get("Abstract", "")))
    ready = inf > 0
    data_terms = Path("..") / "VOSviewer_ready.csv" if ready else data
    many_authors = sum(1 for r in rows if len(split(r.get("Author full names") or r.get("Authors"))) > 25)
    refs = reference_facts(rows) if "References" in fields else None
    cut = bool(refs and refs["max_refs"] <= 12)
    newer = bool(refs and refs["newer_share"] > 0.5)
    summary = []

    def note(text):
        return text.replace("{input_note}", f"`{data}` (the project's copy of the export, {n:,} documents). VOSviewer must read this file: the thesaurus "
                                            "labels are taken from it.")

    # --- countries
    cpp = Counter(c for r in rows for c in {country_of_affiliation(a) for a in split(r.get("Affiliations"))} if c)
    t_c = suggest(cpp, [3, 5, 10, 20], 80)
    body = f"""{BIB.format(data=data)}
3. **Type of analysis: Co-authorship.** **Unit of analysis: Countries.** **Counting method: Full counting.** Thesaurus: none. Keep *Ignore documents
   co-authored by a large number of countries* ticked, maximum **25** → **Next**.
4. **Minimum number of documents of a country: {t_c}** (countries with at least 1, 3, 5, 10, 20 documents in this data: {ladder(cpp, [1, 3, 5, 10, 20])}) → **Next**.
5. **Number of countries to be selected:** keep all (fewer would change Links and Total link strength) → **Next** → **Finish**.
6. {SAVE.format(png="Co-Authorship_Countries_map.png", overlay="Co-Authorship_Countries_overlay.png", stem="countries")}"""
    watch = """- VOSviewer writes country names in lower case and keeps only the largest connected set: one or two countries without foreign co-authors may drop out.
- A **top-10 table** like Table 4 of many scientometric papers (Country, Documents, Citations, Avg. pub. year, Links, Avg. citations, Avg. norm. citations,
  Total link strength) is the map file sorted by `weight<Documents>`, ties by `weight<Citations>`."""
    top = ", ".join(f"{c} {v}" for c, v in cpp.most_common(3))
    put("Co-Authorship_Countries/STEPS.md", note(steps_file("Co-authorship of countries", "which countries publish together.", body, watch,
        f"Counted by this application (a country once per paper): {top}. VOSviewer's numbers can differ by a document or two (its own address rules).")))
    summary.append(("Co-Authorship_Countries", "Co-authorship, countries", "STEPS.md", t_c, ""))

    # --- organizations
    org_pairs, org_strings, opp = organization_thesaurus(rows, args.org_level)
    put("Co-Authorship_Organizations/thesaurus_organizations.txt", tsv(org_pairs))
    t_o = suggest(opp, [3, 5, 10, 20], 250)
    body = f"""{BIB.format(data=data)}
3. **Type of analysis: Co-authorship.** **Unit of analysis: Organizations.** **Counting method: Full counting.**
   **Thesaurus: ...** → `thesaurus_organizations.txt` (this folder; check that its name shows in the box) → **Next**.
4. **Minimum number of documents of an organization: {t_o}** (after the thesaurus: {ladder(opp, [1, 3, 5, 10, 20])}) → **Next**.
5. Keep all → **Next** → **Finish**; *largest connected set only?* → **Yes** (write down how many remain).
6. Labels are cut at 30 characters: **Visualization → Labels → Max. length** 50 before the screenshot.
7. {SAVE.format(png="Co-Authorship_Organizations_map.png", overlay="Co-Authorship_Organizations_overlay.png", stem="organizations")}"""
    watch = f"""- VOSviewer takes every affiliation string as one organization ({org_strings:,} different strings in this export). The thesaurus maps
  {len(org_pairs):,} of them to {len(set(b for _, b in org_pairs)):,} institutions (level: {args.org_level}). Strings whose institution appears only once
  and does not start the string are left as they are.
- **Check that the thesaurus was applied:** on the threshold screen the number of organizations must be well below {org_strings:,}.
- Never merged: company suffixes ("Ltd."), "Citizen Scientist", "Independent Consultant", "Ministry of Education" (key laboratories of many
  universities). Some addresses give only a city; a few known ones are fixed (Hanover NH → Dartmouth College, Enschede → University of Twente (ITC), ...).
- The file is tab-separated CSV: a name with `"` must stay quoted with the quote doubled (VOSviewer: "Incorrect use of quotes" otherwise)."""
    top = ", ".join(f"{k} {v}" for k, v in opp.most_common(3))
    put("Co-Authorship_Organizations/STEPS.md", note(steps_file("Co-authorship of organizations", "the leading institutions and their partners.", body,
        watch, f"Counted by this application after the thesaurus: {top}.")))
    summary.append(("Co-Authorship_Organizations", "Co-authorship, organizations", "STEPS.md, thesaurus_organizations.txt", t_o,
                    f"{len(org_pairs)} affiliation strings mapped"))

    # --- authors
    app_ = Counter(re.sub(r"\s*\(\d+\)$", "", a).lower() for r in rows for a in set(split(r.get("Author full names")))
                   if len(split(r.get("Author full names"))) <= 25)
    t_a = suggest(app_, [3, 5, 10], 250)
    body = f"""{BIB.format(data=data)}
3. **Type of analysis: Co-authorship.** **Unit of analysis: Authors.** **Counting method: Full counting.** Thesaurus: none. Keep *Ignore documents
   with a large number of authors* ticked, maximum **25**. Leave *Reduce first names of authors to initials* **unticked** → **Next**.
4. **Minimum number of documents of an author: {t_a}** ({ladder(app_, [2, 3, 5, 10])}) → **Next** → keep all → **Finish**.
5. *Largest connected set only?* **Yes** gives the connected core (groups without a co-author in it drop out, even very productive ones);
   **No** shows every group. Write down which you chose.
6. {SAVE.format(png="Co-Authorship_Authors_map.png", overlay="Co-Authorship_Authors_overlay.png", stem="authors")}"""
    watch = f"""- VOSviewer identifies authors by name, not by Scopus Author ID: compare the leading authors with the application's Author impact table.
- {many_authors} paper(s) of this export have more than 25 authors: they are ignored, so their authors show one document less here."""
    put("Co-Authorship_Authors/STEPS.md", note(steps_file("Co-authorship of authors", "the collaboration groups of the field.", body, watch)))
    summary.append(("Co-Authorship_Authors", "Co-authorship, authors", "STEPS.md", t_a, f"{many_authors} papers over 25 authors"))

    # --- author keywords
    kw_pairs, kw_all, kpp = keyword_thesaurus(rows)
    put("Co-Occurrence_Author_Keywords/thesaurus_keywords.txt", tsv(kw_pairs))
    t_k = suggest(kpp, [3, 4, 5, 7, 10, 15], 150)
    common = [k for k, v in kpp.most_common(10) if v >= 0.10 * n]
    body = f"""{BIB.format(data=data)}
3. **Type of analysis: Co-occurrence.** **Unit of analysis: Author keywords.** **Counting method: Full counting.**
   **Thesaurus: ...** → `thesaurus_keywords.txt` (this folder) → **Next**.
4. **Minimum number of occurrences of a keyword: {t_k}** (after the thesaurus: {ladder(kpp, [3, 4, 5, 7, 10, 15])}; aim for about 70–150) → **Next** → keep all → **Next**.
5. **Verify selected keywords: untick** your search terms and very general keywords{(' (in 10 % or more of the papers here: ' + ', '.join(common) + ')') if common else ''}
   → **Finish**.
6. Clusters: *Analysis → Resolution* lower = fewer clusters, *Min. cluster size* merges tiny ones (**Update**). Labels: *Visualization → Labels → Size
   variation* about 0.3 so large circles get a label.
7. {SAVE.format(png="Co-Occurrence_Author_Keywords_map.png", overlay="Co-Occurrence_Author_Keywords_overlay.png", stem="keywords")}
8. Cluster names are not a VOSviewer feature: read each cluster's keywords in the map file and type the names onto the picture (PowerPoint, Keynote)."""
    watch = f"""- {kw_all:,} different author keywords; the thesaurus merges {len(kw_pairs)} spellings (case, hyphens, spaces, plural "s", "long form
  (acronym)"). Merges of meaning ("landsat 8" → "landsat") are your choice: add lines to the thesaurus (label <tab> replace by) and run again.
- Overlay colours: set the range with **Customize** to the years where most keywords lie, or every keyword looks the same green."""
    put("Co-Occurrence_Author_Keywords/STEPS.md", note(steps_file("Co-occurrence of author keywords", "the topics of the field and how they connect.",
        body, watch)))
    summary.append(("Co-Occurrence_Author_Keywords", "Co-occurrence, author keywords", "STEPS.md, thesaurus_keywords.txt", t_k,
                    f"{len(kw_pairs)} keyword spellings merged"))

    # --- terms of titles and abstracts
    term_pairs = term_thesaurus(rows)
    put("Text_Terms_Title_Abstract/thesaurus_terms.txt", tsv(term_pairs))
    put("Text_Terms_Title_Abstract/terms_to_untick.txt", "\n".join(["# Terms to untick on the 'Verify selected terms' screen when they appear "
        "(the search terms of the project belong here too).", "# Not words: markup and units", *UNITS, "# Months", *MONTHS,
        "# General words", *GENERAL]) + "\n")
    if ready:
        clean = [{k: re.sub(r"</?(inf|sup)>", "", v or "") if k in ("Title", "Abstract") else v for k, v in r.items()} for r in rows]
        put("VOSviewer_ready.csv", csv_text(clean, fields))
    body = f"""1. **Create...** → *Create a map based on **text data*** → **Next** → *Read data from bibliographic database files* → **Next**.
   (A screen with *Type of analysis / Unit of analysis* belongs to the bibliographic path: go **Back** to the first screen.)
2. Tab **Scopus** → choose `{data_terms}` → **Next**.
3. **Choose fields: Title and abstract fields**; tick *Ignore structured abstract labels* and *Ignore copyright statements* → **Next**.
4. **Choose counting method: Binary counting** (a term counts once per paper). The **thesaurus box is on this screen**: `thesaurus_terms.txt`
   (this folder) → **Next**.
5. **Minimum number of occurrences of a term: 10** (raise to 15–20 for a less crowded map) → **Next** → keep the default 60 % most relevant → **Next**.
6. **Verify selected terms:** untick every term of `terms_to_untick.txt` that appears, and your search terms → **Finish**.
7. Aim for 4–6 clusters (*Analysis → Resolution*, **Update**).
8. {SAVE.format(png="Text_Terms_map.png", overlay="Text_Terms_overlay.png", stem="terms")}"""
    watch = (f"- **{inf} document(s) contain Scopus subscript markup** (`R<inf>rs</inf>`, `PM<inf>2.5</inf>`): VOSviewer turns every tag into the term "
             f"\"inf\". So step 2 uses `VOSviewer_ready.csv` (in `VOS/`): the same export with the tags removed (Rrs, PM2.5).\n" if ready else
             "- No Scopus subscript markup (`<inf>`) in this export.\n") + \
        f"""- The thesaurus maps {len(term_pairs)} long forms to their acronyms as written in the abstracts ("root mean square error" → "rmse").
- Units ("g l" from g/L), months and general words are not removed by a thesaurus: untick them (list in `terms_to_untick.txt`). Missing many of them
  makes a noisy map; unticking takes a few minutes but is worth it."""
    put("Text_Terms_Title_Abstract/STEPS.md", note(steps_file("Terms of titles and abstracts", "the topics found in the papers' own text (a cross-check "
        "of the keyword clusters).", body, watch)))
    summary.append(("Text_Terms_Title_Abstract", "Text data, title and abstract terms", "STEPS.md, thesaurus_terms.txt, terms_to_untick.txt", 10,
                    f"{inf} documents with <inf> markup" if ready else ""))

    # --- citation and co-citation (all built from the references)
    cites = Counter({i: int(r.get("Cited by") or 0) for i, r in enumerate(rows) if str(r.get("Cited by") or "0").isdigit()})
    t_d = suggest(cites, [10, 20, 30, 50, 100], 150)
    if refs:
        ref_warn = []
        if newer:
            ref_warn.append(f"- **{refs['newer_share']:.0%} of the references are in Scopus' newer style** (\"Camici, Stefania, Title, Journal, 661, (2025)\"). "
                            "On such an export VOSviewer found NO citation links and read only 15–58 % of the cited sources. Run the test in "
                            "`../Reference_Format_Test/` first.")
        if cut:
            ref_warn.append(f"- **At most {refs['max_refs']} references per paper** (mean {refs['mean_refs']:.1f}): this export keeps only the first ten or so. "
                            "Every reference-based map is thin; a new export with complete reference lists is better.")
        ref_warn = "\n".join(ref_warn) or "- The references look complete and in the classic Scopus style."
    else:
        ref_warn = "- This export has **no References column**: citation, co-citation and coupling maps cannot be made. Export again with *References*."
    check = "Open `*_network.txt` right after saving: if it is empty (a few bytes), VOSviewer found no links and the map is not a network."
    body = f"""{BIB.format(data=data)}
3. **Type of analysis: Citation.** **Unit of analysis: Documents** → **Next**.
4. **Minimum number of citations of a document: {t_d}** ({ladder(cites, [10, 20, 30, 50, 100])}) → **Next** → keep all → **Finish**;
   *largest connected set only?* → **No** first.
5. {SAVE.format(png="Citation_Documents_map.png", overlay="Citation_Documents_overlay.png", stem="documents")}
6. The same with **Unit of analysis: Sources**, minimum **5** documents of a source → `Citation_Sources_map.png`, `sources_map.txt`, `sources_network.txt`."""
    put("Citation_Documents_and_Sources/STEPS.md", note(steps_file("Citation of documents and sources", "the most cited papers / journals and who cites whom.",
        body, ref_warn, check)))
    summary.append(("Citation_Documents_and_Sources", "Citation, documents and sources", "STEPS.md", t_d, "needs complete references" if (newer or cut) else ""))
    cs_pairs, cs_all, cs_count = cited_source_thesaurus(rows) if refs else ([], 0, Counter())
    put("Co-Citation_and_Bibliographic_Coupling/thesaurus_cited_sources.txt", tsv(cs_pairs))
    t_s = suggest(cs_count, [10, 20, 30, 50], 150)
    body = f"""{BIB.format(data=data)}
3. **Type of analysis: Co-citation.** **Unit of analysis: Cited sources.** Full counting. **Thesaurus: ...** → `thesaurus_cited_sources.txt` (this folder)
   → **Next** (the note "Scopus data on cited sources may not have been harmonized" is normal: it is what the thesaurus is for).
4. **Minimum number of citations of a source: {t_s}** ({ladder(cs_count, [10, 20, 30, 50])}) → **Next** → verify: **untick `undefined`** → **Finish**.
5. Save `Co-Citation_Sources_map.png`, `cocitation_sources_map.txt`, `cocitation_sources_network.txt`.
6. **Bibliographic coupling**, Unit **Documents**, minimum citations **10** → `Coupling_Documents_map.png`, `coupling_documents_map.txt`, `coupling_documents_network.txt`."""
    check2 = (f"Compare a few journals' citations on the map with the counts in the references (application's count): "
              + ", ".join(f"{k} {v}" for k, v in cs_count.most_common(4)) + ". Much lower numbers mean VOSviewer could not read the references.") if cs_count else ""
    put("Co-Citation_and_Bibliographic_Coupling/STEPS.md", note(steps_file("Co-citation and bibliographic coupling", "the intellectual base (sources cited "
        "together) and the research fronts (papers sharing references).", body, ref_warn + f"\n- {cs_all:,} cited source names; the thesaurus merges "
        f"{len(cs_pairs)} spellings.", check2)))
    summary.append(("Co-Citation_and_Bibliographic_Coupling", "Co-citation of sources, bibliographic coupling", "STEPS.md, thesaurus_cited_sources.txt", t_s,
                    "needs complete references" if (newer or cut) else ""))
    if newer:
        put("Reference_Format_Test/export_classic_refs_TEST.csv", csv_text(classic_refs(rows), fields))
        put("Reference_Format_Test/STEPS.md", f"""# Test: does VOSviewer find citation links with classic-style references?

`export_classic_refs_TEST.csv` is the export with the first author of every reference rewritten ("Camici, Stefania," → "Camici S.,"); nothing else
changes. Run the citation of documents (see `../Citation_Documents_and_Sources/STEPS.md`) on it instead of the export. Links appear: the reference
style was the cause, use this file for the citation maps. Still no links: only a new export helps. A TEST file: use it for nothing else.

Result: links found ___
""")
        summary.append(("Reference_Format_Test", "Test of the reference style", "STEPS.md, export_classic_refs_TEST.csv", "", "references in the newer style"))

    # --- README
    lines = ["# VOS: VOSviewer maps of this project", "",
             f"Made by The Data Application (sheet *VOSviewer preparation*) from `{raw.name}` ({n:,} documents). One folder per map: open its `STEPS.md`,",
             "follow it in VOSviewer, save the files it names into the same folder, and write the numbers into its *Record* block. A file you change here",
             "is never overwritten when this sheet is generated again (the new version is written next to it as `<name>.new.<ext>`).", "",
             "| Folder | Map | Files | Suggested threshold | Note |", "|---|---|---|---|---|"]
    lines += [f"| `{a}/` | {b} | {c} | {d} | {e} |" for a, b, c, d, e in summary]
    lines += ["", "Suggested order: author keywords (then its overlay and density views), countries, organizations, terms, authors; the "
              "reference-based maps last" + (" (see their warnings)." if (newer or cut) else "."), "",
              "Data checks: " + "; ".join(x for x in [f"{inf} documents with `<inf>` markup → `VOSviewer_ready.csv` for the text map" if ready else "",
                                                      f"{refs['newer_share']:.0%} of the references in Scopus' newer style" if newer else "",
                                                      f"at most {refs['max_refs']} references per paper" if cut else "",
                                                      f"{many_authors} papers with more than 25 authors"] if x) + "."]
    put("README.md", "\n".join(lines) + "\n")
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    write(pd.DataFrame(summary, columns=["Folder", "VOSviewer map", "Files", "Suggested threshold", "Note"]))
    print(f"VOS/ written: {len(summary)} folders; thesauri: organizations {len(org_pairs)}, keywords {len(kw_pairs)}, cited sources {len(cs_pairs)}, "
          f"terms {len(term_pairs)} lines" + (f"; VOSviewer_ready.csv ({inf} documents with <inf> markup)" if ready else ""))
    if kept:
        print("kept your edited files (new versions written next to them as *.new.*): " + ", ".join(kept))


main()
