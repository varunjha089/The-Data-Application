# The Data Application

A desktop application for the scientometric analysis of **Scopus exports**. Work is organised in **projects**: each project is a folder **that you choose**, with its own settings (Python
environment, main data) and its own results. You choose your Scopus CSV, the application keeps a copy of it, and it cleans it with a documented, checked
procedure. It is meant to be shared: the folder is self-contained, nothing depends on the computer of the person who wrote it, and no knowledge of Python is
needed to use it. It runs on **macOS, Windows and Linux**.

Today it can: **create and open projects, set up a Python environment per project, copy your main data into a project, clean the data, and generate every table and plot of the analysis**
(24 sheets, 18 plots): each task has its own page with its **data table** and a **Generate plot** button.

## What you need

- **Python 3.9 or newer** from https://www.python.org/downloads/ (on Windows tick "Add Python to PATH" in the installer; on Debian/Ubuntu also install
  `python3-venv`). Nothing else: the application installs what it needs into a virtual environment.
- **Google Chrome, Microsoft Edge, Brave or Chromium** is recommended: the application then opens in its own window (no tabs, no address bar).
  Without one it opens in your default browser instead (Safari, Firefox): everything works the same.
- An internet connection the first time a project sets up its environment (to download the packages, `pandas` for now). If your Python is brand new and a
  package is not available for it yet, use Python 3.11 to 3.13.
- A **Scopus export in CSV format** (Scopus, "Export", CSV, with all fields; the file needs the columns EID, Title, Authors and Year). Tick the **References** option in the Scopus export dialog (it is separate from "Bibliographical information"): without it the sheet References cannot be built and is skipped.

## Start (no terminal needed)

| System | How |
|---|---|
| macOS | double-click **`The Data Application.app`** (first time: right-click, Open; drag it to the Dock if you like) |
| Windows | double-click **`run.pyw`** (or `run.bat`); `python the_data_app.py shortcut` puts a shortcut on the desktop |
| Linux | `python3 the_data_app.py` once; `python3 the_data_app.py shortcut` adds it to the applications menu |

A window opens. **Closing the window ends the application** (or press **Quit**). Large text: **A+ / A-**, light or dark: **Light / dark** (remembered).

### The opening screen: create or open a project

- **Create a new project**: type a name (for example "Water monitoring 2016-2025"), **choose the folder** in which the project is saved (press *Choose folder...*, or type a path;
  the folder is created if it does not exist; the next project is suggested in the same place), and press Create. The project gets its own folder inside the one you chose
  (for example `<your folder>/Water_monitoring_2016-2025/`) and opens on its **Settings** page.
- **Open an existing project**: the list shows each project with its number of records, whether it has been cleaned, where it is saved and when it was last opened.
  A project whose folder has been moved or deleted is marked "folder not found" and can be **removed from the list** (its files are never touched).
- **A project that is not in the list** (for example one copied from another computer): choose its folder (the one that contains `project.json`) and it is added and opened.
- **Switch project** (top right) closes the project and returns to this screen.

### Inside a project: the menu on the left

After you open a project, the **menu on the left** (press *Menu* to hide or show it) lists the pages. A green dot means that the task has been done, an orange one that it is out of date
(the cleaned data is newer).

| Page | What |
|---|---|
| **Overview** | all tasks in one table; **Generate all data** and **Generate all plots** |
| **Settings** | the project's own, **persistent** settings (saved in `project.json`): the **Python environment** and the **main data**, plus the project's name and folder |
| **Step 1: Clean the data** | one button; the steps, counts and checks appear as they run; afterwards the report, the first rows of the cleaned data, and buttons to download the cleaned CSV, the report and the log |
| **Tables, Main information, Production, Sources, Authors, Affiliations, Countries, Documents** | one page per sheet of the analysis (the sheets of the reference workbook `Biblioshiny_Analysis.xlsx`), see below |

A task needs the cleaned data (step 1); a task that needs another sheet (for example *Author summary* needs *Authors*) generates it first by itself.

**A sheet page** shows: what the sheet is; **Generate data** (or *again*); one **Generate plot** button for each plot of the sheet (only where a chart makes sense); the **data table**
(50 rows per page, with a tab for each extra table, such as the parameters of the fitted curve); the **plots** with PNG and SVG downloads; and buttons to download the CSV and the log or to show the folder.
Every run is logged in the sheet's folder (`<Sheet>_log.txt`).

**Settings: Python environment.** Choose **Create a new venv** inside this project (recommended; it installs the packages from `requirements.txt`, with the progress
shown), **Use a venv I already have** (type its folder, or Browse; missing packages are installed there on request), or **Use the venv of another project**
(so that several projects share one environment and nothing is installed twice). A project made before a package was needed (for example matplotlib, for the plots) shows
**Install the missing packages**; until then cleaning and tables work, plots wait.

**Settings: Main data.** Press **Choose the Scopus CSV...** and pick the file. It is **copied into the project's `data/raw/`**; your original is never touched or moved.
Choosing a new file makes the earlier cleaned data "out of date" until you clean again.

## The sheets and plots

| Group | Sheets (plot = has a chart) |
|---|---|
| Tables | Authors, Affiliations, Countries, References, Author summary |
| Main information | Main information (plot: documents by type) |
| Production | Annual production, Average citations per year, Life cycle (plots) |
| Sources | Top sources (plot), Documents per source, Bradford's law (plot), Bradford core: who publishes there (3 plots per kind: countries, authors, institutions), Source impact (plot), Sources over time (plot) |
| Authors | Authors over time (plot), Lotka's law (plot), Author impact (plot) |
| Affiliations | Top affiliations (plot), Affiliations over time (plot) |
| Countries | Corresponding authors' countries (plot), Countries' production and citations (2 plots), Country collaboration pairs (plot), Country collaboration chord (chord diagram) |
| Documents | Most cited documents (plot) |

Each sheet is one Python file (`steps/sheets/<Sheet>/<Sheet>.py`) and each plot one more (`<Sheet>_plot.py`); the application copies the script into the project's folder `<Sheet>/` and runs it there with the project's Python,
so the folder of a project also holds the scripts and results of every sheet. The scripts are readable on their own: a header says what the sheet is, the Excel method it follows, its input and its output.
Year axes adapt to the data: the plots of production, citations, life cycle and "over time" (sheets 03, 04, 05, 10, 11, 14, 18, 21) draw about 10 round ticks whatever the span, start where
1% of the papers have been reached (the hidden years and their paper count are named in the axis label) and shade years after the current year as early access. A corpus of 55 years (1972-2027)
used to print 56 overlapping labels. The helpers (`year_start`, `year_label`, `year_axis`) are a short block inside each of those scripts, because each script must run on its own.
Notes on the January export: 79 papers have no source title (left out of the source sheets) and the export keeps at most 10 references per paper.

## What the cleaning does

`steps/01_clean_data.py` is an ordinary Python file (it can be run by hand and read on its own). It follows the Power Query steps of the study, in order:

| Step | What |
|---|---|
| A | text hygiene on every column: repair garbled accents (`UniversitÃ¤t` becomes `Universität`), remove control characters, decode HTML entities, trim spaces |
| 1 | keep records with a valid EID (`2-s2.0-...`), one row per EID |
| 2 | count the references of each paper, drop the long References column |
| 3 | remove records with no authors |
| 4 | remove duplicate papers (same title, ignoring case and punctuation; the earliest year and the most cited one is kept) |
| 5 | keywords in lower case, `-` and `_` become spaces |
| 6 | affiliations: `& amp;` to `&`, Türkiye to Turkey, Viet Nam to Vietnam, one fix for "UPMC Univ. Paris 06" |
| 7 | **Countries** of each paper (distinct, in order), Country Count, Collaboration Type (SCP = one country, MCP = two or more) |
| 8 | Corresponding Country, from the correspondence address |
| 9 | source titles cleaned |
| C | checks (unique EID and title, no missing EID/Authors/Title/Year, plausible years, Cited by is not negative, Country Count agrees with the list) |

Every run saves, automatically, in the project's folder **`01_Clean_Data/`** (named after the step, so later steps get `02_...`, `03_...`):

| File | What |
|---|---|
| `clean_main_data.csv` | the cleaned data, one row per paper |
| `clean_report.txt` | the report made by the script: rows left after each step, what was checked, what was **not** changed (missing values, characters already damaged in the export, ...) |
| `clean_log.txt` | the **log of the run**, for writing about it: project, date and duration, input file (with hash), the command, the full output, output hash, Python and pandas versions |
| `01_clean_data.py` | a copy of the exact script that made the result |

If a check fails, nothing is written except the log of the failed run, and the reason is shown. If your export has fewer columns than the usual one, the steps that need a missing column are skipped.

## Folders

The application folder holds only code, so it can be copied as it is:

```
The_Data_Application/
  The Data Application.app   macOS: double-click      run.pyw / run.bat   Windows      the_data_app.py   (all systems, also the commands)
  run.command / run.sh       start from a terminal (macOS / Linux)
  requirements.txt           packages for the venvs (pandas now; each new plot adds what it needs)
  app/                       the application: server and window (app/web = the interface), projects, set-up, data copy, running the scripts
  steps/01_clean_data.py     step 1 (shared by all projects)
  steps/sheets/<Sheet>/      the scripts of the 24 sheets (<Sheet>.py) and of their plots (<Sheet>_plot.py)
```

Each project is a folder where **you** put it:

```
<the folder you chose>/<project name>/
  project.json               the project's settings: name, venv, main data, results
  data/raw/                  the copy of the main data
  01_Clean_Data/             results of step 1: cleaned CSV, report, log of the run, copy of the script
  Authors/, 03_Annual_Production/, ...   one folder per sheet that has been generated: its script, CSV, log, and the plot (.png/.svg) if made
  .venv/                     the project's own virtual environment (if you chose "Create a new venv")
```

The application's own few settings (text size, theme, the list of projects, the last project and location, and a log) are kept in your user settings folder, not in the
application folder: macOS `~/Library/Application Support/The Data Application/`, Windows `%APPDATA%\The Data Application\`, Linux `~/.config/The Data Application/`.

The window is a small web page served only on your own computer (address 127.0.0.1, a secret key, no internet involved).

## Terminal commands (optional, for scripting)

`python3 the_data_app.py` opens the window. The same things exist as commands (on Windows use `py -3` instead of `python3`); `-p NAME` chooses the project (its name or its folder;
default: the only one, or the last opened):

```sh
python3 the_data_app.py projects                      # list the projects
python3 the_data_app.py new "My project" --location ~/Documents   # create a project (its folder is made inside ~/Documents)
python3 the_data_app.py add /path/to/project            # add an existing project folder (contains project.json) to the list
python3 the_data_app.py env  -p "My project" --create # or: --venv /path/to/venv
python3 the_data_app.py data -p "My project" export.csv
python3 the_data_app.py clean -p "My project"
# the sheets and plots are generated in the window (Overview or the page of a sheet)
python3 the_data_app.py status -p "My project"
python3 the_data_app.py gui --no-window               # start the server only and print its address
```

## Sharing it with friends

Send the application folder as it is: it contains no projects, data, settings or environments of yours (those are in the folders you chose and in your user settings folder).
Your friend opens the application, creates a project in a folder of their choice, and the window sets everything up on their computer. (`PLAN.md` and `CLAUDE.md` are notes for
the developers.) On a Mac, a downloaded copy of the `.app` is blocked once by Gatekeeper: right-click it, choose Open, confirm. To share a **project** (not the application),
copy its folder without `.venv` (a venv does not work on another system) and open it on the other computer with "A project that is not in the list".

## What comes next

More analyses will be added the same way: a script in `steps/sheets/` (or `steps/`), an entry in `app/sheets.py`, and it appears in the menu with its table and plot button.
Decisions and status are in `PLAN.md`, working rules in `CLAUDE.md`.

## Packages and the world map (2026-10-21)

- Missing packages (matplotlib, numpy, openpyxl, pillow) are downloaded automatically into the project's environment the first time a clean / sheet / plot run needs them (internet needed); Settings still shows the manual button.
- New sheet `World_Map` (group Countries): documents of every country and the map of the 15 most productive countries (matplotlib only; Natural Earth polygons in `world_countries_india_view.json`). Checked: run on the January data in the `wm_rs_application` project, plot viewed. NOT checked: Windows/Linux.

## Choices asked from the user (2026-10-21)

A sheet can declare options (`_OPTIONS` in `app/sheets.py`); its page shows them above the buttons, they are saved in `project.json` (`sheet_options`) when changed and passed to the sheet script as arguments. First uses: "World map" (number of countries) and "Authors over time" (heat map and timeline) (number of authors in the timeline, keep ties or not; defaults 15 / cut at exactly N). A plot of a sheet with options regenerates the data first. Checked: saving, arguments, script, plot (10 authors with ties cut). NOT checked: clicking in the window.

- 2026-10-21: timeline (bubble) plots with a "top n" choice for Sources ("Sources over time", default 10) and Countries (new task "Countries over time", default 10), like Authors; bubble area scales with the largest value of the plot. Checked: all three plots generated and viewed in wm_rs_application. NOT checked: clicking in the window.

- 2026-10-22: bookmarks: the dot of every menu item can become a red, green, violet or orange star (hover the marker, choose a colour; the same colour again, or the x, removes it). Saved in project.json ("bookmarks"). Checked in Chrome: hover, choose, reload. NOT checked: touch screens (a click on the marker also opens the colours).

- 2026-10-22: "Source impact" has eight plots to choose from (bars, two pyramids, bubbles, dumbbell h/g, heat map, citations per paper, m-index against first year); the top n sources (default 15, by h-index) is a saved choice, the CSV gets a column "In plots". A sheet can run one plot at a time (`_PER_PLOT`, script argument --only ID). Checked: all eight generated and viewed in wm_rs_application. NOT checked: clicking in the window.

- 2026-10-22: "Affiliations over time" also has a timeline (bubble) plot with a saved "number of institutions" choice (default 10, ties cut), like Sources and Countries. Checked: generated and viewed in wm_rs_application. NOT checked: clicking in the window.

- 2026-10-22: new task "Country radar" (Countries group): radar chart of the top countries on five indicators (documents, citations, citations per document, country h-index, share of multi-country papers), scaled to the top 10; the number of countries drawn is a saved choice (default 5). From the October chart Charts/08_Radar. Checked: generated and viewed in wm_rs_application; values compared with the October table. NOT checked: clicking in the window.

- 2026-10-22: new task "Languages (pie)" (Main information group): papers by language of the original document; the number of languages with their own slice is a saved choice (default 8, the rest grouped as "Other languages"). Checked: generated and viewed in wm_rs_application; counts add up to the 1,149 papers. NOT checked: clicking in the window.

- 2026-10-22: the task "Conferences (editions)" was built and then taken out of the application on request; its code is kept in `future/Conferences/` and the idea in `FUTURE_PLAN.md` (point 2).

## Version control

This folder is a git repository (`git log` shows the history of the application's code). Only the application is under git, not the projects or the data.

- 2026-10-23: new tasks "Country bursts", "Author bursts" and "Institution bursts" (CiteSpace-style burst history): Kleinberg burst detection on the yearly paper counts, table + year strip as PNG/SVG + an HTML page in the layout of CiteSpace (offered as a download only). Choices saved: how many to show (10), gamma (0.7, a decimal choice), smallest number of papers (5, authors 4). Checked: on the Country data gamma 0.7 gives the same 10 countries and the same begin and end years as the CiteSpace table (strengths within about 0.4); authors and institutions have no CiteSpace table to compare with. NOT checked: clicking in the window; a burst in the last year only (e.g. an author whose papers are all in 2025) is an edge effect.

## Name rules and the Topic_Slices sheet (added 2026-10-24)

- `steps/common/names.py` holds the country and institution rules (known-country list, aliases, US state + ZIP, institution without departments, one name per spelling). The application copies it into `<project>/common/` before every clean or sheet run.
- Countries and Affiliations now use these rules; an address with no recognisable country gives no country instead of a wrong one (USA, FRG, "MA 02125" and so on).
- `01_clean_data.py` keeps `Query_IDs` and `N_Queries` when the data has them. The Clean page has a box **Searches to drop** (also `python3 the_data_app.py clean -p NAME --exclude-only-queries Q13`): papers returned only by those searches (for example a search known to be noise) are dropped. It is saved in the project, and changing it marks the cleaned file out of date.
- Sheet `Topic_Slices`: slices by search, term trends, optional gap audit and reference audit. Needs `Query_IDs` and a References export. What it cuts and looks for is **not in the code**: it is read from `topic_slices.json` in the project folder (next to `01_Clean_Data`). The first run writes one with automatic choices (the biggest searches as slices, the most frequent keywords as the term trend, no audit) for you to edit; the format is at the top of `steps/sheets/Topic_Slices/Topic_Slices.py`. A worked definition (the Watershed study: flood / water mapping with conformal prediction) is in `steps/sheets/Topic_Slices/examples/`.
- The burst plots write a "no burst found" picture instead of failing; the Bradford title shows the years of the data.
