"""Native folder/file choosers and 'show in file manager', for every system. Each returns None when there is nothing to offer."""
import os
import shutil
import subprocess
import sys

TITLES = {"venv": "Select the folder of your Python virtual environment", "project": "Choose the folder in which the project is saved",
          "existing": "Choose the project folder (it contains project.json)",
          "template": "Choose the folder of your LaTeX template (it contains the main .tex file)"}
TITLE_FILE = "Select the Scopus CSV export"


def _command(kind, why="venv"):
    title = TITLES.get(why, TITLES["venv"]) if kind == "folder" else TITLE_FILE
    if sys.platform == "darwin":
        what = "folder" if kind == "folder" else "file"
        return ["osascript", "-e", 'POSIX path of (choose %s with prompt "%s")' % (what, title)]
    if os.name == "nt":
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if not ps:
            return None
        if kind == "folder":
            code = ("Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.FolderBrowserDialog; "
                    "$d.Description = '%s'; if ($d.ShowDialog() -eq 'OK') { $d.SelectedPath }" % title)
        else:
            code = ("Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.OpenFileDialog; $d.Title = '%s'; "
                    "$d.Filter = 'CSV files (*.csv)|*.csv|All files (*.*)|*.*'; if ($d.ShowDialog() -eq 'OK') { $d.FileName }" % title)
        return [ps, "-NoProfile", "-Command", code]
    if shutil.which("zenity"):
        return ["zenity", "--file-selection", "--title=" + title] + (["--directory"] if kind == "folder" else [])
    if shutil.which("kdialog"):
        return ["kdialog", "--title", title, "--getexistingdirectory" if kind == "folder" else "--getopenfilename", os.path.expanduser("~")]
    return None


def browse(kind, why="venv"):
    """returns (path or None, error text or None); why = what the folder is for (the dialog title)"""
    cmd = _command(kind, why)
    if cmd is None:
        return None, "This computer has no folder chooser the application can use: type the path instead."
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None, "The chooser could not be opened: type the path instead."
    out = r.stdout.strip().splitlines()
    return (out[0] if out else None), None


def show_in_file_manager(path):
    path = str(path)
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif os.name == "nt":
            os.startfile(path)  # noqa: S606  (Windows only)
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except (OSError, AttributeError):
        return False
