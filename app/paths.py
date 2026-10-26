"""Paths. The application folder itself holds only code, so it can be copied to another computer; the user's projects live wherever the user chooses,
and the few settings of the application itself (text size, theme, list of projects) live in the user's own settings folder."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "requirements.txt"
STEPS = ROOT / "steps"                     # one Python script per step / plot (these are the files that go to the reviewer)


def app_data_dir():
    """where the application keeps its own settings: the user's settings folder of the system (override: environment variable THE_DATA_APP_HOME)"""
    override = os.environ.get("THE_DATA_APP_HOME")
    if override:
        return Path(override)
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "The Data Application"


APP_DATA = app_data_dir()
APP_CONFIG = APP_DATA / "app_config.json"  # text size, theme, the list of projects, the last project and location
APP_LOG = APP_DATA / "app.log"             # messages of the application (the macOS launcher writes here)
SHARED_VENV = APP_DATA / "venv"            # the one Python environment all projects share (outside every project, so deleting a project never removes it;
                                           # outside the application folder, so updates and their backups never touch it)


def shared_python():
    """the python of the shared venv (it may not exist yet)"""
    return SHARED_VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python3")


def default_location():
    """suggested parent folder for new projects (the user can choose any folder)"""
    docs = Path.home() / "Documents"
    return docs if docs.is_dir() else Path.home()
