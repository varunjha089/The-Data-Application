"""Small JSON helpers: the settings of the application (app_config.json) and of each project (projects/<name>/project.json)."""
import json
import os
from pathlib import Path

from .paths import APP_CONFIG


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)                                  # a crash never leaves half a settings file


def app_load():
    return read_json(APP_CONFIG)


def app_save(cfg):
    write_json(APP_CONFIG, cfg)


def rel(path, base):
    """text for a path: relative to base when it is inside base (so the folder can move), otherwise absolute.
    The last part of the path is NOT resolved: .venv/bin/python3 is a symlink to the base python and must stay the venv's python."""
    p = Path(os.path.abspath(str(path)))
    p = p.parent.resolve() / p.name
    try:
        return str(p.relative_to(Path(base).resolve()))
    except ValueError:
        return str(p)


def absolute(text, base):
    p = Path(text)
    return p if p.is_absolute() else Path(base) / p
