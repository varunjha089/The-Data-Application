# The Data Application: plan, decisions and status

Started 2026-10-21 as a side project of the scientometric study in `Power_Query/` (the study itself does not depend on it).

## Goal

A standalone application, shareable with friends, that takes a Scopus export, cleans it, and (later) draws every plot and writes its CSV data.
One Python file per plot, readable on its own, because the files are submitted to a professor for review. The application only runs those files.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Form | a desktop window: a small server on 127.0.0.1 (random port, secret key in a cookie, Host/Origin check) serving a plain HTML/CSS/JS interface (`app/web/`), opened as an app window of Chrome / Edge / Brave / Chromium (`--app=`), else in the default browser; closing the window (pings stop) or Quit ends it. The terminal commands remain (for scripting) | Standard library only (no GUI toolkit to install: tkinter is missing from Homebrew Python and optional on Linux), works on macOS, Windows and Linux, same idea as CourseShelf (local server + web UI) without Rust or Node. The scripts do not depend on it. |
| Launchers | macOS `The Data Application.app` (a bundle whose script finds a Python 3.9+ and starts the window without Terminal), Windows `run.pyw` (pythonw, no console; errors to `data/app.log` and a message box) and `run.bat`, Linux `shortcut` command writes a .desktop entry with absolute paths | Double-click on each system, no terminal. |
| Data input | the browser sends the chosen file to the server, which writes the copy to `data/raw/` | no native file dialog needed anywhere; the venv folder has a Browse button that uses a native chooser (osascript / PowerShell / zenity / kdialog) or the path can be typed. |
| Environment | per project (Settings tab): create `.venv` in the project and install `requirements.txt`, or point to a venv the user has, or use another project's venv | Nothing goes into the system Python; the user's own environment is respected. |
| How scripts run | the launcher calls `<venv python> steps/<script>.py --input ... --output ...` | The scripts are ordinary files: they can be run by hand, read and reviewed. |
| Data | the chosen CSV is copied to the project's `data/raw/`; the original is never changed; `project.json` remembers the copy (size, SHA-256 hash, time) | The analysis stays reproducible even if the original moves. |
| Cleaning | the steps of the study notes (Power Query query Clean_Main_Data) plus text hygiene and checks, in `steps/01_clean_data.py` | The Excel workbook and the application then agree; checks stop the run instead of writing a doubtful file. |
| Paths | code paths relative to the application folder; `project.json` stores paths inside the project as relative paths | The folder can be copied to another computer. |
| Cross-platform | launcher and `app/` use the standard library only (Python 3.9+); `run.command` (macOS), `run.sh` (Linux), `run.bat` (Windows); file dialog: tkinter, else the system chooser (osascript / PowerShell / zenity / kdialog), else a typed path; the venv python is found in `bin/` or `Scripts/`; `project.json` stores the venv python as a relative path (relative to the project) (the last part is not resolved: it is a symlink to the base python) | Works on any system, the folder can be moved, and the venv is really used even when the base Python has no pandas. |
| Projects | a project is a **folder the user chooses** (name + location on the opening screen; the project folder is created inside the chosen one): `project.json` = its settings (name, venv, main data, results), `data/raw/`, `01_Clean_Data/`, optional own `.venv`. The application remembers the list of projects (absolute paths) and the last location in `app_config.json`; the opening screen creates a project or opens one from the list or by choosing its folder; a missing folder is marked and can be removed from the list (files are never deleted); a project can share another project's venv | Projects can live anywhere (a documents folder, a drive, a shared folder), several side by side, each reproducible from its own folder; nothing personal is inside the application folder. |
| App settings location | `app_config.json` and `app.log` in the user's settings folder (macOS `~/Library/Application Support/The Data Application/`, Windows `%APPDATA%`, Linux `~/.config`; override with the environment variable `THE_DATA_APP_HOME`, used by the tests) | The application folder stays clean and shareable; running it never writes there. |
| Menu and pages | inside a project a **collapsible menu on the left** (Overview, Settings, Step 1 Clean, then the sheets in groups); every sheet has its own page: description, **Generate data**, one **Generate plot** button per plot, the **data table** (paged, with a tab per extra CSV), the plots with PNG/SVG downloads, download of CSV and log; the Activity log sits under every page; dots show done / out of date | One long page or tabs would not hold 24 tasks; each task shows its table and its plot. |
| Sheets | the 24 sheets of the reference workbook as scripts in `steps/sheets/<Sheet>/<Sheet>.py` (+ `<Sheet>_plot.py` for 18 of them); the application copies the script into `<project>/<Sheet>/` and runs it there with the project's python, so each sheet folder holds the script, its CSV, its plot and `<Sheet>_log.txt`; a needed sheet is generated first; `References` gets the raw CSV through `--raw`; the folder layout (01_Clean_Data and the sheet folders side by side) is the one of `Power_Query/Workbook_Sheets`, so the scripts also run there on their own | Same files for the user's own folder and for every project; results identical to it; scripts readable for review. |
| Results and logs | each step writes into its own folder inside the project, named after the step (`01_Clean_Data/`): the result, the report of the script, `clean_log.txt` (the run as it happened, with paths relative to the application, hashes and software versions) and a copy of the script used. The window and the terminal commands share `app/pipeline.py`, so both save the log | The run can be written about later without copying text from the screen; the exact script is kept with its result. |
| Not shared | nothing personal is in the application folder; `.gitignore` only lists `.venv/`, `__pycache__/`, `Backup/` | The folder can be sent as it is. |

## Status (2026-10-21)

Built: opening screen (create a project with a name and a chosen folder, open one from the list or by choosing its folder), projects with their own settings, the left menu with Overview, Settings, Step 1 and 24 sheet pages
(data table with paging and extra tables, plot buttons, plots with downloads, logs), Generate all data / all plots, automatic generation of needed sheets, stale marks, per-project venv with "Install the missing packages",
main-data copy, cleaning with log, terminal commands (`projects`, `new --location`, `add`, `status`, `env`, `data`, `clean`, `shortcut`, `gui`, each with `-p NAME`). App settings and log are in the user's settings folder.

Checked (all on macOS, January data, 1,149 papers):
- a new project with its own venv (pandas + matplotlib installed by the application, about 40 s); cleaning identical to our own `Workbook_Sheets/01_Clean_Data`; **all 27 CSVs of the 24 sheets made through the server are byte-identical to our own `Workbook_Sheets` results**; Generate all plots made 18 plots (19 pictures);
  a sheet that needs others (e.g. Author_Summary) generated Authors first; two jobs at once: the second refused; re-cleaning marks all 24 sheets "out of date"; a sheet without cleaned data fails with a clear message;
- the table endpoint (paging, extra CSV), the files endpoint (PNG, CSV download; a path trick, an unknown sheet and a non-picture are refused); a project made with a pandas-only venv shows `missing: matplotlib`, can clean but not plot, and "Install the missing packages" fixed it;
- the interface in headless Chrome: Overview with the menu, a sheet page with its table and plots (two plots on one page), a sheet page with an extra table tab.
- the 18 plots were looked at one by one; earlier checks (opening screen, Settings, Clean, Python 3.9 / 3.13 / 3.14 / 3.15, moved folder, simulated Windows venv layout, `The Data Application.app`) still hold for the unchanged parts.

NOT checked: a real Windows or Linux computer; clicking the buttons with the mouse in the window (every button calls a route that was tested, and the rendered pages were looked at, but no click was made); the hidden-menu (collapsed) look; long runs with other Scopus exports
(different columns may break a sheet script: the cleaning skips missing columns, the sheet scripts do not); plots when a table has fewer rows than the chart expects (for example fewer than 5 sources); the January export's 79 papers without a source title are left out of the source sheets by design.

## Next

1. Make the sheet scripts robust for exports with fewer columns or fewer rows (and test with another Scopus export).
2. A page for the cleaning comparison with a second method (the college's), once the senior has decided.
3. The remaining analyses of the notes (keywords, networks, maps) as new sheets: script + entry in `app/sheets.py`.
4. Decide on a native shell (pywebview now, or a Tauri/Wails wrapper later).
5. Project rename and an "archive" instead of delete.

## Packages and the world map (2026-10-21)

- Missing packages (matplotlib, numpy, openpyxl, pillow) are downloaded automatically into the project's environment the first time a clean / sheet / plot run needs them (internet needed); Settings still shows the manual button.
- New sheet `World_Map` (group Countries): documents of every country and the map of the 15 most productive countries (matplotlib only; Natural Earth polygons in `world_countries_india_view.json`). Checked: run on the January data in the `wm_rs_application` project, plot viewed. NOT checked: Windows/Linux.

## Choices asked from the user (2026-10-21)

A sheet can declare options (`_OPTIONS` in `app/sheets.py`); its page shows them above the buttons, they are saved in `project.json` (`sheet_options`) when changed and passed to the sheet script as arguments. First uses: "World map" (number of countries) and "Authors over time" (heat map and timeline) (number of authors in the timeline, keep ties or not; defaults 15 / cut at exactly N). A plot of a sheet with options regenerates the data first. Checked: saving, arguments, script, plot (10 authors with ties cut). NOT checked: clicking in the window.

- 2026-10-21: the sheets Chord_Country_Collaboration and Chord_Others are one task, Country_Collaboration (two CSVs, two plots). Checked: both plots generated and viewed in the wm_rs_application project. The old folders in that project are left as they are.

- 2026-10-21: timeline (bubble) plots with a "top n" choice for Sources ("Sources over time", default 10) and Countries (new task "Countries over time", default 10), like Authors; bubble area scales with the largest value of the plot. Checked: all three plots generated and viewed in wm_rs_application. NOT checked: clicking in the window.

- 2026-10-22: bookmarks: the dot of every menu item can become a red, green, violet or orange star (hover the marker, choose a colour; the same colour again, or the x, removes it). Saved in project.json ("bookmarks"). Checked in Chrome: hover, choose, reload. NOT checked: touch screens (a click on the marker also opens the colours).

- 2026-10-22: "Source impact" has eight plots to choose from (bars, two pyramids, bubbles, dumbbell h/g, heat map, citations per paper, m-index against first year); the top n sources (default 15, by h-index) is a saved choice, the CSV gets a column "In plots". A sheet can run one plot at a time (`_PER_PLOT`, script argument --only ID). Checked: all eight generated and viewed in wm_rs_application. NOT checked: clicking in the window.

- 2026-10-22: "Affiliations over time" also has a timeline (bubble) plot with a saved "number of institutions" choice (default 10, ties cut), like Sources and Countries. Checked: generated and viewed in wm_rs_application. NOT checked: clicking in the window.

- 2026-10-22: new task "Country radar" (Countries group): radar chart of the top countries on five indicators (documents, citations, citations per document, country h-index, share of multi-country papers), scaled to the top 10; the number of countries drawn is a saved choice (default 5). From the October chart Charts/08_Radar. Checked: generated and viewed in wm_rs_application; values compared with the October table. NOT checked: clicking in the window.

- 2026-10-22: new task "Languages (pie)" (Main information group): papers by language of the original document; the number of languages with their own slice is a saved choice (default 8, the rest grouped as "Other languages"). Checked: generated and viewed in wm_rs_application; counts add up to the 1,149 papers. NOT checked: clicking in the window.

- 2026-10-22: the task "Conferences (editions)" was built and then taken out of the application on request; its code is kept in `future/Conferences/` and the idea in `FUTURE_PLAN.md` (point 2).
