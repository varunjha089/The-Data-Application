"""The virtual environment (venv): create one inside this folder, or point to one you already have; check and install the packages."""
import os
import subprocess
import sys
from pathlib import Path

from .paths import REQUIREMENTS

# import name -> pip name (what the scripts import; keep in step with requirements.txt)
REQUIRED = {"pandas": "pandas", "numpy": "numpy", "matplotlib": "matplotlib", "openpyxl": "openpyxl", "PIL": "pillow"}
MIN_PYTHON = (3, 9)


def venv_python(venv_dir):
    """python executable inside a venv folder (None if there is none)"""
    venv_dir = Path(venv_dir)
    for rel in (("Scripts", "python.exe"), ("bin", "python3"), ("bin", "python")):
        p = venv_dir.joinpath(*rel)
        if p.exists():
            return p
    return None


def resolve(text):
    """what the user typed -> python executable. Accepts the venv folder, its bin/Scripts folder, or the python file itself."""
    text = text.strip().strip("'\"")
    if os.name != "nt":
        text = text.replace("\\ ", " ")                       # a path dragged into a terminal has "\ " for spaces
    p = Path(os.path.expanduser(text)).resolve()
    if p.is_file():
        return p
    if p.is_dir():
        found = venv_python(p)                                # the venv folder (also a conda environment folder)
        if found:
            return found
        if p.name in ("bin", "Scripts") and (p.parent / "pyvenv.cfg").exists():   # the bin/ or Scripts/ folder of a venv
            for name in ("python3", "python", "python.exe"):
                if (p / name).exists():
                    return p / name
    return None


def _run(py, code):
    return subprocess.run([str(py), "-c", code], capture_output=True, text=True)


def python_version(py):
    r = _run(py, "import sys;print('%d.%d.%d' % sys.version_info[:3])")
    return r.stdout.strip() if r.returncode == 0 else None


def is_venv(py):
    r = _run(py, "import sys;print(int(sys.prefix != getattr(sys, 'base_prefix', sys.prefix)))")
    return r.returncode == 0 and r.stdout.strip() == "1"


def missing_packages(py):
    """list of pip names that cannot be imported in this python"""
    out = []
    for mod, pip in REQUIRED.items():
        if _run(py, "import " + mod).returncode != 0:
            out.append(pip)
    return out


def install_missing(py, say=print):
    """install the missing packages of REQUIRED (only those) into this python; returns True when nothing is missing afterwards"""
    missing = missing_packages(py)
    if not missing:
        return True
    say("Installing the missing packages: " + ", ".join(missing) + " (this can take a minute; an internet connection is needed)")
    pip_cmd = [str(py), "-m", "pip", "install", "--disable-pip-version-check"] + missing
    r = subprocess.run(pip_cmd, capture_output=True, text=True)
    for line in (r.stdout + r.stderr).splitlines()[-6:]:
        say(line)
    return r.returncode == 0 and not missing_packages(py)


def install_requirements(py):
    print("Installing the packages from requirements.txt (this can take a minute)...")
    r = subprocess.run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(REQUIREMENTS)])
    return r.returncode == 0


def base_python():
    """the python that creates the venv (a console python, not pythonw.exe)"""
    exe = sys.executable
    if os.name == "nt" and exe.lower().endswith("pythonw.exe"):
        console = Path(exe).with_name("python.exe")
        if console.exists():
            return str(console)
    return exe


def create_venv(venv_dir):
    """create a venv with the python that runs the launcher; returns the venv's python or None"""
    venv_dir = Path(venv_dir)
    if venv_python(venv_dir):
        print(f"A venv already exists at {venv_dir}; using it.")
        return venv_python(venv_dir)
    print(f"Creating a virtual environment at {venv_dir} ...")
    r = subprocess.run([base_python(), "-m", "venv", str(venv_dir)])
    if r.returncode != 0:
        print("Could not create the venv. On Debian/Ubuntu install the package 'python3-venv' first; "
              "otherwise create a venv yourself and choose the option 'use an existing venv'.")
        return None
    return venv_python(venv_dir)


def check(py):
    """(ok, message) for a python executable that is to run the scripts"""
    if py is None or not Path(py).exists():
        return False, "no python found there"
    v = python_version(py)
    if v is None:
        return False, "that python does not start"
    if tuple(int(x) for x in v.split(".")[:2]) < MIN_PYTHON:
        return False, f"Python {v} is too old (need {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer)"
    miss = missing_packages(py)
    if miss:
        return False, "missing packages: " + ", ".join(miss)
    return True, f"Python {v}, packages OK"
