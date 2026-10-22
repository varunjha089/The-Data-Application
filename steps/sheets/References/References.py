"""Sheet "References" (query References): one row per paper and cited reference.
Excel: read the raw Scopus CSV; keep References and EID; inner join with Clean_Main_Data on EID (only papers that survived the cleaning) and take its Year; drop papers
without references; remove quotation marks; split at "); " into rows; clean and trim each; make sure each reference ends with ")"; one row per (EID, reference).
The raw CSV is used because the cleaning step drops the long References column; the same text hygiene as in the cleaning step is applied to it.
Input : the raw Scopus CSV (option --raw FILE; default WM_RS/2.1. Master Data Time Frame_WM_RS_Sciento.csv) and 01_Clean_Data/clean_main_data.csv        Output: References.csv
Note  : the January export keeps at most 10 references per paper, so this table is much smaller than one from a full export.
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

_ap = argparse.ArgumentParser(description="Sheet References")
_ap.add_argument("--raw", help="the raw Scopus CSV (default: WM_RS/2.1. Master Data Time Frame_WM_RS_Sciento.csv next to the folder that holds this one)")
_args = _ap.parse_args()
RAW = Path(_args.raw) if _args.raw else SHEETS.parent / "WM_RS" / "2.1. Master Data Time Frame_WM_RS_Sciento.csv"
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


raw = pd.read_csv(RAW, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=object, usecols=["EID", "References"])
raw["EID"] = raw["EID"].map(text_clean)
raw["References"] = raw["References"].map(text_clean)
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
