# CLAUDE.md: The Data Application

Standing instructions for working on this folder (`Power_Query/The_Data_Application/`). Read this first, then `PLAN.md` (decisions, what was checked and what was NOT), `README.md` (use) and `FUTURE_PLAN.md` (ideas for later, not built yet).

## What it is

A standalone, shareable desktop application (a local web server shown in an app window; standard library only). Work happens in **projects**: each is a folder chosen by the user (any place), with its own `project.json` settings (venv, main data, results); the application keeps the list of projects and its own settings in the user's settings folder (`app/paths.py`: `APP_DATA`, override `THE_DATA_APP_HOME`). The opening screen creates or opens a project; inside it tabs (Clean data, Settings, later more) call the scripts of `steps/`.

## Standing rules

- **Runs everywhere (macOS, Windows, Linux).** Use `pathlib`/`os.path`, never hard-code `/` or `\\`; the venv python is `bin/python3` or `Scripts/python.exe`; never resolve the symlink of a venv python (`config.rel` keeps the last part as it is); open files with an explicit encoding (`utf-8`, `utf-8-sig`); no shell-only commands in the code. The launchers must stay in step (`run.command` = `run.sh`).
- **Standalone and shareable.** No path of the author's computer anywhere (no `/Users/...`, no `Power_Query/...`). All paths relative to the folder (`app/paths.py`). The launcher and `app/` use the **standard library only** and must start under Python 3.9 (no `X | None`, no `match`).
- **One Python file per step or plot in `steps/`**, readable on its own (header: what it does, input, method, output), taking `--input` / `--output`, needing only what `requirements.txt` lists. The application only calls them (`app/runner.py`); never copy plotting or cleaning logic into `app/`.
- **Never change the user's original data**; it is copied to the project's `data/raw/`. Never delete the user's files (no delete-project feature on purpose). Outputs go only into the project folder, one folder per step (`01_Clean_Data/`, `02_...`).
- **Settings belong to a project** (`project.json`, saved at once, relative paths inside the project); only text size, theme, the list of projects and the last project/location are application-wide (`app_config.json` in the user's settings folder, never in the application folder). The application folder must stay free of user data: running the application must not create files in it.
- A check that fails must stop the run with a clear message and write nothing (except the log of the failed run). Every step writes into its own folder named after it (`01_Clean_Data/`, `02_...`) and saves a log of the run there automatically.
- Keep `README.md` (use) and `PLAN.md` (decisions, checked / NOT checked) up to date for every feature.
- Back up the code before a change: `zip -qr "Backup/$(date +%Y-%m-%d_%H-%M-%S)_<why>.zip" app steps the_data_app.py requirements.txt README.md PLAN.md CLAUDE.md` (`Backup/` is not shared).
- The user wears spectacles: keep text in the application large and plain. The machine is macOS (BSD `sed`): edit with Python or the Edit tool, not `sed -i`.
- **Version control: git, for this folder only** (`The_Data_Application/` is the repository; the rest of `Power_Query/` is not). After a finished change (a feature, a fix, a doc update that was asked for) that has been checked, commit it: `git add -A && git commit` with a short message that says what changed and why, ending with the attribution lines of the session. One topic per commit; never commit a half-working state. The remote is `origin` = https://github.com/varunjha089/The-Data-Application (public): push only when Varun asks, and never rewrite pushed history. The repository is public: never commit data, tokens, personal paths or names of study projects in code. The `Backup/` zips are no longer needed before a change: git is the history (keep making one only before something large and risky). Never commit user data, `.venv/`, `__pycache__/` or logs (see `.gitignore`); look at `git status` before committing.
- Python on this machine: `python3` is 3.15 without packages; the packages live in `/opt/homebrew/bin/python3.14`.

## Layout

```
the_data_app.py        entry point; calls app.cli.main (no command = open the window)
The Data Application.app / run.pyw / run.bat / run.command / run.sh   launchers (macOS app bundle, Windows without console, terminal starters)
app/paths.py           ROOT, REQUIREMENTS, STEPS; APP_DATA / APP_CONFIG / APP_LOG (user settings folder); default_location()
app/config.py          JSON read/write (atomic), app_config.json (text size, theme, last project), rel()/absolute() for stored paths
app/project.py         Project (its folder, project.json, python(), main_data(), result paths); the list of known projects (paths in app_config.json): create(name, location), add_existing, forget, find, get, list_projects
app/envsetup.py        create/point to a venv, check Python version and packages (REQUIRED must match requirements.txt), install; install_missing(py) downloads only the missing ones (pipeline.ensure_packages calls it before every clean/sheet/plot run)
app/dataset.py         validation (Scopus columns), copy + SHA-256, register(project, ...)
app/runner.py          step_command(py, script, args)
app/pipeline.py        the steps as functions: clean_data(project, log) (script + results + clean_log.txt + copy of the script), run_sheet / run_plot / run_all (copy steps/sheets/<Sheet>/<script> into <project>/<Sheet>/, run it there with the project's python, log to <Sheet>_log.txt; needed sheets first)
app/sheets.py          registry of the 24 sheets: group, title, description, needs, extra CSVs, plots (id, title, files)
app/years.py           the project's years in the plots (presets last10/last5/all/custom, resolved once and saved; roll_forward)
app/look.py            the project's plot look (text, size, dpi, PDF/TIFF, colour-blind palette) -> arguments of steps/common/plotlook.py
app/sample.py          made-up Scopus export and the "Sample project" (window button, `sample` command, tests)
app/jobs.py            one background job at a time with a pollable log; stream() runs a command and logs its lines
app/server.py          the window's server (127.0.0.1, key cookie, Host/Origin check) and its API; app.project = the open project; run() opens the window and ends when it closes
app/web/               index.html (opening screen, left menu, pages), style.css, app.js (plain, no libraries, no internet)
app/native.py          native folder chooser, show in file manager (every system)
app/window.py          opens Chrome/Edge/Brave/Chromium in app mode, else the default browser
app/cli.py             terminal commands (gui, projects, new, status, env, data, clean, shortcut), each with -p NAME
steps/01_clean_data.py the cleaning (Power Query steps of the study notes + text hygiene + checks); steps are shared by all projects
steps/sheets/<Sheet>/  <Sheet>.py (data) and <Sheet>_plot.py (plot) for the sheets of the analysis: standalone scripts that expect the layout "01_Clean_Data and the sheet folders side by side" (SHEETS = folder above the script); only pandas / numpy / matplotlib; a .json next to a script (World_Map: country polygons) is copied with it
steps/common/          names.py (country / institution / parent-organisation rules, country fallback), plotlook.py (plot-look wrapper); copied into <project>/common/
tests/test_app.py      unittest: fast tests (stdlib) + a full run of the sample project (needs pandas/numpy/matplotlib); TDA_QUICK=1 for the fast part only
requirements.txt       packages for the venvs
```

A new sheet or plot = a script in `steps/sheets/<Sheet>/` + an entry in `app/sheets.py`: the menu, the page, the table, the buttons and the routes are generic (`app.js` renderSheet, `server.py` /api/sheets, /api/sheet/*). A new kind of step (like the cleaning) needs a function in `pipeline.py`, a job in `server.py` and a page in `index.html`/`app.js`. `Power_Query/Workbook_Sheets` holds the same scripts for use without the application: keep the two in step (the app copy is the master for the sheet/plot scripts only after they were generated and checked there).

## Test without touching anything

First: `python -m unittest discover -s tests -v` with a Python that has the packages (e.g. a project's venv). Every feature gets a test there.

Tests must not touch the user's real settings or projects: set `THE_DATA_APP_HOME=<scratch>/appdata` and `PYTHONDONTWRITEBYTECODE=1`, and create test projects with `--location <scratch>`. The application can then be run from the real folder (it writes nothing there). **Do not hand the user a window running from a scratch copy**: open the real `The Data Application.app`.

```sh
S=<scratch>; export THE_DATA_APP_HOME=$S/appdata PYTHONDONTWRITEBYTECODE=1; cd The_Data_Application
/opt/homebrew/bin/python3.14 the_data_app.py new "Test" --location $S
/opt/homebrew/bin/python3.14 the_data_app.py env -p Test --create          # or: env -p Test --venv <existing venv>
/opt/homebrew/bin/python3.14 the_data_app.py data -p Test "<some Scopus csv>"
/opt/homebrew/bin/python3.14 the_data_app.py clean -p Test && /opt/homebrew/bin/python3.14 the_data_app.py status -p Test
```

Test the window without a screen: `python3 the_data_app.py gui --no-window --port 8765` prints a URL with `?key=...`; `curl -c jar "<url>"` then `curl -b jar .../api/projects`, `-X POST -d '{"name":"Test"}' .../api/project/create`, `.../api/status`; add `&tab=settings` to the URL to start on a tab; a headless screenshot: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --screenshot=out.png --window-size=1180,2300 --virtual-time-budget=6000 "<url>"`. 
