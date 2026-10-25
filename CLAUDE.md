# CLAUDE.md: The Data Application

Instructions for working on this folder: the program of The Data Application, a public repository (https://github.com/varunjha089/The-Data-Application, MIT).
Read this file first, then `README.md` (how it is used). If `CLAUDE.local.md` exists next to this file, read it too: it holds the owner's own setup and is never
committed. The owner's development notes (`PLAN.local.md`, `FUTURE_PLAN.local.md`) are local files as well.

## What it is

A desktop application for the scientometric analysis of Scopus CSV exports: clean the export, then generate 34 sheets (tables) in 8 groups, with their plots,
each from its own readable Python script. It is a small web server on 127.0.0.1 shown in an app window (Chrome/Edge in app mode, else the default browser),
written with the Python standard library only; the analysis scripts run in a per-project venv with pandas, numpy and matplotlib. Version: `app/__init__.py`.

Work happens in **projects**: a project is a folder the user chooses anywhere, with its own `project.json` (venv, main data, choices, years, plot look), a copy
of the export in `data/raw/`, `01_Clean_Data/`, and one folder per sheet. The application keeps only the list of projects, text size and theme in the user's
settings folder (`app/paths.py`: `APP_DATA`; override with `THE_DATA_APP_HOME`).

## Rules

- **Shareable and standalone.** No path, folder name, study, search ID, year range or threshold of any one user in the code or the docs: everything a study needs is
  a setting of its project (`_OPTIONS` in `app/sheets.py`, `project.json`, or a file in the project such as `topic_slices.json`). Notes about a particular study go into
  a `*.local.*` file (ignored by git), never into a tracked file. Examples use the made-up sample data (`app/sample.py`).
- **Runs everywhere** (macOS, Windows, Linux): `pathlib`, explicit encodings (`utf-8`, `utf-8-sig`), no shell-only commands; the venv python is `bin/python3` or
  `Scripts/python.exe` (never resolve its symlink). The launcher and `app/` use the standard library only and must start on Python 3.9: no `X | None`, no `match`,
  no f-string that reuses its own quote inside `{}` (a test checks this). The launchers stay in step (`run.command` = `run.sh`).
- **One Python file per step or plot** in `steps/`, readable on its own (header: what it does, the Excel method it follows, input, output, how to run it), using only
  what `requirements.txt` lists. The application only runs them; never copy cleaning or plotting logic into `app/`.
- **The user's data is never changed or deleted.** The export is copied into the project; outputs go only into the project's folders; there is no delete-project
  feature. The application folder never receives user data: running the application must not create files in it.
- **A failure stops with a plain message.** A failed check writes nothing except the log of the failed run; messages say what is wrong and what to do
  (`dataset.validate`, `pipeline.explain_failure`).
- **Every run is recorded** in its folder: `<Sheet>_log.txt` / `<Sheet>_plot_log.txt` and `run_info.json` (version, script SHA-256, arguments, input SHA-256, choices,
  years, plot look, software). Keep both when changing `pipeline.py`.
- **Large, plain text** in the interface (the owner wears spectacles). On macOS edit files with Python or the Edit tool (BSD `sed -i` differs).

## Layout

```
the_data_app.py           entry point -> app.cli.main (no command = open the window)
The Data Application.app  run.pyw  run.bat  run.command  run.sh      launchers (macOS bundle, Windows without console, terminal)
app/__init__.py           __version__
app/paths.py              ROOT, STEPS, REQUIREMENTS; APP_DATA / APP_CONFIG / APP_LOG (the user's settings folder)
app/config.py             atomic JSON read/write, app_config.json, rel()/absolute() for stored paths
app/project.py            Project (folder, project.json, python(), main_data(), result paths); the list of projects: create, add_existing, forget, find, get
app/envsetup.py           make or use a venv, check Python and packages (REQUIRED matches requirements.txt), install the missing ones
app/dataset.py            validate an export (plain-words reasons: Excel file, WoS/RIS, semicolons, not UTF-8, missing columns), copy + SHA-256
app/pipeline.py           clean_data, run_sheet, run_plot, run_all: copy steps/... into the project, run with the project's python, log, run_info.json
app/sheets.py             registry of the sheets: group, title, description, needs, extra CSVs, plots, options (_OPTIONS), per-plot sheets
app/years.py              the project's years in the plots: presets last10 / last5 / all / custom, resolved once and SAVED; roll_forward
app/look.py               the project's plot look -> arguments of steps/common/plotlook.py
app/sample.py             made-up Scopus export and the "Sample project" (window button, `sample` command, tests)
app/update.py             self-update like a desktop program: daily check of GitHub's latest release, install (git fast-forward or release ZIP + backup),
                          the new version's quick tests, rollback, restart; THE_DATA_APP_UPDATE_API points it elsewhere in tests
app/jobs.py               one background job at a time with a pollable log; stream() runs a command
app/server.py             the window's server: 127.0.0.1, key cookie, Host/Origin check, the /api routes
app/web/                  index.html, style.css, app.js (plain JavaScript, no libraries, no internet)
app/native.py, window.py  folder chooser and file manager; opening the window
app/cli.py                commands: gui, projects, new, add, status, env, data, clean, sample, years, run, shortcut (-p NAME), --version
steps/01_clean_data.py    the cleaning (text hygiene, documented Power Query steps, country fallback, checks)
steps/common/             names.py (countries, institutions, parent organisations, country fallback), plotlook.py (plot-look wrapper); copied into <project>/common/
steps/sheets/<Sheet>/     <Sheet>.py (data) and <Sheet>_plot.py (plots); a .json next to a script is copied with it
tests/test_app.py         fast tests (standard library) + a full run of the sample project (needs pandas, numpy, matplotlib)
future/                   finished code taken out of the menu (kept for later)
```

## How to add things

- **A sheet or a plot**: a script in `steps/sheets/<Sheet>/` + a row in `_ROWS` in `app/sheets.py`. The menu, page, table, buttons and routes are generic.
  A script that makes one plot per call goes in `_PER_PLOT` (it gets `--only ID`); extra tables in `_EXTRA_CSV`; downloads in `_DOWNLOADS`; an explanation in `_EXPLAIN`.
- **A choice on a sheet page**: an entry in `_OPTIONS` (kinds `number`, `check`, `select`; `"for": "plot"` sends it to the plot script only; `show_if` hides it until
  another choice has a value). It is saved in `project.json` and passed as arguments, so the script stays runnable by hand.
- **A year axis**: use the helper block of the year plots (`year_args`, `year_window`, `year_label`, `year_axis`, `year_rows`) and add the sheet to the `_year_options`
  loop in `app/sheets.py` (choose whether it follows the project's years or draws all years by default).
- **A new kind of step** (like the cleaning): a function in `pipeline.py`, a job in `server.py`, a page in `index.html` / `app.js`.
- Every feature: a test in `tests/test_app.py`, an entry in `README.md`.

## Test

```sh
python -m unittest discover -s tests -v              # with a Python that has pandas, numpy, matplotlib (any project's venv): about 2 minutes
TDA_QUICK=1 python3 -m unittest discover -s tests    # only the fast tests (standard library)
```

Tests and trials never touch the user's real settings or projects: set `THE_DATA_APP_HOME=<scratch>/appdata` and `PYTHONDONTWRITEBYTECODE=1`, and make projects
with `--location <scratch>` (the sample project is ideal: `python3 the_data_app.py sample --location <scratch>`). Never hand the user a window started from a scratch copy.

- The window without a screen: `python3 the_data_app.py gui --no-window --port 8765` prints a URL with `?key=...`; `curl -c jar "<url>"`, then `curl -b jar .../api/status`;
  `&tab=settings` (or `&tab=sheet:<Sheet>`) starts on a page; headless Chrome `--headless=new --screenshot=out.png --window-size=1300,2400 --virtual-time-budget=6000 "<url>"`.
- Look at every plot you changed (open the PNG). Check a choice by changing it in the page, not only through the API.
- Before sharing a version: a fresh clone, a new venv made by the application (`env --create`) on the oldest Python you can find, the full tests.

## Git and releases

- This folder is the repository (`main`, remote `origin`). Look at `git status` first; commit after every checked change with a message that says what and why
  (attribution lines of the session at the end); one topic per commit; never a half-working state. Push to `origin` after every change that is verified (tests pass, the new commits scanned clean): the owner asked for this on 2026-10-24; never rewrite pushed history.
- Never commit data, tokens, personal paths, `.venv/`, `__pycache__/`, logs or `*.local.*` (see `.gitignore`). Before a push, scan the new commits for them.
- A release: raise `__version__` in `app/__init__.py`, describe it in `README.md`, run the full tests and the fresh-clone test, commit, tag `vX.Y.Z`, push the
  tag, and publish a **GitHub Release** for it whose body is the what's-new list: the users' update window shows that body, and `releases/latest` is what
  every copy checks. A tag without a release is never offered. Never publish a release that has not passed the tests: copies install it on a click.
