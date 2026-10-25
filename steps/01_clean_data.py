"""steps/01_clean_data.py : clean a Scopus CSV export and write one row per paper.

Run by the application (menu: "Clean the data"), or by hand:
    python3 steps/01_clean_data.py --input data/raw/<export>.csv --output data/clean/clean_main_data.csv
Needs pandas only. The input file is never changed. A text report is written next to the output (clean_report.txt).

The steps follow the Power Query steps of the study notes (query Clean_Main_Data), in the same order, so that the Excel workbook and this
file agree. Two general steps come first and a list of checks runs at the end.

  A. text hygiene on every text column: repair "mojibake" (UTF-8 text that was read as Windows-1252, "UniversitÃ¤t" -> "Universität"),
     remove control characters, decode HTML entities ("&amp;" -> "&"), trim spaces
  1. keep records whose EID starts with "2-s2.0-"; one row per EID
  2. count the references of each paper (Reference Count), then drop the long References column
  3. remove records with no authors
  4. remove duplicate papers: same Title Key (title in lower case, letters and digits only); keep the earliest year, then the most cited
  4b. remove duplicate papers with the same DOI (in any letter case), in the same order: the same paper indexed twice under two titles
  5. keywords: lower case, "-" and "_" become spaces, then trimmed
  6. affiliations / correspondence address: "& amp;" -> "&", Türkiye -> Turkey, Viet Nam -> Vietnam, "UPMC Univ. Paris 06;" -> "UPMC Univ. Paris 06, France;"
  7. Countries (distinct country of each affiliation, in order), Country Count, Collaboration Type (SCP = 1 country, MCP = 2 or more).
     An address written without its country gets the country of the same institution elsewhere in this data, when at least 2 and 2/3 of that
     institution's addresses name the same country (switch off with --no-country-fallback); the table used is written to institution_countries.csv
  8. Corresponding Country (from Correspondence Address, with the same fallback)
  9. Source title: remove "(Switzerland)", trim
  C. checks: unique EID and title, no missing EID / Authors / Title / Year, plausible years, Cited by >= 0, Countries agree with Country Count

A column that is not in the export is skipped together with what is derived from it (the export may have been made with fewer fields).
"""
import argparse
import html
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

for _c in (Path(__file__).resolve().parent / "common", Path(__file__).resolve().parent.parent / "common"):      # shared name rules (countries, institutions): in the application, or in the project
    sys.path.insert(0, str(_c))
from names import country_of_affiliation, country_with_fallback, learn_institution_countries

# columns the study keeps (the notes drop seven columns that are empty or not needed); only those present in the export are used
KEEP = ["Authors", "Author full names", "Author(s) ID", "Title", "Year", "Source title", "Volume", "Issue", "Art. No.", "Page start", "Page end", "Cited by", "DOI",
        "Link", "Affiliations", "Authors with affiliations", "Abstract", "Author Keywords", "Index Keywords", "Funding Details", "Funding Texts", "References",
        "Correspondence Address", "Editors", "Publisher", "Sponsors", "Conference name", "Conference date", "Conference location", "ISSN", "ISBN", "PubMed ID",
        "Language of Original Document", "Abbreviated Source Title", "Document Type", "Open Access", "Source", "EID",
        "Query_IDs", "N_Queries"]          # the two columns added by the merge of the search exports: which search returned the paper
EXCLUDE_ONLY = []                            # set from --exclude-only-queries
COUNTRY_FALLBACK = True                      # off with --no-country-fallback
REQUIRED = ["EID", "Title", "Authors", "Year"]
lines = []                                   # everything printed is also written to clean_report.txt


def say(text=""):
    print(text)
    lines.append(text)


def step(name, df):
    say(f"{name:<62} {len(df):>6} rows")


MOJI = re.compile(r"[\u00c2-\u00c5\u00e2]")        # Â Ã Ä Å â: the lead characters of broken accents and quotation marks (not "×", which is a real character)
def fix_mojibake(s):
    """repair sequences such as 'Ã¤' or 'â\\x80\\x93': one UTF-8 character (2-4 bytes) shown as 2-4 Latin-1/Windows-1252 characters.
    A run is replaced only when it decodes as valid UTF-8; text whose bytes were already lost in the export is left as it is."""
    out, i = [], 0
    while i < len(s):
        if MOJI.match(s[i]):
            for n in (4, 3, 2):                          # longest sequence first
                chunk = s[i:i + n]
                for enc in ("cp1252", "latin-1"):
                    try:
                        out.append(chunk.encode(enc).decode("utf-8"))
                        i += n
                        break
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        continue
                else:
                    continue
                break
            else:
                out.append(s[i])
                i += 1
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def text_clean(s):
    """mojibake repaired, control characters out, HTML entities decoded, spaces trimmed (a missing value stays missing)"""
    if not isinstance(s, str):
        return None
    s = fix_mojibake(s)
    s = "".join(ch for ch in s if not (ord(ch) < 32 or 127 <= ord(ch) < 160))
    return html.unescape(s).strip() or None


def clean(src, out):
    raw = pd.read_csv(src, dtype=object, keep_default_na=False, na_values=[""], encoding="utf-8-sig")
    step("read the export", raw)
    absent = [c for c in REQUIRED if c not in raw.columns]
    if absent:
        sys.exit("This does not look like a Scopus export, columns missing: " + ", ".join(absent))

    # A. text hygiene
    changed = {}
    for c in raw.columns:
        new = raw[c].map(text_clean)
        changed[c] = int(((raw[c] != new) & ~(raw[c].isna() & new.isna())).sum())
        raw[c] = new
    say("A. cells changed by the text hygiene: " + str({c: n for c, n in changed.items() if n}))

    # 1. valid EID, one row per EID
    d = raw[raw["EID"].fillna("").str.startswith("2-s2.0-")].drop_duplicates("EID")
    step("1. valid EID, duplicates of EID removed", d)
    keep = [c for c in KEEP if c in d.columns]
    d = d[keep].copy()
    has = lambda c: c in d.columns

    # 2. reference count
    if has("References"):
        d["Reference Count"] = d["References"].map(lambda r: 0 if pd.isna(r) else len(r.split("); ")))
        d = d.drop(columns=["References"])
    d["Year"] = pd.to_numeric(d["Year"], errors="coerce")
    d = d[d["Year"].notna()].copy()
    d["Year"] = d["Year"].astype(int)
    if has("Cited by"):
        d["Cited by"] = pd.to_numeric(d["Cited by"], errors="coerce").fillna(0).astype(int)

    # 3. no authors
    d = d[d["Authors"].notna()].copy()
    step("3. records without authors removed", d)

    # 3b. papers returned ONLY by the searches named in --exclude-only-queries (a search known to be noise, e.g. Q3) are removed
    if EXCLUDE_ONLY and has("Query_IDs"):
        d = d[~d["Query_IDs"].fillna("").map(lambda q: set(q.split(";")) <= set(EXCLUDE_ONLY))].copy()
        step(f"3b. papers found only by {','.join(EXCLUDE_ONLY)} removed", d)

    # 4. duplicate papers (same title key); the earliest year and the most cited one is kept
    d["Title Key"] = d["Title"].map(lambda t: None if pd.isna(t) else re.sub(r"[^a-z0-9]", "", t.lower()))
    d = d.sort_values(["Year"] + (["Cited by"] if has("Cited by") else []), ascending=[True, False][: 2 if has("Cited by") else 1], kind="stable").drop_duplicates("Title Key")
    step("4. duplicate papers (same title) removed", d)
    d = d.drop(columns=["Title Key"]).reset_index(drop=True)

    # 4b. duplicate papers (same DOI, e.g. a conference paper indexed twice, once with "... Demonstration Track" added to its title); same order as in 4
    if has("DOI"):
        doi = d["DOI"].str.strip().str.lower()
        d = d[doi.isna() | ~doi.duplicated()].reset_index(drop=True)
        step("4b. duplicate papers (same DOI) removed", d)

    # 5. keywords
    for c in ["Author Keywords", "Index Keywords"]:
        if has(c):
            d[c] = d[c].map(lambda v: None if pd.isna(v) else v.lower().replace("-", " ").replace("_", " ").strip())

    # 6. affiliations and correspondence address
    for c in ["Affiliations", "Authors with affiliations", "Correspondence Address"]:
        if has(c):
            d[c] = d[c].map(lambda v: None if pd.isna(v) else v.replace("& amp;", "&").replace("Türkiye", "Turkey").replace("Viet Nam", "Vietnam"))
    for c in ["Affiliations", "Authors with affiliations"]:
        if has(c):
            d[c] = d[c].map(lambda v: None if pd.isna(v) else v.replace("UPMC Univ. Paris 06;", "UPMC Univ. Paris 06, France;"))

    # 7. countries
    learned, filled = {}, []
    if has("Affiliations") and COUNTRY_FALLBACK:
        parts = [x for a in d["Affiliations"].dropna() for x in a.split("; ")]
        learned = learn_institution_countries(parts)
    if has("Affiliations"):
        def countries(a):
            if pd.isna(a):
                return None
            found = []
            for part in a.split("; "):                       # one affiliation; its country must be a known country name (common/names.py)
                c, how = country_with_fallback(part, learned)
                if how == "institution":
                    filled.append(part)
                if c and c not in found:
                    found.append(c)
            return "; ".join(found) or None
        d["Countries"] = d["Affiliations"].map(countries)
        d["Country Count"] = d["Countries"].map(lambda c: None if pd.isna(c) else len(c.split("; ")))
        d["Collaboration Type"] = d["Country Count"].map(lambda n: None if pd.isna(n) else ("SCP" if n == 1 else "MCP"))

    # 8. corresponding country
    if has("Correspondence Address"):
        def corr(a):
            if pd.isna(a):
                return None
            p = a.split("; ")
            return None if len(p) < 2 or p[1].startswith("email:") else country_with_fallback(p[1], learned)[0]
        d["Corresponding Country"] = d["Correspondence Address"].map(corr)

    # 9. source title
    if has("Source title"):
        d["Source title"] = d["Source title"].map(lambda s: None if pd.isna(s) else (s.replace("(Switzerland)", "").strip() or None))

    order = [c for c in KEEP if c in d.columns] + [c for c in ["Reference Count", "Countries", "Corresponding Country", "Country Count", "Collaboration Type"] if c in d.columns]
    d = d[order]
    if has("Country Count"):
        d["Country Count"] = d["Country Count"].astype("Int64")

    # C. integrity checks
    say("")
    say("C. checks")
    problems = []

    def check(ok, msg):
        say(("  ok    " if ok else "  FAIL  ") + msg)
        if not ok:
            problems.append(msg)
    check(d["EID"].is_unique and d["EID"].notna().all(), "EID unique and never missing")
    check(d["Title"].notna().all() and d["Authors"].notna().all(), "Title and Authors never missing")
    check(d["Year"].between(1900, date.today().year + 1).all(), f"all years plausible ({d['Year'].min()} to {d['Year'].max()})")
    if has("Cited by"):
        check((d["Cited by"] >= 0).all(), "Cited by is a whole number >= 0")
    if has("DOI"):
        check(d["DOI"].dropna().is_unique, "no DOI appears twice")
    if has("Countries"):
        both = d["Countries"].notna()
        check((d.loc[both, "Countries"].map(lambda c: len(c.split("; "))) == d.loc[both, "Country Count"]).all(), "Country Count equals the number of countries listed")
        check(set(d["Collaboration Type"].dropna()) <= {"SCP", "MCP"}, "Collaboration Type is SCP or MCP")
    bad = d.apply(lambda col: col.map(lambda v: isinstance(v, str) and v != v.strip())).sum()
    check(bad.sum() == 0, "no text cell starts or ends with a space" + ("" if bad.sum() == 0 else f"  {bad[bad > 0].to_dict()}"))
    if problems:
        sys.exit("cleaning stopped: " + "; ".join(problems))

    # reported, not changed (real gaps of the export)
    say("")
    say("reported, not changed")
    if has("Author full names") and has("Author(s) ID"):
        n_names = d["Author full names"].map(lambda x: 0 if pd.isna(x) else len(x.split("; ")))
        n_ids = d["Author(s) ID"].map(lambda x: len(str(x).rstrip(";").split(";")) if isinstance(x, str) else 0)
        say(f"  papers whose number of author names and author IDs differ: {int((n_names != n_ids).sum())}")
    miss = {c: int(d[c].isna().sum()) for c in ["Source title", "Affiliations", "Correspondence Address", "DOI", "Author Keywords"] if has(c)}
    say("  missing values: " + str({c: n for c, n in miss.items() if n}))
    damaged = re.compile(r"Ã|â€|â\x80")
    left = {c: int(d[c].map(lambda v: isinstance(v, str) and bool(damaged.search(v))).sum()) for c in d.columns}
    say("  cells with characters already damaged in the export (cannot be repaired, left as they are): " + str({c: n for c, n in left.items() if n}))
    say("  papers per year: " + str(d["Year"].value_counts().sort_index().to_dict()))
    if has("Reference Count"):
        say(f"  references per paper: at most {int(d['Reference Count'].max())}")

    if has("Affiliations"):
        if COUNTRY_FALLBACK:
            say(f"  addresses without a country that got one from the same institution elsewhere in the data: {len(filled)} "
                f"({len(set(filled))} different; {len(learned)} institutions have a known country, see institution_countries.csv)")
        else:
            say("  a missing country is NOT taken from the same institution elsewhere (switched off)")

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    table = out.parent / "institution_countries.csv"
    if learned:
        pd.DataFrame([(name, key, c, n) for key, (c, name, n) in sorted(learned.items(), key=lambda kv: kv[1][1].lower())],
                     columns=["Institution", "Key", "Country", "Addresses naming it"]).to_csv(table, index=False, encoding="utf-8-sig")
    elif table.exists():
        table.unlink()                                       # switched off: an old table must not be used by the Affiliations sheet
    d.to_csv(out, index=False, encoding="utf-8-sig")
    say("")
    say(f"written {out.name}: {len(d)} papers, {d.shape[1]} columns")
    (out.parent / "clean_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Clean a Scopus CSV export.")
    ap.add_argument("--input", required=True, help="the Scopus CSV export")
    ap.add_argument("--output", required=True, help="the cleaned CSV to write")
    ap.add_argument("--exclude-only-queries", default="", help="comma list of search IDs, e.g. Q3: papers returned only by these searches are dropped (needs Query_IDs)")
    ap.add_argument("--no-country-fallback", action="store_true", help="do not give an address without a country the country of the same institution elsewhere in the data")
    a = ap.parse_args()
    EXCLUDE_ONLY = [q.strip() for q in a.exclude_only_queries.split(",") if q.strip()]
    COUNTRY_FALLBACK = not a.no_country_fallback
    clean(a.input, a.output)
