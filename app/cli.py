"""Commands of The Data Application (standard library only): the window (this is the default) and terminal commands for scripting and testing.
Every command that works on a project takes  -p NAME  (the project's name or folder name); without it the only project, or the last opened one, is used."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from . import __version__, config, dataset, envsetup, pipeline, sample, update, years
from . import project as projects
from .paths import ROOT, STEPS, SHARED_VENV


def pick_project(name):
    """the project a terminal command works on; None (and a message) when it cannot be decided"""
    if name:
        pr = projects.find(name)
        if pr is None:
            names = ", ".join(p["name"] for p in projects.list_projects() if p["exists"]) or "none"
            print(f"No project '{name}'. Known projects: {names}. Create one with: new NAME --location FOLDER")
        return pr
    items = [p for p in projects.list_projects() if p["exists"]]
    if not items:
        print("There is no project yet. Create one with:  python3 the_data_app.py new \"My project\" --location FOLDER  (or in the window).")
        return None
    last = config.app_load().get("last_project")
    if len(items) == 1:
        return projects.Project(items[0]["path"])
    if last and projects.is_project_dir(last):
        print(f"(project '{projects.Project(last).name}', the last one opened; use -p NAME to choose another)")
        return projects.Project(last)
    print("Several projects exist: choose one with -p NAME:  " + ", ".join(p["name"] for p in items))
    return None


def cmd_projects():
    items = projects.list_projects()
    if not items:
        print("No projects yet.")
    for p in items:
        state = f"data: {p['records'] or 'none'} records   cleaned: {p['cleaned'] or 'no'}" if p["exists"] else "FOLDER NOT FOUND"
        print(f"{p['name']:<30} {state}\n    {p['path']}")
    return 0


def cmd_new(name, location):
    pr, err = projects.create(name, location)
    if pr is None:
        print(err)
        return 1
    pr.touch()
    print(f"Project '{pr.name}' created in {pr.dir}")
    return 0


def cmd_add(path):
    pr, err = projects.add_existing(path)
    print(err if pr is None else f"Project '{pr.name}' added to the list ({pr.dir})")
    return 1 if pr is None else 0


def cmd_status(pr):
    cfg = pr.load()
    print(f"Project     : {pr.name}   ({pr.dir})")
    py = pr.python()
    if py is None:
        print("Environment : not set up")
    else:
        ok, msg = envsetup.check(py)
        print(f"Environment : {'ready' if ok else 'PROBLEM'}  ({msg})\n              {cfg.get('python')}")
    info = cfg.get("main_data")
    if info and pr.main_data():
        print(f"Main data   : {info['file']}  ({info['records']} records, copied {info['copied']})")
    elif info:
        print(f"Main data   : {info['file']}  <- the copy is missing, choose the data again")
    else:
        print("Main data   : none chosen")
    if cfg.get("clean_data") and pr.clean_file.exists():
        print(f"Clean data  : {cfg['clean_data']['file']}  (made {cfg['clean_data']['made']})")
    elif pr.clean_file.exists():
        print("Clean data  : file exists but is older than the main data: clean again")
    else:
        print("Clean data  : not made yet")
    scripts = sorted(p.name for p in STEPS.glob("*.py"))
    print("Scripts     : " + (", ".join(scripts) if scripts else "none"))
    return 0


def cmd_env(pr, create, venv):
    """use the application's shared venv (--create; made the first time) or an existing one (--venv PATH); missing packages are installed"""
    if create:
        py = envsetup.venv_python(SHARED_VENV) or envsetup.create_venv(SHARED_VENV)
    elif venv:
        py = envsetup.resolve(venv)
        if py is None:
            print("No python found there: give the folder of the venv (it contains pyvenv.cfg and a bin or Scripts folder).")
            return 1
    else:
        print("Say what to do: --create (the shared venv of the application, one for all projects) or --venv PATH (one you have).")
        return 1
    if py is None:
        return 1
    ok, msg = envsetup.check(py)
    if not ok and msg.startswith("missing packages"):
        print(f"This python: {msg}.")
        if not envsetup.install_requirements(py):
            print("The installation failed. Is there an internet connection? If your Python is very new, use Python 3.11 to 3.13.")
            return 1
        ok, msg = envsetup.check(py)
    if not ok:
        print("Not usable:", msg)
        return 1
    pr.set_python(py)
    print(f"Environment ready: {py}  ({msg})")
    return 0


def cmd_data(pr, file):
    ok, msg = dataset.import_file(pr, file)
    print(("Done: " if ok else "Not accepted: ") + msg)
    return 0 if ok else 1


def cmd_clean(pr, exclude_only_queries=None):
    if exclude_only_queries is not None:                       # saved in the project, so the window uses it too ("" switches it off)
        pr.update(clean_options={**(pr.load().get("clean_options") or {}), "exclude_only_queries": exclude_only_queries})
    ok, msg = pipeline.clean_data(pr, print)
    print("\n" + msg)
    return 0 if ok else 1


def cmd_sample(location):
    pr, err = sample.create_sample_project(location)
    if pr is None:
        print(err)
        return 1
    pr.touch()
    print(f"Project '{pr.name}' created in {pr.dir} with a made-up Scopus export ({pr.load()['main_data']['records']} records).")
    print(f"Next: python3 the_data_app.py env -p \"{pr.name}\" --create   (or open it in the window)")
    return 0


def cmd_years(pr, preset, first, last, roll):
    try:
        if roll:
            years.roll_forward(pr)
        elif preset:
            years.set_window(pr, preset, first or 0, last or 0)
    except ValueError as e:
        print(e)
        return 1
    w = years.info(pr)
    print(f"Years in the plots: {years.PRESETS[w['preset']]}: {years.text(w)} (set on {w['set_on']})" + (f"; rolled forward it would be {w['today'][0]}-{w['today'][1]}" if w["can_roll"] else ""))
    return 0


def cmd_run(pr, plots):
    ok, msg = pipeline.run_all(pr, print, plots)
    print("\n" + msg)
    return 0 if ok else 1


def cmd_update(check_only):
    st = update.check(force=True)
    if st.get("error"):
        print(st["error"])
        return 1
    if not st["available"]:
        print(f"The Data Application {st['current']} is the latest version.")
        return 0
    lt = st["latest"]
    print(f"Version {lt['version']} is available (you have {st['current']}), published {lt['published']}: {lt['url']}\n\n{lt['notes']}\n")
    if check_only:
        return 0
    ok, msg = update.install(print)
    print("\n" + msg.replace(" The application restarts now.", " Start the application again to use it."))
    return 0 if ok else 1


def make_shortcut():
    """a shortcut with absolute paths (paths with spaces are fine): Linux applications menu, Windows desktop; macOS has the .app"""
    py, script = sys.executable, ROOT / "the_data_app.py"
    if sys.platform == "darwin":
        print("On macOS use 'The Data Application.app' in this folder (drag it to the Dock or the Applications folder).")
        return 0
    if os.name == "nt":
        pyw = Path(py).with_name("pythonw.exe")
        target = pyw if pyw.exists() else Path(py)
        link = Path(os.path.expanduser("~")) / "Desktop" / "The Data Application.lnk"
        ps = ("$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%s'); $s.TargetPath = '%s'; $s.Arguments = '\"%s\" gui'; "
              "$s.WorkingDirectory = '%s'; $s.Save()" % (link, target, script, ROOT))
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
        print(f"Shortcut created on the desktop: {link}" if r.returncode == 0 else "Could not create the shortcut: " + r.stderr.strip())
        return r.returncode
    apps = Path(os.path.expanduser("~/.local/share/applications"))
    apps.mkdir(parents=True, exist_ok=True)
    entry = apps / "the-data-application.desktop"
    entry.write_text("[Desktop Entry]\nType=Application\nName=The Data Application\nComment=Clean and analyse Scopus exports\n"
                     f'Exec="{py}" "{script}" gui\nPath={ROOT}\nTerminal=false\nCategories=Education;Science;\n', encoding="utf-8")
    print(f"Added to the applications menu: {entry}")
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):                      # old Windows consoles: show ? instead of failing on a character
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="the_data_app.py", description="The Data Application: without a command the window opens.")
    ap.add_argument("--version", action="version", version=f"The Data Application {__version__}")
    sub = ap.add_subparsers(dest="cmd")

    def with_project(p):
        p.add_argument("-p", "--project", metavar="NAME", help="project name or folder (default: the only or the last opened project)")
        return p
    g = sub.add_parser("gui", help="open the application window (this is what happens without a command)")
    g.add_argument("--no-window", action="store_true", help="start the server only and print its address")
    g.add_argument("--port", type=int, default=0, help="fixed port (default: a free one)")
    sub.add_parser("projects", help="list the projects")
    n = sub.add_parser("new", help="create a project")
    n.add_argument("name")
    n.add_argument("--location", metavar="FOLDER", help="folder in which the project folder is created (default: Documents)")
    ad = sub.add_parser("add", help="add an existing project folder (one that contains project.json) to the list")
    ad.add_argument("path")
    with_project(sub.add_parser("status", help="show what is set up in a project"))
    e = with_project(sub.add_parser("env", help="create or point to the project's Python venv"))
    e.add_argument("--create", action="store_true", help="use the application's shared venv (one for all projects; made the first time) and install the packages")
    e.add_argument("--venv", metavar="PATH", help="use this existing venv (folder or python file)")
    d = with_project(sub.add_parser("data", help="choose the project's main data (a copy is made)"))
    d.add_argument("file", help="the Scopus CSV")
    cl = with_project(sub.add_parser("clean", help="clean the project's main data"))
    cl.add_argument("--exclude-only-queries", metavar="IDS", default=None, help="comma list of search IDs (e.g. Q3): papers returned only by these searches are dropped; saved in the project; \"\" switches it off")
    sm = sub.add_parser("sample", help="create a project with a made-up Scopus export, to try the application")
    sm.add_argument("--location", metavar="FOLDER", help="folder in which the project folder is created (default: Documents)")
    y = with_project(sub.add_parser("years", help="show or set the years the plots draw (the whole project)"))
    y.add_argument("preset", nargs="?", choices=sorted(years.PRESETS), help="last10, last5, all or custom")
    y.add_argument("--from", dest="first", type=int, help="first year (custom)")
    y.add_argument("--to", dest="last", type=int, help="last year (custom)")
    y.add_argument("--roll-forward", action="store_true", help="work the preset out again for today")
    r = with_project(sub.add_parser("run", help="generate the data of every sheet (or, with --plots, every plot)"))
    r.add_argument("--plots", action="store_true")
    u = sub.add_parser("update", help="check GitHub for a newer version and install it (projects and data are never touched)")
    u.add_argument("--check-only", action="store_true", help="only say whether a newer version exists")
    sub.add_parser("shortcut", help="make a desktop / applications-menu shortcut that opens the window (Linux, Windows)")
    a = ap.parse_args(argv)
    if a.cmd in (None, "gui"):
        from . import server
        return server.run(port=getattr(a, "port", 0), open_window=not getattr(a, "no_window", False))
    if a.cmd == "projects":
        return cmd_projects()
    if a.cmd == "new":
        return cmd_new(a.name, a.location)
    if a.cmd == "add":
        return cmd_add(a.path)
    if a.cmd == "shortcut":
        return make_shortcut()
    if a.cmd == "sample":
        return cmd_sample(a.location)
    if a.cmd == "update":
        return cmd_update(a.check_only)
    pr = pick_project(a.project)
    if pr is None:
        return 1
    if a.cmd == "status":
        return cmd_status(pr)
    if a.cmd == "env":
        return cmd_env(pr, a.create, a.venv)
    if a.cmd == "data":
        return cmd_data(pr, a.file)
    if a.cmd == "years":
        return cmd_years(pr, a.preset, a.first, a.last, a.roll_forward)
    if a.cmd == "run":
        return cmd_run(pr, a.plots)
    return cmd_clean(pr, a.exclude_only_queries)
