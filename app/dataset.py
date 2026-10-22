"""The main data of a project: a Scopus CSV export. The file is COPIED into the project (data/raw/); the original is never touched."""
import csv
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

REQUIRED_COLUMNS = ["EID", "Title", "Authors", "Year"]


def validate(path):
    """(ok, message, n_rows): is it a Scopus CSV with the columns the cleaning needs?"""
    path = Path(path)
    if not path.is_file():
        return False, "file not found: " + str(path), 0
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            header = next(rd, [])
            n = sum(1 for _ in rd)
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        return False, f"cannot read it as a CSV file ({e})", 0
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        return False, "not a Scopus export: these columns are missing: " + ", ".join(missing), n
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
