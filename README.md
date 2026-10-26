# The Data Application

A desktop application for the scientometric analysis of **Scopus exports**. Work is organised in **projects**: each project is a folder **that you choose**, with its own settings (Python
environment, main data) and its own results. You choose your Scopus CSV, the application keeps a copy of it, and it cleans it with a documented, checked
procedure. It is meant to be shared: the folder is self-contained, nothing depends on the computer of the person who wrote it, and no knowledge of Python is
needed to use it. It runs on **macOS, Windows and Linux**.

Today it can: **create and open projects, set up a Python environment per project, copy your main data into a project, clean the data, and generate every table and plot of the analysis**
(24 sheets, 18 plots): each task has its own page with its **data table** and a **Generate plot** button.

## Getting started (5 minutes)

1. **Get the application**: `git clone https://github.com/varunjha089/The-Data-Application.git` (or download the ZIP from that page and unzip it).
2. **Install Python 3.9 to 3.13** if you do not have it (see *What you need* below). Nothing else: the application installs its own packages.
3. **Start it**: macOS double-click `The Data Application.app`; Windows double-click `run.pyw`; Linux `python3 the_data_app.py`.
4. **No Scopus export yet?** On the opening screen press **Create the sample project**: a made-up export (invented papers, authors and journals) to try every step.
   With your own data: **Create a new project**, then on **Settings** choose your Scopus CSV.
5. On **Settings** press **Set up the environment** (the first time downloads pandas, numpy and matplotlib, about a minute).
6. **Step 1: Clean the data**, then **Overview**: **Generate all data** and **Generate all plots**. Every task also has its own page with its table, plots and choices.
7. Each result is in the project folder, one folder per task, with a log and a **run record** (`run_info.json`: version, script, arguments, checksums, settings).

Something wrong? The message on the page says what failed and what to do; the full details are in the task's log (Download the log).

## Updates

Like a desktop program, the application looks for a new version by itself: at most once a day, in the background, it asks GitHub for the latest release
(nothing about you is sent). When there is one, a window shows what's new with **Install and restart**, **Later** and **Skip this version**. Installing
never touches your projects or data (they are outside the application folder):

- a copy made with `git clone` is updated with git (a fast-forward to the release); it refuses, and changes nothing, if you edited the application's files;
- a copy downloaded as a ZIP downloads the new release; the current files are backed up first (your settings folder, `updates/`);
- either way the new version's own tests run first, and if they fail the previous version is put back. Then the application restarts in a new window.

The footer has **Check for updates** and a switch for the automatic check. In a terminal: `python3 the_data_app.py update` (or `--check-only`).
Copies older than 0.4.0 have no updater: update them once by hand (`git pull`, or download the new ZIP).

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
| macOS | double-click **`The Data Application.app`** (first time: right-click, Open). For the Dock, Launchpad or Applications: open it once from its folder, then drag it to the Dock, make an alias in Applications (Option + Command drag), or even copy it there: a copy finds the program through the folder remembered at the last start from it |
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
| **Tables, Main information, Production, Sources, Authors, Affiliations, Countries, Documents** | one page per sheet of the analysis (the tables and charts of a Biblioshiny-style analysis), see below |

A task needs the cleaned data (step 1); a task that needs another sheet (for example *Author summary* needs *Authors*) generates it first by itself.

**A sheet page** shows: what the sheet is; **Generate data** (or *again*); one **Generate plot** button for each plot of the sheet (only where a chart makes sense); the **data table**
(50 rows per page, with a tab for each extra table, such as the parameters of the fitted curve); the **plots** with PNG and SVG downloads; and buttons to download the CSV and the log or to show the folder.
Every run is logged in the sheet's folder (`<Sheet>_log.txt`).

**Settings: Python environment.** Choose **Use the shared venv** (recommended): one virtual environment for all projects, kept in the application's
settings folder (macOS `~/Library/Application Support/The Data Application/venv`), so it is installed only once (about 200 MB) and deleting a project never
removes it; it is made and filled from `requirements.txt` the first time, with the progress shown. Or **Use a venv I already have** (type its folder, or
Browse; missing packages are installed there on request). A project that still has its own `.venv` from an earlier version offers a button to delete it. A project made before a package was needed (for example matplotlib, for the plots) shows
**Install the missing packages**; until then cleaning and tables work, plots wait.

**Settings: Main data.** Press **Choose the Scopus CSV...** and pick the file. It is **copied into the project's `data/raw/`**; your original is never touched or moved.
Choosing a new file makes the earlier cleaned data "out of date" until you clean again.

## The sheets and plots

| Group | Sheets (plot = has a chart) |
|---|---|
| Tables | Authors, Affiliations, Countries, References, Author summary |
| Main information | Main information (plot: documents by type), Document types, Languages and Open access (pies), Subject areas (pie and bar chart; needs the Scopus Source List) |
| Production | Annual production (2 plots: with total citations, and with a log trend line), Average citations per year, Life cycle (plots) |
| Sources | Top sources (plot), Documents per source, Bradford's law (plot), Publishers (treemaps of the largest publishers' sources), Bradford core: who publishes there (3 plots per kind: countries, authors, institutions; the first is a population pyramid, core papers left and other papers right), Source impact (plot), Sources over time (plot) |
| Authors | Authors over time (plot), Lotka's law (plot), Author impact (plot), Authors: radial chart (plot: one bar per author, length = fractional score, colour = country) |
| Affiliations | Top affiliations (plot), Affiliations over time (plot) |
| Countries | Corresponding authors' countries (plot), Countries' production and citations (2 plots), Country collaboration pairs (plot), Country collaboration chord (chord diagram) |
| Documents | Word cloud of the keywords (plot), Most cited documents (plot) |

Each sheet is one Python file (`steps/sheets/<Sheet>/<Sheet>.py`) and each plot one more (`<Sheet>_plot.py`); the application copies the script into the project's folder `<Sheet>/` and runs it there with the project's Python,
so the folder of a project also holds the scripts and results of every sheet. The scripts are readable on their own: a header says what the sheet is, the Excel method it follows, its input and its output.
Year axes adapt to the data and you choose the range. The plots of production, citations, life cycle and "over time" (sheets 03, 04, 05, 11, 14, 18, 21) and the three burst strips draw about 10 round ticks
whatever the span, shade years after the current year as early access, and by default start where 1% of the papers have been reached (the hidden years and their paper count are named in the axis label).
Which years are drawn is set once for the project (Settings, **Years in the plots**: the last 10 or 5 complete years, all years, or years you choose), and each of those
sheet pages can override it in **Your choices** (the project's years, all years, or a first and last year). The choice cuts only the picture, never the table. The helpers (`year_args`, `year_window`, `year_label`, `year_axis`, `year_rows`) are a short block inside each of those scripts, because each script must run on its own
(by hand: `python3 03_Annual_Production_plot.py --from-year 1990 --to-year 2025`). Options marked `"for": "plot"` in `app/sheets.py` go to the plot script only; the sheet's data is not made again for them.
Papers without a source title are left out of the source sheets.

## The report (written with an AI model)

The **Report** page (menu: Project, Report) writes the results chapter of your thesis or paper as **LaTeX**, in the project's folder `Report/`:
one file per figure and per table in `Report/results/`, so you drop one by deleting its file. Every figure and table gets three paragraphs:

1. **What the plot or table is**, why it matters and its limitation in one or two sentences. This text is the same for every study, so it ships with
   the application (`steps/report/about.json`) and costs nothing.
2. **The analysis** of your numbers, and 3. **a short conclusion** (2 to 4 sentences): written by the AI model you choose.

**Set it up once** in Settings, *AI writing (for all projects)*: choose the provider (**Anthropic Claude** or **Google Gemini**), paste your API key and
choose a model from the list the provider sends. On macOS the key is kept in the **Keychain**; on Windows and Linux in a file in your settings folder
that only you can read (`ai_keys.json`). The key is never written into a project, a log or a command line. An environment variable
(`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) also works. The provider charges you for its use: the page shows how many calls a run needs and a rough
number of tokens before you start.

**What the model sees:** only the summary tables of the sheet (their first rows), the notes its scripts printed (for example the fitted parameters),
the main information of the data set, one line you write about the study and, if you tick it, the plot picture. Never your export.

**Safe for your own writing:**
- `report_manifest.json` remembers every file the application wrote. A file **you edited** is never written again; a file **you deleted** stays
  deleted (its tick is removed); a file whose data, model and text have not changed is kept without asking the model again (no cost).
- Every number in the model's text is looked up in the data it was given. Numbers it computed or invented are listed in `report_check.txt` and in a
  `% CHECK` line at the top of the file, and shown on the page: check them before you submit.
- **Write without AI** writes paragraph 1 and the figure or table, and leaves the analysis to you.

**Template:** the default report (`Report/report.tex`, yours to edit), or **your own LaTeX template folder** (a university thesis format, a journal
class): it is copied into `Report/`, the packages the figures and tables need are added, and `\input{results_chapter}` is put before the
bibliography (move it where the results belong). Files it replaces are moved to `Report/_backup_<date>/` first. If biblatex is set to biber and
biber does not run on the computer, the copy is switched to bibtex. **Build the PDF** runs latexmk (or pdflatex) if LaTeX is installed; otherwise
upload the `Report` folder to Overleaf. The folder holds its own copy of the plot pictures, so it can be sent on its own.

## What the cleaning does

`steps/01_clean_data.py` is an ordinary Python file (it can be run by hand and read on its own). It follows the steps of a documented Power Query cleaning, in order:

| Step | What |
|---|---|
| A | text hygiene on every column: repair garbled accents (`UniversitÃ¤t` becomes `Universität`), remove control characters, decode HTML entities, trim spaces |
| 1 | keep records with a valid EID (`2-s2.0-...`), one row per EID |
| 2 | count the references of each paper, drop the long References column |
| 3 | remove records with no authors |
| 4 | remove duplicate papers (same title, ignoring case and punctuation; the earliest year and the most cited one is kept) |
| 4b | remove duplicate papers with the same DOI (the same paper indexed twice under two titles), kept in the same order |
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
  steps/sheets/<Sheet>/      the scripts of the sheets (<Sheet>.py) and of their plots (<Sheet>_plot.py)
  steps/report/              the report: make_report.py, about.json (paragraph 1 of every figure and table), template/report.tex
```

Each project is a folder where **you** put it:

```
<the folder you chose>/<project name>/
  project.json               the project's settings: name, venv, main data, results
  data/raw/                  the copy of the main data
  data/source_list/          the Scopus Source List you chose for the sheet Subject areas (the newest file is used)
  01_Clean_Data/             results of step 1: cleaned CSV, report, log of the run, copy of the script
  Authors/, 03_Annual_Production/, ...   one folder per sheet that has been generated: its script, CSV, log, and the plot (.png/.svg) if made
  Report/                    the report: report.tex (or your template), results_chapter.tex, results/<one file per figure and table>.tex,
                             figures/, report_check.txt (numbers to check), report_log.txt, report_manifest.json (what the application wrote)
  (no venv: all projects share <settings folder>/venv; a .venv here is from before 0.9.9 and can be deleted in Settings)
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
python3 the_data_app.py env  -p "My project" --create # the shared venv; or: --venv /path/to/venv
python3 the_data_app.py data -p "My project" export.csv
python3 the_data_app.py clean -p "My project"
python3 the_data_app.py run -p "My project"            # every sheet's data; add --plots for every plot
python3 the_data_app.py years -p "My project" last10   # years in the plots: last10, last5, all, custom --from 2005 --to 2020; --roll-forward
python3 the_data_app.py sample --location ~/Documents  # a project with made-up data, to try the application
python3 the_data_app.py status -p "My project"
python3 the_data_app.py --version
python3 the_data_app.py gui --no-window               # start the server only and print its address
```

## Sharing it with friends

The application is on GitHub: https://github.com/varunjha089/The-Data-Application (MIT licence). Send that link, or send the application folder as it is: it contains no projects, data, settings or environments of yours (those are in the folders you chose and in your user settings folder).
Your friend opens the application, creates a project in a folder of their choice, and the window sets everything up on their computer. (`CLAUDE.md` is the guide for
developers.) On a Mac, a downloaded copy of the `.app` is blocked once by Gatekeeper: right-click it, choose Open, confirm. To share a **project** (not the application),
copy its folder (without an old `.venv`, if it has one) and open it on the other computer with "A project that is not in the list".

## What comes next

More analyses will be added the same way: a script in `steps/sheets/` (or `steps/`), an entry in `app/sheets.py`, and it appears in the menu with its table and plot button.
Working rules for developers are in `CLAUDE.md`; `python -m unittest discover -s tests` must pass.

## More about the sheets

- **Packages**: a package a script needs (matplotlib, numpy, openpyxl, pillow) is installed into the project's environment the first time it is needed (internet needed); Settings also has a button for it.
- **World map**: documents of every country and a map of the most productive ones (matplotlib only; Natural Earth polygons, India worldview, in `world_countries_india_view.json`).
- **Your choices**: a sheet can declare options (`_OPTIONS` in `app/sheets.py`); its page shows them above the buttons, they are saved in `project.json` and passed to the
  script as arguments (how many authors, countries, sources or institutions; keep ties; burst settings; years). A plot of a sheet with data options makes its data again first.
- **Timelines** (bubbles) for sources, authors, institutions and countries, with a "top n" choice; **Source impact** has eight plots to choose from (bars, two pyramids,
  bubbles, dumbbell, heat map, citations per paper, m-index against first year); **Country radar** (five indicators); **Languages**, **Document types** and **Open access** pies.
- **Word cloud** of the keywords (Author Keywords, Index Keywords or both): a word's size follows the number of papers that use it; blue, violet, green,
  pink, red, teal and indigo (no yellow or orange). Spelling variants are merged using only what the data shows: plurals ("llms" and "llm") and an
  abbreviation in brackets with its full name ("retrieval augmented generation (rag)" also makes "rag" count as "retrieval augmented generation"); the table's
  column Variants lists what was merged (switch it off on the page). Choose how many keywords are drawn, and leave out the most used ones (the words of
  your search, which are in nearly every paper); they stay in the table and are named under the picture. Drawn without any extra package.
- **Log trend line** (Annual production): the documents per year as bars shaded from light yellow to dark red, with the exponential ln(documents) =
  a + b x year fitted by least squares, its R² and the growth per year (e^b - 1). Years without papers cannot be fitted; years after the last complete
  year are still being indexed, so they are drawn hatched and left out of the fit.
- **Publishers**: the export writes one publisher in many ways ("MDPI", "MDPI AG" with an address and an e-mail, "Multidisciplinary Digital Publishing
  Institute (MDPI)"), so the names are merged first: e-mail addresses are removed, the large publishers are recognised by a word of their name (Elsevier with
  Academic Press; Springer Nature with Nature Research and BioMed Central; Wiley with Blackwell; Taylor & Francis with Routledge and CRC Press; IEEE; ...),
  and the company form at the end (Inc., Ltd, B.V., ...) is dropped; the table lists the names merged into each publisher. A source belongs to the
  publisher named most often on its papers. The plot draws one treemap per publisher with the most documents (choose how many, and how many sources
  each shows; the rest form "Other sources"): every source is a rectangle sized by its documents, labelled with its documents and its share of the
  publisher. A name that does not fit is replaced by the source's abbreviation. Papers without a source title are not drawn; their number is printed in the plot's log.
- **Subject areas**: documents by Scopus subject area, as in Scopus's "Documents by subject area" chart. Scopus classifies sources, not papers, and the CSV
  export has no subject area, so the sheet looks each paper's source up in the **Scopus Source List**, the Excel file Elsevier publishes free of charge
  ([Scopus content page](https://www.elsevier.com/products/scopus/content/content-policy-and-selection), "the Scopus Source List"). Choose it once on the
  sheet's page; it is copied into the project's `data/source_list/`. A paper is matched by ISSN, then by source title, then by ISBN or title of a conference
  proceedings volume; it takes every subject area of its source (the first two digits of its ASJC codes), so it can count in several areas, as in Scopus.
  The pie shows the shares of all (paper, area) pairs, the top areas and "Other", like Scopus; the bar chart shows papers per area and the share of
  matched papers. Papers whose source is not in the list (mostly books, which the list does not cover) are counted as "Not matched" and named under the
  plots; `Subject_Areas_papers.csv` says how each paper was matched. Without a source list the sheet is skipped (no error). The sample project brings a
  small made-up list, so the sheet can be tried there.
- **Bursts** for countries, authors and institutions (Kleinberg burst detection on the yearly counts, like CiteSpace's burst history): table, year strip and an HTML page.
  A burst in the last year only is an edge effect.
- **Bookmarks**: the dot of a menu item can become a red, green, violet or orange star (saved in `project.json`).
- **Name rules** (`steps/common/names.py`): known countries and their aliases (USA, FRG, a US state + ZIP), the institution of an address without its department, one name
  per spelling, parent organisations. An address with no recognisable country gives no country rather than a wrong one.
- **Merged searches**: when the export carries `Query_IDs` / `N_Queries` (several Scopus searches merged), the Clean page has **Searches to drop** (papers found only by a
  noise search, e.g. `Q3`), and the sheet **Topic_Slices** cuts the analysis by search, with term trends and an optional gap audit. What it cuts and looks for is set in
  `topic_slices.json` in the project folder (written with automatic choices on the first run; format at the top of `steps/sheets/Topic_Slices/Topic_Slices.py`;
  an example for the sample project in `steps/sheets/Topic_Slices/examples/`). Without Query_IDs (a single search) the sheet is skipped.
- The code is a git repository (`git log`); only the application is under git, never projects or data.

## Version 0.10.2 (2026-10-26)

- **Every table can go into the report:** each table picture (Author summary, Affiliations, ...) has its tick box now; tables without
  their own first paragraph get a general one. Author summary has its own.
- **Write with AI (or without) also builds the PDF** when LaTeX is installed, so one click gives the finished report; the grey
  *Build the PDF* button says why it is grey (write the report first).

## Version 0.10.1 (2026-10-26)

- **A project folder you moved is found again in one click:** a project shown as *folder not found* now has **Find the moved folder...**;
  choose its new folder and the list points there (same place in the list; the project itself is not changed).

## Version 0.10.0 (2026-10-26)

- **New sheet: Authors: radial chart** (group Authors), in the style of the "Best Countries" overall-rankings chart: one bar per author
  around a circle, sorted clockwise by rank; the length is the author's **fractional score** (each paper counts 1, shared by its authors),
  the colour the **country** the author publishes from (read from the addresses of the papers), and each bar carries the rank, the name,
  the fractional score and the number of publications. Inside the ring the authors are grouped by rank (1-10, 11-20, ...). Choose how
  many authors, ranking by fractional score or by publications, a dark or light background, and how many countries get their own colour.

## Version 0.9.9 (2026-10-26)

- **One shared venv for all projects.** Instead of a venv in every project (about 200 MB each), the projects share one, kept in the
  application's settings folder (macOS `~/Library/Application Support/The Data Application/venv`): it is installed once, and deleting
  a project never removes it. Settings, *Use the shared venv*, makes it the first time. A project that still has its own `.venv` shows
  how much space it takes and a button to delete it once the project uses the shared venv.

## Version 0.9.8 (2026-10-26)

- **Fix: using a venv you already have.** The application followed the link inside the venv (`bin/python3`) to the system's Python, so
  the packages were installed into Homebrew's Python, which refuses that ("externally-managed-environment"). The venv's own Python is
  used now. If a system Python is ever chosen, the application says so plainly and points to *Use the shared venv* instead of showing
  pip's error.

## Version 0.9.7 (2026-10-26)

- **No title at the top of the plot pictures** (a report or paper gives each figure its own caption). The title is written in the plot's
  log instead (`title of <picture> (not drawn in the picture): ...`). Pictures with several panels keep their panel labels, such as
  "(a) MDPI". Settings, *Look of the plots*, has a tick box to draw the titles again. Generate the plots again to update the pictures.

## Version 0.9.6 (2026-10-26)

- **Rows in each table picture.** The number of rows is now set for the project (Settings, *Rows in table pictures*) and, if you
  want, for each table picture on its own (the box above it on its sheet's page; a sheet with several tables keeps a number per
  table). **Redraw all table pictures** in Settings draws every picture of the project again with these numbers, so the pictures
  made earlier with 50 rows become short at once. A table's own number also limits that table in the report.

## Version 0.9.5 (2026-10-26)

- **Rows in the table pictures: type any number.** Settings has a number box (0 = all rows, at most 1000) instead of the choices
  20 / 50 / 100 / all, and every sheet page has its own box with **Redraw** next to the table picture (for example 10 rows for
  *Documents per source*). A sheet's own number also limits its table in the report; "use the project's" goes back to the Settings value.

## Version 0.9.4 (2026-10-26)

- **A tick box above every plot and table** on the sheet pages puts it in the report or leaves it out, so you can decide while you look
  at it; it is the same choice as the list on the Report page.
- The names in the Report page's list are readable in the dark theme (plain text colour, underlined).

## Version 0.9.3 (2026-10-26)

- **Report names on the sheet pages:** every plot and table picture, and the data table, now carries the name it has in the report
  (for example *Figure: Share of the document types*, report file `fig_document_types_pie.tex`), so the page, the Report list and the
  LaTeX files are easy to match. On the Report page, a figure's or table's name opens its sheet.

## Version 0.9.2 (2026-10-25)

- **Publisher treemaps:** the panel titles are one line again; the number of papers without a source title (not drawn) is printed in the
  plot's log instead of under each title.

## Version 0.9.1 (2026-10-25)

- **The publisher treemaps are drawn about 8 times faster** (28 s down to under 4 s on a data set of 1,149 papers; at 600 dpi about 5 s instead of
  minutes). The largest label that fits each rectangle is now computed instead of searched size by size; small rectangles sometimes get their
  name where they had only numbers before.
- **Updating from 0.8.0 works again.** In 0.9.0 the update tests ran inside an update's own check, so the check failed and the update was
  undone; they are skipped there again.

## Version 0.9.0 (2026-10-25)

- **New page: Report.** Writes the results chapter as LaTeX, one file per figure and table, with three paragraphs each: what the plot or table is
  and its limitation (the application's own text, no cost), and the analysis and conclusion written by an AI model you choose.
- **AI writing in Settings:** Anthropic Claude or Google Gemini, your own API key (kept in the macOS Keychain, or in a file only you can read on
  Windows and Linux; never in a project or a log), and the model chosen from the provider's own list. Only the summary tables of the sheets (and, if
  you tick it, the plot pictures) are sent.
- Your edits are kept: a file you changed or deleted is never written again, and unchanged items are not asked again. Every number in the model's
  text is checked against the data; the ones not found are listed for you to check.
- Your own LaTeX template folder can be used (the needed packages and the results chapter are added to the copy); **Build the PDF** with latexmk
  or pdflatex. **Write without AI** gives the same files with the analysis left open.

## Version 0.8.0 (2026-10-25)

- **New plot: annual production with a log trend line** (sheet Annual production). Bars shaded from light yellow to dark red by year, with their
  numbers, and the fitted exponential with its equation, R² and the growth per year. The year still being indexed is left out of the fit.
- **New sheet: Publishers** (group Sources). The many ways the export writes one publisher are merged ("MDPI", "MDPI AG ...", "Multidisciplinary
  Digital Publishing Institute (MDPI)" are one publisher), then one treemap per largest publisher shows how its documents are spread over its
  sources. Choose how many publishers (default 4) and how many sources per treemap (default 12). No new package is needed.

## Version 0.7.0 (2026-10-25)

- **New sheet: Word cloud of the keywords** (group Documents). Choose Author Keywords, Index Keywords or both, how many words are drawn, and how many of
  the most used keywords to leave out (your search terms). Plurals and abbreviations in brackets are merged into one keyword ("rag", "retrieval augmented
  generation (rag)" and "retrieval augmented generation" are one); the table lists the variants. Colours: blue, violet, green, pink, red, teal, indigo.
  A less used keyword is never drawn larger than a more used one. No new package is needed.

## Version 0.6.4 (2026-10-25)

- **The cleaning no longer stops at "no DOI appears twice"** when Scopus lists one paper twice under two titles (for example a conference paper once
  with "... Demonstration Track" added to its title). New step 4b removes papers whose DOI was already seen, keeping the earliest year and then the most
  cited one, as step 4 does for titles. Exports without such pairs are cleaned exactly as before.

## Version 0.6.3 (2026-10-25)

- **The buttons work again after a task.** After setting up the Python environment of a new project (or any other task), "Choose the Scopus CSV..." and
  the other buttons stayed grey until the window was reloaded. They are now enabled as soon as the task ends.

## Version 0.6.2 (2026-10-25)

- **Every number in the tables has at most 2 decimal places** (Mean Citations per Document and per Year, TC per year, m index, MCP ratio, the
  Life cycle and Lotka parameters, ...), in the CSV files, the tables in the window and the table pictures. Generate the data again to see it.
- Shares that were proportions between 0 and 1 are now percentages, so that 2 decimals keep small values: Bradford's law has **Cumulative Share (%)**
  (Zone 1 up to 33.33 %), Lotka's law has **Authors (%)** and **Lotka β = 2 (%)**. The Lotka plot computes its points from the counts, so it is exact.
- The numbers written on the Life cycle, Lotka and Bradford plots (r, C, R²) also have 2 decimals.

## Version 0.6.1 (2026-10-25)

- **Generate all no longer stops at Topic slices** on a data set of one search. Topic slices needs the columns Query_IDs and N_Queries (merged Scopus
  searches); without them, or without a References table, the sheet is now skipped with a message, like References and Subject areas, and the sheets
  after it (Most cited documents) are generated too.

## Version 0.6.0 (2026-10-25)

- **New sheet: Subject areas** (group Main information), the "Documents by subject area" chart of Scopus as a pie chart and a bar chart, with a table of
  every area. The Scopus export has no subject area, so the sheet asks for the **Scopus Source List** (a free Excel file from Elsevier; the page links to
  it): choose it once on the sheet's page and it is kept in the project. Each paper takes the subject areas of its journal, book series or conference;
  papers whose source is not in the list are counted as "Not matched". The number of areas with their own slice is a choice on the page (10 by default).
- A sheet can now ask for a file of yours (shown as a box above its choices); without it the sheet is skipped and **Generate all** goes on.

## Version 0.5.2 (2026-10-25)

- **Table pictures follow the years of the plots.** On a sheet with a year setting (the project's years, all years, or its own), the table picture shows
  the same years as the plot: the rows of a table with a Year column, or the year columns of a table whose columns are years (Countries, Authors,
  Affiliations over time). The title names the years ("Annual production (10 rows, 2016–2025)"); a Grand Total column is recounted over the years shown
  and called "Total 2016–2025". The CSV keeps every year. Generating the plot redraws these pictures, so a new year setting reaches them too.
- Table pictures are wide enough for their full title.

## Version 0.5.1 (2026-10-25)

- **The table picture is shown on the sheet page**, under *Plots and tables*, next to the plots, with its PNG / SVG links.
- **Generating a plot also draws the table pictures** when they are missing or older than the data (a project whose data was made before 0.5.0
  only needed its plot redrawn, and got no table picture).

## Version 0.5.0 (2026-10-25)

- **Every table also as a picture.** When a sheet's data is generated, each of its tables is saved as `<table>_table.png` and `<table>_table.svg` next to
  the CSV (the SVG keeps the text editable), and the sheet page offers *Download the table as a picture: PNG / SVG* under the table. The plots are unchanged.
  A long table is drawn with its first 50 rows and says so in its title ("first 50 of 928 rows"); choose 20, 50, 100 or all (up to 1,000) in Settings,
  *Look of the plots*. Cells are shown exactly as in the CSV. Drawn by `steps/common/table_image.py`, which can also be run by hand on any CSV.

## Version 0.4.1 (2026-10-25)

- **Fix: the cleaning stopped with `IndexError`** on exports where a correspondence address is empty (`; ; ;`): the country fill-in of 0.3.0 asked for
  the institution of an empty address. Empty addresses now simply have no institution. Found on a real 3,013-record export; a test covers it.
- **Life cycle: no invented ceiling.** When the S-curve has not turned yet (its inflection point lies after the fitted years), the growth is still
  accelerating and the data cannot say where it will level off: the plot now says so (with r and R2) instead of printing a meaningless K, peak and 90% year;
  the parameters table has a new row, Saturation visible (yes/no).
- **macOS: a copy of the `.app` outside the application folder works** (for Launchpad or Applications): it starts the program from the folder remembered at
  the last start from there, and explains what to do when that folder is unknown.

## Version 0.4.0 (2026-10-25)

- **Updates by itself** (see *Updates* above): daily check of the latest GitHub release, an update window with the release notes, install through git or
  the release ZIP with a backup, the new version's tests before it is kept, automatic rollback, restart. `update` command. The tests run real updates in
  throw-away copies (git, ZIP, a release that fails its tests, a copy edited by hand).

## Version 0.3.0 (2026-10-24)

- **Years in the plots** (Settings): *the last 10 complete years* (the default), *the last 5*, *all years*, or *years I choose*. A complete year is one that has ended:
  in October 2026 the last 10 complete years are 2016-2025 (2026 is still being indexed, early-access papers carry 2027). The years are worked out when you choose
  and then **saved**, so a plot does not change by itself next year; **Roll forward** works them out again. Every sheet with a year axis has the choice
  *the project's years / all years / the years below*. Production, the life cycle and the burst strips draw all years by default (their meaning needs the whole history);
  the others follow the project. The tables always keep every year.
- **Look of the plots** (Settings): text size, picture size, resolution (150 / 300 / 600 dpi), an extra **PDF** and/or **TIFF** next to every PNG, and a **colour-blind safe**
  palette (Okabe-Ito). The plot scripts are not changed: the application runs them through `steps/common/plotlook.py`, which changes only the picture; the command is in the log.
- **Run record**: every task folder has `run_info.json` (application version, script and its SHA-256, the exact arguments, the SHA-256 of the export and the cleaned data,
  the choices, the years, the look, Python and pandas versions), so every figure can be traced and made again. The Clean step has one too.
- **Clearer messages**: a wrong file (an Excel workbook, a Web of Science or RIS file, a CSV with semicolons, a file that is not UTF-8, missing columns) is refused with
  what to do; a task that stops says why in plain words (a missing column, a missing package, a file open in Excel, ...).
- **Sample project**: made-up Scopus-format data (`app/sample.py`) to try everything without an export; also used by the tests.
- **Tests**: `python -m unittest discover -s tests -v` (the full run makes the sample project and every sheet and plot; `TDA_QUICK=1` for the fast part).
- **Missing countries**: an address written without its country (`Wuhan University, Wuhan`) gets the country of the same institution elsewhere in the data, when at least
  2 and 2/3 of that institution's addresses name the same country. The cleaning report counts them; the table is `01_Clean_Data/institution_countries.csv`; the Affiliations
  table says where each country came from (Country Source). It can be switched off on the Clean page.
- **Parent organisations**: Affiliations has a Parent Organisation column (the institutes of the Chinese Academy of Sciences, CNRS, CSIC, CNR, Max Planck, Helmholtz, CSIR,
  ICAR, ISRO, CSIRO, NASA, USGS, ... together; the list is `PARENTS` in `steps/common/names.py`). *Top affiliations* can count by institution or by parent organisation.
- **Life cycle**: the S-curve is fitted on complete years only (by default up to last year; a choice on the page). The current year and early-access years are drawn hollow
  and kept in the table (column In Fit).
- **Bradford core**: each actor also gets the normalised citation score (citations divided by the mean of the papers of the same year: 1 = average) inside and outside the
  core, and the mean h-index of the sources it publishes in; a fourth picture per kind (`core_<kind>_ncs`) compares core and other papers corrected for age.
