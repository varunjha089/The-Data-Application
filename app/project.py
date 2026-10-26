"""Projects. A project is a folder that the user chooses; in it: project.json (the project's OWN settings: venv, main data, results), data/raw/ (copy of the main data),
01_Clean_Data/ (results of step 1), and optionally its own .venv. The application remembers the list of projects (app_config.json in the user's settings folder),
so several projects, in different places, can be opened from the opening screen."""
import os
import re
from datetime import datetime
from pathlib import Path

from . import config
from .paths import default_location, shared_python


def _now():
    return datetime.now().isoformat(timespec="seconds")


def slugify(name):
    s = re.sub(r"[^\w\- ]", "", name, flags=re.UNICODE).strip().replace(" ", "_")
    return s[:60].strip("_.") or "project"


class Project:
    def __init__(self, path):
        self.dir = Path(path).expanduser().resolve()
        self.slug = self.dir.name
        self.config_file = self.dir / "project.json"
        self.raw = self.dir / "data" / "raw"            # copy of the main data
        self.venv_dir = self.dir / ".venv"              # a project's own venv (before 1.0: now all projects share paths.SHARED_VENV)
        self.clean = self.dir / "01_Clean_Data"         # results of step 1
        self.clean_file = self.clean / "clean_main_data.csv"
        self.clean_report = self.clean / "clean_report.txt"
        self.clean_log = self.clean / "clean_log.txt"

    # ---- settings (persistent: project.json)
    def load(self):
        return config.read_json(self.config_file)

    def save(self, cfg):
        config.write_json(self.config_file, cfg)

    def update(self, **changes):
        cfg = self.load()
        for k, v in changes.items():
            if v is None:
                cfg.pop(k, None)
            else:
                cfg[k] = v
        self.save(cfg)
        return cfg

    @property
    def name(self):
        return self.load().get("name", self.slug)

    def python(self):
        text = self.load().get("python")
        if text == "shared":                                  # the application's shared venv (paths.SHARED_VENV)
            return shared_python()
        return config.absolute(text, self.dir) if text else None

    def uses_shared(self):
        return self.load().get("python") == "shared"

    def set_python(self, py):
        self.update(python="shared" if py is not None and Path(py) == shared_python() else config.rel(py, self.dir))

    def rel(self, path):
        return config.rel(path, self.dir)

    def main_data(self):
        """Path of the copy of the main data, or None"""
        info = self.load().get("main_data")
        if not info:
            return None
        p = config.absolute(info["file"], self.dir)
        return p if p.exists() else None

    def touch(self):
        """remember that this project was opened (and where: the next new project is suggested in the same place)"""
        self.update(opened=_now())
        remember(self.dir)
        app = config.app_load()
        app["last_project"] = str(self.dir)
        app["last_location"] = str(self.dir.parent)
        config.app_save(app)


# ---- the list of projects the application knows (paths, in app_config.json)
def known():
    return [Path(p) for p in config.app_load().get("projects", [])]


def remember(path):
    app = config.app_load()
    items = app.get("projects", [])
    if str(Path(path)) not in items:
        items.append(str(Path(path)))
    app["projects"] = items
    config.app_save(app)


def forget(path):
    """take a project off the list (its folder and files are NOT touched)"""
    app = config.app_load()
    app["projects"] = [p for p in app.get("projects", []) if p != str(Path(path))]
    if app.get("last_project") == str(Path(path)):
        app.pop("last_project", None)
    config.app_save(app)


def relocate(old, new):
    """a project whose folder was moved: the list points to its new folder (same place in the list); returns (Project, None) or (None, message)"""
    new_dir = Path(os.path.expanduser(str(new or "").strip())).resolve() if str(new or "").strip() else None
    if new_dir is None or not is_project_dir(new_dir):
        return None, "That folder is not a project (it has no project.json). Choose the project's own folder."
    app = config.app_load()
    items = [str(new_dir) if p == str(Path(old)) else p for p in app.get("projects", [])]
    if str(new_dir) not in items:
        items.append(str(new_dir))
    app["projects"] = list(dict.fromkeys(items))                 # never twice in the list
    if app.get("last_project") == str(Path(old)):
        app["last_project"] = str(new_dir)
    config.app_save(app)
    return Project(new_dir), None


def is_project_dir(path):
    return (Path(path) / "project.json").is_file()


def get(path):
    """a project from the list, or None"""
    if path and str(Path(path)) in [str(p) for p in known()] and is_project_dir(path):
        return Project(path)
    return None


def find(text):
    """a project by its folder path, its name or its folder name (the terminal commands use this)"""
    text = (text or "").strip()
    if text and is_project_dir(Path(text).expanduser()):
        pr = Project(text)
        remember(pr.dir)
        return pr
    for d in known():
        if is_project_dir(d):
            pr = Project(d)
            if text.lower() in (pr.name.lower(), pr.slug.lower()):
                return pr
    return None


def add_existing(path):
    """register a project folder that is not in the list yet (it must contain project.json); returns (Project, None) or (None, error)"""
    p = Path(path).expanduser()
    if not p.is_dir():
        return None, "That folder does not exist."
    if not is_project_dir(p):
        return None, "That folder is not a project (it has no project.json). Choose the folder that contains project.json."
    pr = Project(p)
    remember(pr.dir)
    return pr, None


def create(name, location=None):
    """create <location>/<name as folder name>; returns (Project, None) or (None, error text)"""
    name = " ".join((name or "").split())
    if not name:
        return None, "Give the project a name."
    if len(name) > 80:
        return None, "That name is too long (80 characters at most)."
    if any(p["name"].lower() == name.lower() for p in list_projects() if p["exists"]):
        return None, f"A project called '{name}' already exists in the list: open it there."
    loc = Path(location).expanduser() if location and location.strip() else default_location()
    try:
        loc.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return None, f"Cannot use that location ({e}). Choose another folder."
    slug, n = slugify(name), 1
    while (loc / slug).exists():
        n += 1
        slug = f"{slugify(name)}_{n}"
    pr = Project(loc / slug)
    try:
        pr.dir.mkdir()
        pr.save({"name": name, "created": _now(), "opened": _now()})
    except OSError as e:
        return None, f"Cannot create the project there ({e}). Choose another folder."
    remember(pr.dir)
    return pr, None


def list_projects():
    out = []
    for d in known():
        if is_project_dir(d):
            c = config.read_json(d / "project.json")
            md = c.get("main_data") or {}
            out.append({"path": str(d), "slug": d.name, "exists": True, "name": c.get("name", d.name), "created": c.get("created", ""), "opened": c.get("opened", ""),
                        "records": md.get("records"), "data_file": md.get("file"), "has_python": bool(c.get("python")), "cleaned": (c.get("clean_data") or {}).get("made")})
        else:
            out.append({"path": str(d), "slug": d.name, "exists": False, "name": d.name, "created": "", "opened": "", "records": None, "data_file": None,
                        "has_python": False, "cleaned": None})
    return sorted(out, key=lambda p: (p["exists"], p["opened"]), reverse=True)
