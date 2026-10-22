"""Commands of The Data Application (standard library only): the window (this is the default) and terminal commands for scripting and testing.
Every command that works on a project takes  -p NAME  (the project's name or folder name); without it the only project, or the last opened one, is used."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from . import config, dataset, envsetup, pipeline
from . import project as projects
from .paths import ROOT, STEPS


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
    """create the project's own venv (--create) or use an existing one (--venv PATH); missing packages are installed"""
    if create:
        py = envsetup.venv_python(pr.venv_dir) or envsetup.create_venv(pr.venv_dir)
    elif venv:
        py = envsetup.resolve(venv)
        if py is None:
            print("No python found there: give the folder of the venv (it contains pyvenv.cfg and a bin or Scripts folder).")
            return 1
    else:
        print("Say what to do: --create (a new venv in the project) or --venv PATH (one you have).")
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


def cmd_clean(pr):
    ok, msg = pipeline.clean_data(pr, print)
    print("\n" + msg)
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
    e.add_argument("--create", action="store_true", help="create .venv in the project and install the packages")
    e.add_argument("--venv", metavar="PATH", help="use this existing venv (folder or python file)")
    d = with_project(sub.add_parser("data", help="choose the project's main data (a copy is made)"))
    d.add_argument("file", help="the Scopus CSV")
    with_project(sub.add_parser("clean", help="clean the project's main data"))
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
    pr = pick_project(a.project)
    if pr is None:
        return 1
    if a.cmd == "status":
        return cmd_status(pr)
    if a.cmd == "env":
        return cmd_env(pr, a.create, a.venv)
    if a.cmd == "data":
        return cmd_data(pr, a.file)
    return cmd_clean(pr)
