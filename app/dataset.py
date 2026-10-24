"""The main data of a project: a Scopus CSV export. The file is COPIED into the project (data/raw/); the original is never touched."""
import csv
import hashlib
import shutil
import sys
from datetime import datetime
from pathlib import Path

REQUIRED_COLUMNS = ["EID", "Title", "Authors", "Year"]


def allow_long_fields():
    """Python's csv module refuses any cell longer than 131072 characters. A Scopus export made with the References option has such cells
    (one paper alone can cite thousands of works), so the limit is raised to the largest value this system accepts (sys.maxsize overflows on
    Windows, hence the loop). The setting is global to the csv module, so importing this module is enough for the whole application."""
    n = sys.maxsize
    while True:
        try:
            csv.field_size_limit(n)
            return
        except OverflowError:
            n //= 10


allow_long_fields()


SCOPUS_HELP = ("In Scopus: select the papers, Export, CSV, tick all information fields (and References for the reference sheets), and use that file as it is. "
               "Do not open and save it in Excel first: Excel can change the separator and the characters.")


def _sniff(head):
    """what kind of file the first bytes say it is, when it is clearly not a CSV export (None otherwise)"""
    if head.startswith(b"PK\x03\x04"):
        return "an Excel workbook (.xlsx), not a CSV file. In Excel use Save As, 'CSV UTF-8 (Comma delimited)', or better export the CSV from Scopus again"
    if head.startswith(b"%PDF"):
        return "a PDF file, not a CSV export"
    text = head.lstrip(b"\xef\xbb\xbf").lstrip()
    if text.startswith((b"FN ", b"PT ", b"VR ")):
        return "a Web of Science export; only Scopus CSV exports are supported"
    if text.startswith(b"TY  -"):
        return "an RIS file; export the papers from Scopus as CSV instead"
    if text.startswith(b"@"):
        return "a BibTeX file; export the papers from Scopus as CSV instead"
    return None


def validate(path):
    """(ok, message, n_rows): is it a Scopus CSV with the columns the cleaning needs? The message says in plain words what is wrong and what to do."""
    path = Path(path)
    if not path.is_file():
        return False, "file not found: " + str(path), 0
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
    except OSError as e:
        return False, f"the file cannot be opened ({e})", 0
    what = _sniff(head)
    if what:
        return False, "This is " + what + ".", 0
    if not head.strip():
        return False, "The file is empty.", 0
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            header = next(rd, [])
            n = sum(1 for _ in rd)
    except UnicodeDecodeError:
        return False, ("The file is not UTF-8 text (it was probably saved by Excel in another character set, so accents would be lost). " + SCOPUS_HELP), 0
    except (OSError, csv.Error) as e:
        return False, f"The file cannot be read as a CSV file ({e}). " + SCOPUS_HELP, 0
    if len(header) == 1 and (";" in header[0] or "\t" in header[0]):
        sep = "semicolons" if ";" in header[0] else "tabs"
        return False, f"The columns are separated by {sep}, not commas (Excel does this in some languages). " + SCOPUS_HELP, 0
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        near = [h for h in header if h.strip().lower() in {m.lower() for m in missing}]
        extra = f" (found {', '.join(repr(h) for h in near)}: the names must be written exactly as Scopus writes them)" if near else ""
        return False, ("This is not a Scopus export: the columns " + ", ".join(missing) + f" are missing{extra}. The file has {len(header)} columns, "
                       f"starting with {', '.join(header[:4]) or 'nothing'}. " + SCOPUS_HELP), n
    if n == 0:
        return False, "The file has the Scopus columns but no papers.", 0
    return True, f"{n} records, {len(header)} columns", n


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def register(project, dst, original, records):
    """remember a copy that is already in the project's data/raw/; a new main file makes the old cleaned data out of date"""
    project.update(main_data={"file": project.rel(dst), "original_path": str(original), "records": records, "sha256": sha256(dst),
                              "copied": datetime.now().isoformat(timespec="seconds")}, clean_data=None)


def import_file(project, src):
    """copy src into the project and remember it; returns (ok, message)"""
    src = Path(src).expanduser().resolve()
    ok, msg, n = validate(src)
    if not ok:
        return False, msg
    project.raw.mkdir(parents=True, exist_ok=True)
    dst = project.raw / src.name
    if dst.resolve() != src:
        shutil.copy2(src, dst)
    register(project, dst, src, n)
    return True, f"copied to {project.rel(dst)} ({msg})"
