"""Build the command that runs one of the scripts in steps/ with the python of a project's venv (the scripts are plain Python files: they can also be run by hand)."""
from .paths import STEPS


def step_command(py, script, args):
    """list for subprocess, or None when the project has no usable python yet"""
    if py is None or not py.exists():
        return None
    return [str(py), str(STEPS / script)] + [str(a) for a in args]
