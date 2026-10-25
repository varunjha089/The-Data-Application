"""The steps of the analysis as functions that the window AND the terminal commands both call.
Every step writes its results and a LOG of the run into its own folder inside the project (01_Clean_Data/ for step 1), so that what was done can be written about later."""
import hashlib
import json
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from . import __version__, envsetup, look, runner, years
from .jobs import stream
from .paths import STEPS

CLEAN_SCRIPT = "01_clean_data.py"


def _versions(py):
    r = subprocess.run([str(py), "-c", "import sys, pandas; print('Python', sys.version.split()[0] + ', pandas', pandas.__version__)"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


_sha_cache = {}


def _sha(path):
    """SHA-256 of a file (remembered while the file is unchanged: the cleaned data is hashed once, not for every sheet)"""
    st = Path(path).stat()
    key = (str(path), st.st_mtime, st.st_size)
    if key not in _sha_cache:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _sha_cache[key] = h.hexdigest()
    return _sha_cache[key]


# what a failed script means, in plain words (the full traceback stays in the log)
_HINTS = [
    (r"KeyError: '([^']+)'", "The column or item '{0}' is missing. If it is a Scopus column, export the data again from Scopus with all information fields ticked "
                             "(citation, bibliographical, abstract and keywords, funding, other information, and References when you need them)."),
    (r"No module named '([^']+)'", "The package '{0}' is not installed in the project's Python: Settings, Install the missing packages."),
    (r"FileNotFoundError: .*'([^']+)'", "The file {0} is missing: generate the sheets this one needs first (Overview, Generate all data)."),
    (r"PermissionError: .*'([^']+)'", "{0} cannot be written: is it open in Excel or another program? Close it and try again."),
    (r"UnicodeDecodeError", "A file is not UTF-8 text. Export the data from Scopus again as CSV (do not open and save it in Excel first)."),
    (r"MemoryError", "The computer ran out of memory: close other programs, or use a smaller export."),
]


def explain_failure(lines):
    """the last error line of a script's output and, when it is a known one, what to do about it"""
    text = [str(x).strip() for x in lines if str(x).strip() and not str(x).startswith("$ ")]
    if not text:
        return "The script stopped without a message."
    last = text[-1]
    for pattern, hint in _HINTS:
        m = re.search(pattern, last)
        if m:
            return f"{last}. {hint.format(*(Path(g).name for g in m.groups()))}"
    return last if len(last) < 300 else last[:297] + "..."


def write_run_info(folder, section, info):
    """<folder>/run_info.json: what made the files of this folder (application version, script and its SHA-256, arguments, input SHA-256, settings, software),
    one entry per data run and per plot, so that every figure can be traced and made again"""
    f = Path(folder) / "run_info.json"
    try:
        cur = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except ValueError:
        cur = {}
    cur["application"] = f"The Data Application {__version__}"
    keys = section.split("/")
    node = cur
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = info
    f.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _inputs(project, files):
    out = []
    for p in files:
        p = Path(p)
        if p.exists():
            out.append({"file": project.rel(p), "sha256": _sha(p)})
    return out


def clean_country_fallback(project):
    """fill in a missing country from the same institution elsewhere in the data (a setting of the project; on unless switched off)"""
    return (project.load().get("clean_options") or {}).get("country_fallback", True) is not False


def clean_exclude(project):
    """the search IDs whose papers are dropped when no other search found them (a setting of the project; empty = keep everything)"""
    return ",".join(q for q in re.split(r"[,;\s]+", (project.load().get("clean_options") or {}).get("exclude_only_queries") or "") if q)


def copy_common(project):
    """steps/common/*.py (the shared name rules) next to the results, so that the scripts of the project run on their own"""
    dest = project.dir / "common"
    dest.mkdir(parents=True, exist_ok=True)
    for f in (STEPS / "common").glob("*.py"):
        shutil.copy2(f, dest / f.name)


def ensure_packages(py, log):
    """make sure the packages the scripts import are in the project's environment; missing ones are downloaded (pip) now"""
    if not envsetup.missing_packages(py):
        return True
    return envsetup.install_missing(py, log)


def clean_data(project, log):
    """Step 1: run steps/01_clean_data.py on the project's main data. `log(text)` receives every line (the window shows it, the terminal prints it).
    Writes <project>/01_Clean_Data/{clean_main_data.csv, clean_report.txt, clean_log.txt, 01_clean_data.py}. Returns (ok, message)."""
    src = project.main_data()
    if src is None:
        return False, "No main data chosen yet (Settings)."
    py = project.python()
    only = clean_exclude(project)                                # e.g. "Q3": papers found only by a noise search are dropped
    fallback = clean_country_fallback(project)
    extra = (["--exclude-only-queries", only] if only else []) + ([] if fallback else ["--no-country-fallback"])
    cmd = runner.step_command(py, CLEAN_SCRIPT, ["--input", src, "--output", project.clean_file] + extra)
    if cmd is None:
        return False, "The Python environment is not set up yet (Settings)."
    if not ensure_packages(py, log):
        return False, "The missing packages could not be installed (internet connection? see Settings)."
    lines = []

    def both(text):
        lines.append(str(text))
        log(text)
    started = datetime.now()
    t0 = time.time()
    project.clean.mkdir(parents=True, exist_ok=True)
    both("$ " + " ".join([project.rel(py), "steps/" + CLEAN_SCRIPT, "--input", project.rel(src), "--output", project.rel(project.clean_file)] + extra))
    ok = stream(cmd, both, echo=False) == 0
    if ok:
        project.update(clean_data={"file": project.rel(project.clean_file), "source": (project.load().get("main_data") or {}).get("file"),
                                   "made": started.strftime("%Y-%m-%dT%H:%M:%S"), "exclude": only, "country_fallback": fallback})
        shutil.copy2(STEPS / CLEAN_SCRIPT, project.clean / CLEAN_SCRIPT)      # the exact script that made this result
        copy_common(project)
    info = project.load().get("main_data") or {}
    versions = _versions(py)
    reason = "" if ok else explain_failure(lines)
    write_run_info(project.clean, "clean", {"when": started.isoformat(timespec="seconds"), "seconds": round(time.time() - t0, 1), "ok": ok,
                                            "script": CLEAN_SCRIPT, "script_sha256": _sha(STEPS / CLEAN_SCRIPT),
                                            "arguments": ["--input", project.rel(src), "--output", project.rel(project.clean_file)] + extra,
                                            "inputs": _inputs(project, [src]), "outputs": _inputs(project, [project.clean_file]) if ok else [],
                                            "settings": {"exclude_only_queries": only, "country_fallback": fallback}, "software": versions, "error": reason or None})
    head = ["The Data Application: step 1, clean the data",
            f"Project : {project.name}",
            f"Run     : {started.strftime('%Y-%m-%d %H:%M:%S')} (took {time.time() - t0:.0f} s)",
            f"Result  : {'finished' if ok else 'STOPPED WITH AN ERROR, nothing was written'}",
            f"Input   : {project.rel(src)}  ({info.get('records', '?')} records, SHA-256 {info.get('sha256', '?')[:16]}...)",
            f"Output  : {project.rel(project.clean_file)}" + (f"  (SHA-256 {_sha(project.clean_file)[:16]}...)" if ok and project.clean_file.exists() else ""),
            f"Software: {versions} (The Data Application {__version__})",
            "-" * 78]
    project.clean_log.write_text("\n".join(head + lines) + "\n", encoding="utf-8")
    return ok, ("The data is cleaned. Results and the log are in 01_Clean_Data." if ok else f"The cleaning stopped: {reason} The full details are in the log.")


# ---------------------------------------------------------------------------------------------------------------------------------- sheets and plots
from . import sheets as sheetlist  # noqa: E402


def sheet_csv(project, name, csv=None):
    return project.dir / name / (csv or f"{name}.csv")


def sheet_state(project, name):
    """done / made / stale for a sheet: stale = the cleaned data is newer than the sheet's CSV"""
    f = sheet_csv(project, name)
    if not f.exists():
        return {"done": False, "made": None, "stale": False}
    stale = project.clean_file.exists() and project.clean_file.stat().st_mtime > f.stat().st_mtime + 1
    return {"done": True, "made": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%S"), "stale": stale}


def _run_script(project, name, script, args, title, log, log_name, section, prefix=()):
    """copy steps/sheets/<name>/<script> into <project>/<name>/ and run it there with the project's python; the run is logged to <project>/<name>/<log_name>
    and described in <project>/<name>/run_info.json under `section`. `prefix` goes between python and the script (the plot-look wrapper)."""
    py = project.python()
    folder = project.dir / name
    src = STEPS / "sheets" / name / script
    if py is None or not py.exists():
        return False, "The Python environment is not set up yet (Settings)."
    if not src.exists():
        return False, f"The script {script} is missing in the application."
    if not ensure_packages(py, log):
        return False, "The missing packages could not be installed (internet connection? see Settings)."
    folder.mkdir(parents=True, exist_ok=True)
    copy_common(project)
    shutil.copy2(src, folder / script)
    for extra in (STEPS / "sheets" / name).iterdir():                 # files the script reads next to itself (e.g. the map polygons)
        if extra.suffix == ".json":
            shutil.copy2(extra, folder / extra.name)
    lines = []

    def both(text):
        lines.append(str(text))
        log(text)
    started = datetime.now()
    t0 = time.time()
    shown = [project.rel(a) if str(a).startswith("/") or ":" in str(a)[:3] else str(a) for a in list(prefix) + [script] + list(args)]
    both("$ " + " ".join([project.rel(py)] + [f"{name}/{script}" if a == script else a for a in shown]))
    ok = stream([py] + [str(a) for a in prefix] + [script] + [str(a) for a in args], both, echo=False, cwd=folder) == 0
    versions = _versions(py)
    reason = "" if ok else explain_failure(lines)
    head = [f"The Data Application {__version__}: {title}", f"Project : {project.name}", f"Run     : {started.strftime('%Y-%m-%d %H:%M:%S')} (took {time.time() - t0:.0f} s)",
            f"Result  : {'finished' if ok else 'STOPPED WITH AN ERROR: ' + reason}", f"Script  : {name}/{script}", f"Software: {versions}", "-" * 78]
    (folder / log_name).write_text("\n".join(head + lines) + "\n", encoding="utf-8")
    md = project.load().get("main_data") or {}
    inputs = [{"file": md.get("file"), "sha256": md.get("sha256"), "what": "main data (the Scopus export)"}] + _inputs(project, [project.clean_file])
    if section != "data":
        inputs += _inputs(project, sorted(folder.glob(f"{name}*.csv")))
    write_run_info(folder, section, {"when": started.isoformat(timespec="seconds"), "seconds": round(time.time() - t0, 1), "ok": ok, "script": script,
                                     "script_sha256": _sha(src), "command": " ".join(shown), "inputs": inputs,
                                     "options": sheetlist.option_values(project, name), "year_window": years.get(project),
                                     "plot_look": look.get(project) if section != "data" else None, "software": versions, "error": reason or None})
    return ok, "Done." if ok else f"The script stopped: {reason} The full details are in the log."


def _fresh_picture(csv_path):
    pic = csv_path.with_name(csv_path.stem + "_table.png")
    return pic.exists() and pic.stat().st_mtime >= csv_path.stat().st_mtime - 5


def make_table_pictures(project, name, log):
    """a PNG and an SVG of every table of the sheet (steps/common/table_image.py, run with the project's python); skipped, never fatal,
    when matplotlib is not installed yet. The rows drawn are a project setting (look.table_rows)."""
    py = project.python()
    if py is None or "matplotlib" in envsetup.missing_packages(py):
        log("(table pictures skipped: the package matplotlib is not installed yet; Settings, Install the missing packages)")
        return
    spec = sheetlist.get(name)
    rows = str(look.get(project)["table_rows"])
    for c in spec["csvs"]:
        path = sheet_csv(project, name, c)
        if not path.exists() or not c.endswith(".csv"):
            continue
        title = spec["title"] if c == spec["csvs"][0] else spec["title"] + ": " + c[:-4].split("_", 1)[-1].replace("_", " ")
        stream([py, project.dir / "common" / "table_image.py", path.name, "--rows", rows, "--title", title], log, echo=False, cwd=path.parent)


def run_sheet(project, name, log, _chain=()):
    """Generate the data of one sheet. A needed sheet that has not been generated yet is generated first. Returns (ok, message)."""
    spec = sheetlist.get(name)
    if spec is None:
        return False, f"Unknown sheet {name}."
    if not project.clean_file.exists():
        return False, "Clean the data first (step 1)."
    for need in spec["needs"]:
        if not sheet_csv(project, need).exists():
            log(f"--- {name} needs {need}: generating it first")
            ok, msg = run_sheet(project, need, log, _chain + (name,))
            if not ok:
                return False, f"{need} could not be generated: {msg}"
    args = sheetlist.option_args(project, name) if sheetlist.has_data_options(name) else []
    if name == "References":
        raw = project.main_data()
        if raw is None:
            return False, "No main data chosen yet (Settings)."
        args = ["--raw", raw]
    log(f"=== {name}")
    ok, msg = _run_script(project, name, f"{name}.py", args, f"sheet {name}", log, f"{name}_log.txt", "data")
    if ok:
        make_table_pictures(project, name, log)
    return (ok, f"{spec['title']}: data generated." if ok else msg)


def run_plot(project, name, plot_id, log):
    """Generate one plot of a sheet (the sheet's data first when it is missing). Returns (ok, message)."""
    spec = sheetlist.get(name)
    if spec is None or not any(p["id"] == plot_id for p in spec["plots"]):
        return False, "Unknown plot."
    if sheetlist.has_data_options(name) or not sheet_csv(project, name).exists():       # a sheet with options: its data is made again, so the plot follows the saved options
        ok, msg = run_sheet(project, name, log)
        if not ok:
            return False, msg
    log(f"=== plot of {name}")
    wrap = look.args(project)
    prefix = [project.dir / "common" / "plotlook.py"] + wrap if wrap else []
    ok, msg = _run_script(project, name, f"{name}_plot.py", (["--only", plot_id] if spec.get("per_plot") else []) + sheetlist.option_args(project, name, plot=True),
                          f"plot of sheet {name}", log, f"{name}_plot_log.txt", f"plots/{plot_id if spec.get('per_plot') else 'all'}", prefix)
    if ok:
        stale = [c for c in spec["csvs"] if c.endswith(".csv") and sheet_csv(project, name, c).exists()
                 and not _fresh_picture(sheet_csv(project, name, c))]
        if stale:                                      # the data was made before table pictures existed (or by hand): draw them now
            make_table_pictures(project, name, log)
    return (ok, f"{spec['title']}: plot generated." if ok else msg)


def run_all(project, log, plots=False):
    """Generate every sheet (or, with plots=True, every plot of every sheet). Stops at the first error."""
    done = 0
    for spec in sheetlist.SHEETS:
        if plots:
            if not spec["plots"]:
                continue
            for pl in (spec["plots"] if spec.get("per_plot") else spec["plots"][:1]):         # a script that makes one plot per call is called for each of its plots
                ok, msg = run_plot(project, spec["name"], pl["id"], log)
                done += ok
                if not ok:
                    break
        else:
            ok, msg = run_sheet(project, spec["name"], log)
            done += ok
        if not ok:
            return False, f"Stopped at {spec['name']}: {msg}"
    return True, f"{done} {'plots' if plots else 'sheets'} generated."
