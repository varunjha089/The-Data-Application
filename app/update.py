"""Updates, the way a desktop program does it (standard library only).

At most once a day, in the background, the application asks GitHub for the latest release of its repository (nothing about the user is sent:
a plain GET of the public releases API). When it is newer than this copy, the window shows it with its notes: Install and restart / Later /
Skip this version. Checking can be switched off; the choice is kept in the user's settings (app_config.json, "update").

Installing never touches projects or data (they live outside the application folder):
  - a copy made with git (the folder has .git): `git fetch --tags`, then a fast-forward to the release tag. It refuses when tracked files were
    changed by hand, or when the history does not fast-forward, and says so; nothing is changed then.
  - any other copy (a downloaded ZIP): the release's ZIP is downloaded, the current program files are backed up to the user's settings folder
    (updates/), and the new files are copied over the old ones.
Then the quick tests of the NEW version run; if they fail, the previous version is put back (git reset to the old commit, or the backup).
Finally the application starts again from the new files and the old window closes.

Tests use THE_DATA_APP_UPDATE_API to point the check at a local server instead of GitHub.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

from . import __version__, config
from .paths import APP_DATA, ROOT

REPO = "varunjha089/The-Data-Application"          # where the releases are published (a fork changes this line)
CHECK_EVERY = 24 * 3600
SKIP = {".git", ".venv", "Backup", "__pycache__", ".DS_Store"}   # never copied or backed up: not part of a release


def api_url():
    return os.environ.get("THE_DATA_APP_UPDATE_API") or f"https://api.github.com/repos/{REPO}/releases/latest"


def parse_version(v):
    """'v0.10.2' -> (0, 10, 2); anything that is not a number counts as 0"""
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-+]", str(v).strip().lstrip("vV"))[:3])


def newer(a, b):
    return parse_version(a) > parse_version(b)


def method():
    """'git' when this copy is a git checkout and git is installed, else 'zip'"""
    return "git" if (ROOT / ".git").exists() and shutil.which("git") else "zip"


def fetch_latest(timeout=8):
    req = urllib.request.Request(api_url(), headers={"Accept": "application/vnd.github+json", "User-Agent": f"TheDataApplication/{__version__}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8"))
    tag = d.get("tag_name") or ""
    if not tag:
        raise ValueError("the release has no tag")
    return {"version": tag.lstrip("vV"), "tag": tag, "name": d.get("name") or tag, "notes": (d.get("body") or "").strip(),
            "url": d.get("html_url") or f"https://github.com/{REPO}/releases", "zip": d.get("zipball_url") or "",
            "published": (d.get("published_at") or "")[:10]}


def _settings():
    return config.app_load().get("update") or {}


def _save(**changes):
    cfg = config.app_load()
    u = dict(cfg.get("update") or {})
    u.update(changes)
    cfg["update"] = u
    config.app_save(cfg)
    return u


def state():
    """what the window shows, without asking GitHub"""
    u = _settings()
    latest = u.get("latest")
    enabled = u.get("enabled", True)
    available = bool(latest) and newer(latest["version"], __version__)
    return {"current": __version__, "enabled": enabled, "latest": latest, "available": available,
            "show": enabled and available and u.get("skipped") != latest["version"] if available else False,
            "skipped": u.get("skipped"), "last_check": u.get("last_check"), "error": u.get("error"), "method": method()}


def check(force=False):
    """ask GitHub (at most once a day unless force); errors are remembered, never raised"""
    u = _settings()
    if not force and (not u.get("enabled", True) or time.time() - u.get("last_check_unix", 0) < CHECK_EVERY):
        return state()
    try:
        _save(latest=fetch_latest(), error=None, last_check=time.strftime("%Y-%m-%d %H:%M"), last_check_unix=time.time())
    except Exception as e:                              # offline, rate limit, no release yet: the application works on
        _save(error=f"could not check for updates ({e})", last_check=time.strftime("%Y-%m-%d %H:%M"), last_check_unix=time.time())
    return state()


def set_enabled(on):
    _save(enabled=bool(on))
    return state()


def skip(version):
    _save(skipped=version)
    return state()


def _git(*args, log=None):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if log:
        for line in (r.stdout + r.stderr).strip().splitlines():
            log("  " + line)
    return r


def _quick_tests(log):
    """the new version's own fast tests, in a throw-away settings folder"""
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, TDA_QUICK="1", THE_DATA_APP_HOME=tmp, PYTHONDONTWRITEBYTECODE="1", THE_DATA_APP_UPDATING="1")
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
    for line in tail:
        log("  " + line)
    return r.returncode == 0


def _version_on_disk():
    m = re.search(r'__version__\s*=\s*"([^"]+)"', (ROOT / "app" / "__init__.py").read_text(encoding="utf-8"))
    return m.group(1) if m else "?"


def _program_files():
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        if p.is_file() and not (set(rel.parts) & SKIP) and p.suffix not in (".pyc", ".log"):
            yield p, rel


def install(log):
    """install the latest release found by check(); returns (ok, message). The caller restarts the application when ok."""
    latest = _settings().get("latest")
    if not latest or not newer(latest["version"], __version__):
        return False, "There is no newer version to install."
    log(f"Updating The Data Application {__version__} -> {latest['version']} ({method()})")
    if method() == "git":
        if _git("status", "--porcelain", "--untracked-files=no").stdout.strip():
            return False, ("Files of the application were changed by hand (git status shows them), so it was not updated. "
                           "Keep or undo those changes, then update again.")
        prev = _git("rev-parse", "HEAD").stdout.strip()
        log("$ git fetch --tags origin")
        if _git("fetch", "--tags", "origin", log=log).returncode != 0:
            return False, "Could not reach the repository (internet connection?). Nothing was changed."
        log(f"$ git merge --ff-only {latest['tag']}")
        if _git("merge", "--ff-only", latest["tag"], log=log).returncode != 0:
            return False, ("This copy has its own commits, so the release cannot be applied as a fast-forward. "
                           "Nothing was changed; update it with git by hand.")

        def rollback():
            _git("reset", "--hard", prev, log=log)
    else:
        if not latest.get("zip"):
            return False, "The release has no download. Nothing was changed."
        backup_dir = APP_DATA / "updates"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / f"backup_{__version__}_{time.strftime('%Y%m%d_%H%M%S')}.zip"
        with zipfile.ZipFile(backup, "w", zipfile.ZIP_DEFLATED) as z:
            for p, rel in _program_files():
                z.write(p, rel.as_posix())
        log(f"Backup of this version: {backup}")
        with tempfile.TemporaryDirectory() as tmp:
            dl = Path(tmp) / "release.zip"
            log(f"Downloading {latest['zip']}")
            req = urllib.request.Request(latest["zip"], headers={"User-Agent": f"TheDataApplication/{__version__}"})
            try:
                with urllib.request.urlopen(req, timeout=120) as r, open(dl, "wb") as f:
                    shutil.copyfileobj(r, f)
                with zipfile.ZipFile(dl) as z:
                    z.extractall(Path(tmp) / "x")
            except Exception as e:
                return False, f"The download failed ({e}). Nothing was changed."
            tops = [p for p in (Path(tmp) / "x").iterdir() if p.is_dir()]
            src = tops[0] if len(tops) == 1 else Path(tmp) / "x"
            if not (src / "the_data_app.py").is_file():
                return False, "The download is not The Data Application. Nothing was changed."
            n = 0
            for p in src.rglob("*"):
                rel = p.relative_to(src)
                if p.is_file() and not (set(rel.parts) & SKIP):
                    (ROOT / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, ROOT / rel)
                    n += 1
            log(f"{n} files copied")

        def rollback():
            with zipfile.ZipFile(backup) as z:
                z.extractall(ROOT)
            log(f"restored from {backup}")
    log("Checking the new version (its quick tests) ...")
    got = _version_on_disk()
    if not _quick_tests(log) or got != latest["version"]:
        rollback()
        return False, f"The new version did not pass its checks (found version {got}); the previous version {__version__} was put back."
    _save(skipped=None)
    return True, f"Updated to {latest['version']}. The application restarts now."


def restart():
    """start the application again from the (new) files on disk; the caller then stops this one"""
    kw = {"cwd": str(ROOT), "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kw["start_new_session"] = True
    subprocess.Popen([sys.executable, str(ROOT / "the_data_app.py"), "gui"], **kw)
