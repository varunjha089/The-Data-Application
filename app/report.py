"""The Report page: which figures and tables go into the report, the LaTeX template, writing the results (steps/report/make_report.py, run with the
project's python like every sheet script) and building the PDF. Everything is written into <project>/Report/; the user's edits there are kept.
Standard library only."""
import glob
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from . import __version__, ai, config, pipeline, sheets as sheetlist
from .jobs import stream
from .paths import STEPS

FOLDER = "Report"
SRC = STEPS / "report"
OURS = {"make_report.py", "about.json", "report_items.json", "report_manifest.json", "report_status.json", "report_check.txt", "report_info.tex",
        "results_chapter.tex", "report_log.txt", "run_info.json", "results"}            # files of the application: a template never replaces them
NEEDED = ["graphicx", "float", "booktabs", "tabularx", "array"]
TOKENS_IN, TOKENS_IMAGE, TOKENS_OUT = 3000, 1600, 900      # rough size of one call, for the estimate shown before writing


def folder(pr):
    return pr.dir / FOLDER


def options(pr):
    o = dict(pr.load().get("report") or {})
    o.setdefault("study", "")
    o.setdefault("main", "report.tex")
    o.setdefault("template", "default")
    return o


def catalog(pr):
    """every figure and table a report can hold, in the order of the menu"""
    about = config.read_json(SRC / "about.json")
    out = []
    for s in sheetlist.SHEETS:
        base = {"sheet": s["name"], "group": s["group"], "sheet_title": s["title"], "what": s["what"], "csvs": [c for c in s["csvs"] if c.endswith(".csv")]}
        for p in s["plots"]:
            for f in p["files"]:
                a = about.get("plot:" + f) or {}
                out.append({**base, "stem": "fig_" + f, "kind": "fig", "file": f, "title": a.get("title") or p["title"],
                            "exists": (pr.dir / s["name"] / (f + ".png")).exists()})
        for c in s["csvs"]:
            a = about.get("table:" + c)
            if a:
                out.append({**base, "stem": "tab_" + c[:-4], "kind": "tab", "file": c, "title": a["title"], "exists": (pr.dir / s["name"] / c).exists()})
    return out


def _manifest(pr):
    return config.read_json(folder(pr) / "report_manifest.json")


def _sha(path):
    return pipeline._sha(path)


def state(pr):
    """everything the Report page shows; also unticks the items whose file the user deleted (they stay deleted)"""
    o, items, man = options(pr), catalog(pr), _manifest(pr)
    st = (config.read_json(folder(pr) / "report_status.json").get("items") or {})
    chosen = o.get("items")
    deleted = []
    for it in items:
        tex = folder(pr) / "results" / (it["stem"] + ".tex")
        m = man.get(it["stem"])
        if m and not tex.exists():
            it["file_state"], it["note"] = "deleted", "deleted by you"
            deleted.append(it["stem"])
        elif tex.exists() and (m is None or _sha(tex) != m.get("sha256")):
            it["file_state"], it["note"] = "edited", "edited by you (kept)"
        elif tex.exists():
            it["file_state"] = "written"
            it["note"] = "written without AI" if m.get("model") == "none" else "written by " + m.get("model", "").split(":", 1)[-1]
        else:
            it["file_state"], it["note"] = "new", "not written yet" if it["exists"] else "plot or table not generated yet"
        it["check"] = (m or {}).get("check", []) if tex.exists() else []
        it["failed"] = (st.get(it["stem"]) or {}).get("note") if (st.get(it["stem"]) or {}).get("state") == "failed" else None
    if chosen is None:                                       # first visit: everything that exists, except what was deleted
        chosen = [it["stem"] for it in items if it["exists"] and it["stem"] not in deleted]
    elif any(s in chosen for s in deleted):
        chosen = [s for s in chosen if s not in deleted]
        pr.update(report={**o, "items": chosen})
    for it in items:
        it["selected"] = it["stem"] in chosen
    s = ai.settings()
    k, where = ai.key(s["provider"])
    todo = [it for it in items if it["selected"] and it["exists"] and it["file_state"] != "edited"
            and not (it["file_state"] == "written" and (man.get(it["stem"]) or {}).get("model") == f"{s['provider']}:{ai.model()}")]
    images = s["images"] and any(it["kind"] == "fig" for it in todo)
    main = folder(pr) / o["main"]
    pdf = main.with_suffix(".pdf")
    return {"options": {k2: o[k2] for k2 in ("study", "main", "template")}, "items": items, "groups": sheetlist.GROUPS,
            "folder": str(folder(pr)), "exists": folder(pr).exists(), "main_exists": main.exists(),
            "pdf": pdf.exists(), "pdf_when": datetime.fromtimestamp(pdf.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%S") if pdf.exists() else None,
            "tex": bool(tex_tool("latexmk") or tex_tool("pdflatex")), "check_file": (folder(pr) / "report_check.txt").exists(),
            "ai": {"provider": s["provider"], "label": ai.PROVIDERS[s["provider"]]["label"], "model": ai.model(), "has_key": bool(k), "where": where, "images": s["images"]},
            "estimate": {"calls": len(todo), "tokens_in": len(todo) * TOKENS_IN + (TOKENS_IMAGE * sum(1 for it in todo if it["kind"] == "fig") if images else 0),
                         "tokens_out": len(todo) * TOKENS_OUT}}


def selected(pr):
    """the stems of the ticked figures and tables (before the first choice: everything that exists and was not deleted)"""
    chosen = options(pr).get("items")
    return set(chosen) if chosen is not None else {it["stem"] for it in state(pr)["items"] if it["selected"]}


def tick(pr, stem, on):
    """tick or untick one figure or table (from its sheet page); the order stays the order of the menu"""
    sel = selected(pr)
    sel = sel | {stem} if on else sel - {stem}
    save_options(pr, {"items": [it["stem"] for it in catalog(pr) if it["stem"] in sel]})
    return stem in sel


def save_options(pr, body):
    o = options(pr)
    if "items" in body:
        valid = {it["stem"] for it in catalog(pr)}
        o["items"] = [s for s in body["items"] if s in valid]
    if "study" in body:
        o["study"] = str(body["study"] or "")[:300]
    pr.update(report=o)
    return o


# ---------------------------------------------------------------- the folder and the template
def prepare(pr, log=lambda t: None):
    """<project>/Report with the application's script and texts (always the current ones) and, the first time, the default template"""
    f = folder(pr)
    f.mkdir(parents=True, exist_ok=True)
    for name in ("make_report.py", "about.json"):
        shutil.copy2(SRC / name, f / name)
    o = options(pr)
    if not (f / o["main"]).exists() and o["template"] == "default":
        shutil.copy2(SRC / "template" / "report.tex", f / "report.tex")
        pr.update(report={**o, "main": "report.tex"})
        log("The default template was copied: Report/report.tex (yours to edit).")


def _backup(f, names):
    """move the files a template would replace into Report/_backup_<time>/ (nothing of the user's is ever lost)"""
    names = [n for n in names if (f / n).exists()]
    if not names:
        return None
    b = f / ("_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    b.mkdir()
    for n in names:
        shutil.move(str(f / n), str(b / n))
    return b.name


def _main_tex(src):
    cands = [p for p in sorted(src.glob("*.tex")) if re.search(r"\\documentclass", p.read_text(encoding="utf-8", errors="replace"))
             and "\\begin{document}" in p.read_text(encoding="utf-8", errors="replace")]
    for pref in ("main.tex", "report.tex", "thesis.tex"):
        for p in cands:
            if p.name == pref:
                return p
    return cands[0] if cands else None


def patch_main(path):
    """make a template ready for the results: missing packages, \\input{results_chapter}, bibtex where biber cannot run; returns what changed"""
    text = path.read_text(encoding="utf-8", errors="replace")
    done = []
    missing = [p for p in NEEDED if not re.search(r"\\usepackage(\[[^\]]*\])?\{[^}]*\b" + p + r"\b", text)]
    if missing:
        add = "% added by The Data Application for the results chapter\n" + "".join(f"\\usepackage{{{p}}}\n" for p in missing)
        text = text.replace("\\begin{document}", add + "\\begin{document}", 1)
        done.append("added the packages " + ", ".join(missing))
    if not re.search(r"\\(input|include)\{results_chapter(\.tex)?\}", text):
        m = re.search(r"\\printbibliography|\\bibliography\{|\\end\{document\}", text)
        text = text[:m.start()] + "% the results chapter written by The Data Application (move this line where the results belong)\n\\input{results_chapter}\n" + text[m.start():]
        done.append("added \\input{results_chapter} before " + m.group(0).rstrip("{"))
    if re.search(r"backend\s*=\s*biber", text) and not biber_works():
        text = re.sub(r"backend\s*=\s*biber", "backend=bibtex", text)
        done.append("switched biblatex from biber to bibtex (biber does not run on this computer)")
    path.write_text(text, encoding="utf-8")
    return done


def use_template(pr, path):
    """copy a LaTeX template folder into Report/ (files it replaces are backed up first); returns (ok, message)"""
    src = Path(path or "").expanduser()
    if not src.is_dir():
        return False, "Choose a folder."
    main = _main_tex(src)
    if main is None:
        return False, "No main .tex file (one with \\documentclass and \\begin{document}) in that folder."
    f = folder(pr)
    prepare(pr)
    o = options(pr)
    names = [p.name for p in src.iterdir() if p.name not in OURS and not p.name.startswith(".")]
    replaced = [n for n in names if (f / n).is_file()] + ([o["main"]] if o["main"] not in names and (f / o["main"]).exists() else [])
    backup = _backup(f, replaced)
    for n in names:
        p = src / n
        if p.is_dir():
            shutil.copytree(p, f / n, dirs_exist_ok=True)
        else:
            shutil.copy2(p, f / n)
    done = patch_main(f / main.name)
    pr.update(report={**o, "template": str(src), "main": main.name})
    return True, (f"Template copied; main file {main.name}" + (": " + "; ".join(done) if done else "") +
                  (f". Your earlier files are in Report/{backup}." if backup else "."))


def use_default(pr):
    f = folder(pr)
    prepare(pr)
    o = options(pr)
    backup = _backup(f, ["report.tex"])
    shutil.copy2(SRC / "template" / "report.tex", f / "report.tex")
    pr.update(report={**o, "template": "default", "main": "report.tex"})
    return True, "The default template is in use: Report/report.tex" + (f" (your earlier file is in Report/{backup})." if backup else ".")


# ---------------------------------------------------------------- write and build (jobs)
def write(pr, log, use_ai=True, rewrite=False):
    """run make_report.py in <project>/Report with the project's python; the API key goes in the environment only"""
    py = pr.python()
    if py is None or not py.exists():
        return False, "The Python environment is not set up yet (Settings)."
    if not pipeline.ensure_packages(py, log):
        return False, "The missing packages could not be installed (internet connection? see Settings)."
    prepare(pr, log)
    f, o, st = folder(pr), options(pr), state(pr)
    items = [{k: it[k] for k in ("stem", "kind", "sheet", "file", "title", "group", "sheet_title", "what", "csvs")} for it in st["items"] if it["selected"]]
    (f / "report_items.json").write_text(json.dumps({"project": pr.name, "study": o["study"], "main": o["main"], "items": items}, indent=1), encoding="utf-8")
    s = ai.settings()
    args = ["--provider", "none"]
    env = {}
    if use_ai:
        k, _ = ai.key(s["provider"])
        if not k:
            return False, "No API key yet: add one in Settings, AI writing (or write without AI)."
        if not ai.model():
            return False, "No model chosen yet: choose one in Settings, AI writing."
        args = ["--provider", s["provider"], "--model", ai.model()] + (["--images"] if s["images"] else [])
        env["TDA_AI_KEY"] = k
    args += ["--rewrite"] if rewrite else []
    lines = []

    def both(text):
        lines.append(str(text))
        log(text)
    started, t0 = datetime.now(), time.time()
    both("$ " + " ".join([pr.rel(py), "Report/make_report.py"] + args))
    code = stream([py, "make_report.py"] + args, both, env=env, echo=False, cwd=f)
    head = [f"The Data Application {__version__}: the report", f"Project : {pr.name}", f"Run     : {started.strftime('%Y-%m-%d %H:%M:%S')} (took {time.time() - t0:.0f} s)",
            f"Result  : {['finished', 'finished, some items failed', 'stopped'][min(code, 2)] if code in (0, 1, 2) else 'STOPPED WITH AN ERROR'}", "-" * 78]
    (f / "report_log.txt").write_text("\n".join(head + lines) + "\n", encoding="utf-8")
    pipeline.write_run_info(f, "report", {"when": started.isoformat(timespec="seconds"), "seconds": round(time.time() - t0, 1), "ok": code == 0,
                                          "script": "make_report.py", "script_sha256": pipeline._sha(SRC / "make_report.py"), "command": " ".join(["make_report.py"] + args),
                                          "items": len(items), "template": o["template"], "main": o["main"]})
    if code == 0:
        return True, "The report is written in the project's folder Report. Build the PDF, or open the folder."
    if code == 1:
        return False, "Some items failed (see the Activity box); the others are written. Press Write again to retry the failed ones."
    stop = next((l for l in reversed(lines) if l.startswith(("STOPPED", "SKIPPED"))), "")
    return False, stop or "The report script stopped: " + pipeline.explain_failure(lines)


def biber_works():
    t = tex_tool("biber")
    if not t:
        return False
    try:
        return subprocess.run([t, "--version"], capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def tex_tool(name):
    """a TeX program: on the PATH, or where TeX Live / MacTeX / MiKTeX put it (an app started from the Dock does not see /Library/TeX/texbin)"""
    found = shutil.which(name)
    if found:
        return found
    for pattern in [f"/Library/TeX/texbin/{name}", f"/usr/texbin/{name}", f"/usr/local/texlive/*/bin/*/{name}", f"/opt/homebrew/bin/{name}",
                    f"C:/Program Files/MiKTeX/miktex/bin/x64/{name}.exe", f"C:/texlive/*/bin/windows/{name}.exe"]:
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[-1]
    return None


def build(pr, log):
    """the PDF of the report: latexmk (runs bibtex/biber itself) or pdflatex twice"""
    f, o = folder(pr), options(pr)
    main = f / o["main"]
    if not main.exists():
        return False, "There is no report yet: write it first."
    mk, pdftex = tex_tool("latexmk"), tex_tool("pdflatex")
    if not (mk or pdftex):
        return False, "No LaTeX found on this computer. Install MacTeX (macOS), MiKTeX (Windows) or TeX Live, or upload the Report folder to Overleaf."
    tool_dir = str(Path(mk or pdftex).parent)
    env = {"PATH": tool_dir + os.pathsep + os.environ.get("PATH", "")}
    if mk:
        code = stream([mk, "-pdf", "-interaction=nonstopmode", "-file-line-error", main.name], log, env=env, cwd=f)
    else:
        code = 0
        for _ in range(2):
            code = stream([pdftex, "-interaction=nonstopmode", "-file-line-error", main.name], log, env=env, cwd=f) or code
    pdf = main.with_suffix(".pdf")
    if code == 0 and pdf.exists():
        return True, f"PDF built: Report/{pdf.name}."
    texlog = main.with_suffix(".log")
    errs = []
    if texlog.exists():
        errs = [l.strip() for l in texlog.read_text(encoding="utf-8", errors="replace").splitlines() if re.match(r"^(\./)?[^:\s]+\.tex:\d+:", l) or l.startswith("! ")][:3]
    errs = errs or ["see the Activity box"]
    return False, "LaTeX stopped: " + " | ".join(errs) + (" (a PDF from an earlier build is still there)" if pdf.exists() else "")
