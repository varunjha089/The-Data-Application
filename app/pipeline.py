"""The steps of the analysis as functions that the window AND the terminal commands both call.
Every step writes its results and a LOG of the run into its own folder inside the project (01_Clean_Data/ for step 1), so that what was done can be written about later."""
import hashlib
import shutil
import subprocess
import time
from datetime import datetime

from . import envsetup, runner
from .jobs import stream
from .paths import STEPS

CLEAN_SCRIPT = "01_clean_data.py"


def _versions(py):
    r = subprocess.run([str(py), "-c", "import sys, pandas; print('Python', sys.version.split()[0] + ', pandas', pandas.__version__)"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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
    cmd = runner.step_command(py, CLEAN_SCRIPT, ["--input", src, "--output", project.clean_file])
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
    both("$ " + " ".join([project.rel(py), "steps/" + CLEAN_SCRIPT, "--input", project.rel(src), "--output", project.rel(project.clean_file)]))
    ok = stream(cmd, both, echo=False) == 0
    if ok:
        project.update(clean_data={"file": project.rel(project.clean_file), "source": (project.load().get("main_data") or {}).get("file"),
                                   "made": started.strftime("%Y-%m-%dT%H:%M:%S")})
        shutil.copy2(STEPS / CLEAN_SCRIPT, project.clean / CLEAN_SCRIPT)      # the exact script that made this result
    info = project.load().get("main_data") or {}
    head = ["The Data Application: step 1, clean the data",
            f"Project : {project.name}",
            f"Run     : {started.strftime('%Y-%m-%d %H:%M:%S')} (took {time.time() - t0:.0f} s)",
            f"Result  : {'finished' if ok else 'STOPPED WITH AN ERROR, nothing was written'}",
            f"Input   : {project.rel(src)}  ({info.get('records', '?')} records, SHA-256 {info.get('sha256', '?')[:16]}...)",
            f"Output  : {project.rel(project.clean_file)}" + (f"  (SHA-256 {_sha(project.clean_file)[:16]}...)" if ok and project.clean_file.exists() else ""),
            f"Software: {_versions(py)}",
            "-" * 78]
    project.clean_log.write_text("\n".join(head + lines) + "\n", encoding="utf-8")
    return ok, ("The data is cleaned. Results and the log are in 01_Clean_Data." if ok else "The cleaning stopped with an error (see the log).")


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


def _run_script(project, name, script, args, title, log, log_name):
    """copy steps/sheets/<name>/<script> into <project>/<name>/ and run it there with the project's python; the run is logged to <project>/<name>/<log_name>"""
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
    both("$ " + " ".join([project.rel(py), f"{name}/{script}"] + [project.rel(a) if str(a).startswith("/") or ":" in str(a)[:3] else str(a) for a in args]))
    ok = stream([py, script] + [str(a) for a in args], both, echo=False, cwd=folder) == 0
    head = [f"The Data Application: {title}", f"Project : {project.name}", f"Run     : {started.strftime('%Y-%m-%d %H:%M:%S')} (took {time.time() - t0:.0f} s)",
            f"Result  : {'finished' if ok else 'STOPPED WITH AN ERROR'}", f"Script  : {name}/{script}", f"Software: {_versions(py)}", "-" * 78]
    (folder / log_name).write_text("\n".join(head + lines) + "\n", encoding="utf-8")
    return ok, "Done." if ok else "The script stopped with an error (see the log)."


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
    args = sheetlist.option_args(project, name) if sheetlist.BY_NAME[name]["options"] else []
    if name == "References":
        raw = project.main_data()
        if raw is None:
            return False, "No main data chosen yet (Settings)."
        args = ["--raw", raw]
    log(f"=== {name}")
    ok, msg = _run_script(project, name, f"{name}.py", args, f"sheet {name}", log, f"{name}_log.txt")
    return (ok, f"{spec['title']}: data generated." if ok else msg)


def run_plot(project, name, plot_id, log):
    """Generate one plot of a sheet (the sheet's data first when it is missing). Returns (ok, message)."""
    spec = sheetlist.get(name)
    if spec is None or not any(p["id"] == plot_id for p in spec["plots"]):
        return False, "Unknown plot."
    if spec["options"] or not sheet_csv(project, name).exists():       # a sheet with options: its data is made again, so the plot follows the saved options
        ok, msg = run_sheet(project, name, log)
        if not ok:
            return False, msg
    log(f"=== plot of {name}")
    ok, msg = _run_script(project, name, f"{name}_plot.py", ["--only", plot_id] if spec.get("per_plot") else [], f"plot of sheet {name}", log, f"{name}_plot_log.txt")
    return (ok, f"{spec['title']}: plot generated." if ok else msg)


def run_all(project, log, plots=False):
    """Generate every sheet (or, with plots=True, every plot of every sheet). Stops at the first error."""
    done = 0
    for spec in sheetlist.SHEETS:
        if plots:
            if spec["plots"]:
                ok, msg = run_plot(project, spec["name"], spec["plots"][0]["id"], log)
                done += ok
            else:
                continue
        else:
            ok, msg = run_sheet(project, spec["name"], log)
            done += ok
        if not ok:
            return False, f"Stopped at {spec['name']}: {msg}"
    return True, f"{done} {'plots' if plots else 'sheets'} generated."
