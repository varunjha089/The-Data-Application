# FUTURE_PLAN.md: ideas for The Data Application

Ideas we will do later, in the order the user gave them. Nothing here is built yet. When an idea is done, move it to `PLAN.md` (what was decided, what was checked and what was NOT) and mark it here as done.

## 1. Table as a picture (PNG / SVG), with the columns and the top n chosen by the user

Every task page shows a data table. Add a button "Table as picture" that writes the table as a PNG and an SVG, so it can go straight into a paper or a slide.

- **The user chooses before generating:**
  - **top n:** how many rows (the first n rows of the table, in the order of the table, which is usually largest first). Same kind of input box as "Your choices" on the pages that have one; the value is saved in the project until it is changed.
  - **columns:** which columns appear (tick boxes, all ticked at first), and their order if possible.
- **Which tables:** every CSV of every task (the pages that have two CSVs, such as Country collaboration, get one picture per CSV, chosen with the same tabs as the table).
- **Output:** into the task's own folder, named after the CSV (for example `16_Author_Impact_table.png` and `.svg`), plus a note in the task log of which columns and which n were used.
- **Design:** large plain text (the user wears spectacles), header row shaded, numbers right aligned, long text shortened with "...", the title and "top n of N rows" as a caption; light background so it prints well.
- **Same format as the rest of the application:** one script in `steps/` (needs only pandas and matplotlib), taking `--input`, `--output`, `--top`, `--columns`; the application only calls it. The column names and n are passed as arguments, never hard-coded.
- **To decide when we build it:** how the user picks the columns in the window (tick boxes under the table, or a small "Table picture" panel on the page).

## 2. Conferences held at least n times (built once, taken out of the application, to come back later)

**Idea:** a task "Conferences (editions)" that shows only the conferences held at least n times (n chosen by the user, default 3), with two plots: a bubble timeline (one row per conference, a bubble for every conference year, size = papers, darkness = citations per year) and bars with the number of editions of each conference.

**Status:** built and checked on the January data (2026-10-22), then removed from the menu at the user's request. The finished code is in `future/Conferences/` (`Conferences.py` makes `Conferences.csv` and `Conferences_timeline.csv`, `Conferences_plot.py` makes `conference_timeline` and `conference_editions_bars`). To bring it back: move the folder to `steps/sheets/Conferences/`, add the entry to `app/sheets.py` (group Sources; plots `conference_timeline`, `conference_editions_bars`; options `min_editions` number default 3 with argument `--min-editions`, `by_source` check default off with argument `--by-source`) and the name to `Workbook_Sheets/run_all.py`. A copy of the old outputs may still be in a project's `Conferences/` folder.

**How it worked:**
- A paper belongs to a conference when its export has a Conference name and a Conference date. Edition = one conference year (the year at the start of the Conference date).
- Series (what counts as "one conference"): by default the Conference name cleaned of ordinal (23rd), year, Roman numerals (XVIII), "Vol. 3" and the subtitle after ":"; or, with the tick box, the Source title (for example Proceedings of SPIE).
- January data: cleaned name, n = 3 gave 3 conferences (IGARSS 7 editions, Remote Sensing for Agriculture, Ecosystems, and Hydrology 4, Remote Sensing and Geoinformation of the Environment 3); n = 2 gave 8; by source title with n = 3 gave 6 (Proceedings of SPIE 9, IGARSS 7, ISPRS Archives 5, IOP Conference Series 5, ISPRS Annals 3, Journal of Physics Conference Series 3).

**Open points before bringing it back:**
- Decide the default grouping. By cleaned name is strict (the many different SPIE conferences stay apart, so few reach 3 editions); by source title gives the longer list the user first expected.
- The name cleaning is rule based and was checked only on the January data: on another export, read `Conferences.csv` for names that should have been merged.
- Conference papers without a conference date cannot be placed in an edition and are left out (39 of the 135 had no Source title, but all had a conference date).
