"""Sheet "References" (query References): one row per paper and cited reference.
Excel: read the raw Scopus CSV; keep References and EID; inner join with Clean_Main_Data on EID (only papers that survived the cleaning) and take its Year; drop papers
without references; remove quotation marks; split at "); " into rows; clean and trim each; make sure each reference ends with ")"; one row per (EID, reference).
The raw CSV is used because the cleaning step drops the long References column; the same text hygiene as in the cleaning step is applied to it.
Input : the raw Scopus CSV (option --raw FILE [FILE ...]; default: every CSV in the project's data/raw/, where the application keeps its copy) and 01_Clean_Data/clean_main_data.csv        Output: References.csv
        Several raw files may be given; per paper (EID) the longest References text is used. A file without a References column is ignored.
        If NO given file has a References column (the export was made without the References option) the sheet is SKIPPED with a message, not
        built from nothing: no References.csv is written and the script ends normally, like the cleaning step does for a missing column.
Note  : some exports keep only the first references of each paper; the table is then smaller than the papers' real reference lists.
Run   : python3 References.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "References.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


import html
import re

import argparse
import sys

_ap = argparse.ArgumentParser(description="Sheet References")
_ap.add_argument("--raw", nargs="+", help="one or more raw Scopus CSVs that contain a References column (default: every CSV in data/raw/ of the project)")
_args = _ap.parse_args()
RAWS = [Path(x) for x in _args.raw] if _args.raw else sorted((SHEETS / "data" / "raw").glob("*.csv"))
MOJI = re.compile(r"[\u00c2-\u00c5\u00e2]")        # Â Ã Ä Å â: the lead characters of broken accents and quotation marks (not "×", which is a real character)
def fix_mojibake(s):
    """repair UTF-8 text that was read as Windows-1252 ('Ã¤' -> 'ä'); only runs that decode as valid UTF-8 are replaced"""
    out, i = [], 0
    while i < len(s):
        if MOJI.match(s[i]):
            for n in (4, 3, 2):
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
    if not isinstance(s, str):
        return None
    s = fix_mojibake(s)
    s = "".join(ch for ch in s if not (ord(ch) < 32 or 127 <= ord(ch) < 160))
    return html.unescape(s).strip() or None


frames = []
for f in RAWS:
    cols = list(pd.read_csv(f, encoding="utf-8-sig", nrows=0).columns)
    if "EID" in cols and "References" in cols:
        frames.append(pd.read_csv(f, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=object, usecols=["EID", "References"]))
    else:
        print(f"note: {f.name} has {len(cols)} columns but no {'References' if 'EID' in cols else 'EID'} column, so it is not used")
if not frames:
    print("SKIPPED: none of the raw files has a References column, so the References sheet was not built and no References.csv was written.")
    print("         The Scopus export was made without the References option. Re-export the papers from Scopus with References ticked")
    print("         (it is a separate option in the export dialog, not part of 'Bibliographical information') and run this sheet again with --raw <that file>.")
    sys.exit(0)
raw = pd.concat(frames, ignore_index=True)
raw["EID"] = raw["EID"].map(text_clean)
raw["References"] = raw["References"].map(text_clean)
raw = raw.dropna(subset=["EID"]).assign(_n=lambda d: d["References"].fillna("").str.len()).sort_values("_n", ascending=False).drop_duplicates("EID").drop(columns="_n")
clean = read_csv(CLEAN)[["EID", "Year"]]
m = raw.merge(clean, on="EID", how="inner").dropna(subset=["References"])
rows = []
for eid, refs, year in zip(m["EID"], m["References"], m["Year"]):
    for r in refs.replace('"', "").split("); "):
        r = text_clean(r)
        if r:
            rows.append((eid, year, r if r.endswith(")") else r + ")"))
references = pd.DataFrame(rows, columns=["EID", "Year", "Reference"]).drop_duplicates(["EID", "Reference"]).reset_index(drop=True)
print(f"{m['EID'].nunique()} papers with references -> {len(references)} references")
write(references)
