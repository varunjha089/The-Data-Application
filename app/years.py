"""The years the plots of a project draw (standard library only). One setting for the whole project, saved in project.json as
{"preset", "from", "to", "set_on"}; a sheet can still choose all years or its own range (app/sheets.py, option "years").

The presets are worked out once, when they are chosen, and the result is SAVED: "the last 10 complete years" chosen in October 2026 is 2016-2025, and it stays
2016-2025 when the project is opened next year, so a plot made for a paper does not change by itself. "Roll forward" works the preset out again for today.
A complete year is a year that has ended (the current year is still being indexed and early-access papers carry next year's date), capped at the last year
of the data, so an export that ends in 2020 gets 2011-2020."""
import csv
from datetime import date

PRESETS = {"last10": "The last 10 complete years", "last5": "The last 5 complete years", "all": "All years (from the year 1% of the papers is reached)",
           "custom": "Years I choose"}
DEFAULT = "last10"
_cache = {}


def data_years(project):
    """(first, last) year of the cleaned data, or None when it is not cleaned yet"""
    f = project.clean_file
    if not f.exists():
        return None
    key = (str(f), f.stat().st_mtime)
    if key not in _cache:
        lo = hi = None
        with open(f, newline="", encoding="utf-8-sig") as fh:
            rd = csv.reader(fh)
            head = next(rd, [])
            if "Year" in head:
                i = head.index("Year")
                for row in rd:
                    try:
                        y = int(float(row[i]))
                    except (ValueError, IndexError):
                        continue
                    lo, hi = (y, y) if lo is None else (min(lo, y), max(hi, y))
        _cache[key] = (lo, hi) if lo is not None else None
    return _cache[key]


def last_complete_year(today=None):
    return (today or date.today()).year - 1


def resolve(preset, today=None, last_data=None, lo=0, hi=0):
    """(first, last) year of a preset; (0, 0) = all years (the plot works out its own start); custom keeps lo and hi (0 = automatic)"""
    if preset in ("last10", "last5"):
        end = last_complete_year(today)
        if last_data:
            end = min(end, last_data)
        return end - (9 if preset == "last10" else 4), end
    if preset == "custom":
        lo, hi = int(lo or 0), int(hi or 0)
        return (hi, lo) if lo and hi and lo > hi else (lo, hi)
    return 0, 0


def set_window(project, preset, lo=0, hi=0, today=None):
    """choose a preset (or custom years) for the project and save the years it gives today"""
    if preset not in PRESETS:
        raise ValueError(f"unknown choice {preset!r}")
    if preset == "custom":
        for v in (lo, hi):
            if v and not 1900 <= int(v) <= 2100:
                raise ValueError("A year must be between 1900 and 2100 (or 0 for automatic).")
    dy = data_years(project)
    first, last = resolve(preset, today, dy[1] if dy else None, lo, hi)
    w = {"preset": preset, "from": first, "to": last, "set_on": (today or date.today()).isoformat()}
    project.update(year_window=w)
    return w


def get(project):
    """the project's window; the first time it is asked for, the default (the last 10 complete years) is worked out and saved, so that it stays fixed"""
    saved = project.load().get("year_window")
    if saved and saved.get("preset") in PRESETS:
        return saved
    return set_window(project, DEFAULT)


def roll_forward(project, today=None):
    """work the saved preset out again for today (a custom range is kept as it is)"""
    w = get(project)
    return set_window(project, w["preset"], w["from"], w["to"], today)


def info(project, today=None):
    """what the Settings page shows: the saved window, the years of the data, and what the preset would give today"""
    w = get(project)
    dy = data_years(project)
    now = resolve(w["preset"], today, dy[1] if dy else None, w["from"], w["to"])
    return {**w, "presets": PRESETS, "data": list(dy) if dy else None, "today": list(now),
            "can_roll": w["preset"] in ("last10", "last5") and list(now) != [w["from"], w["to"]]}


def text(w):
    """'2016-2025' or 'all years'"""
    if not w["from"] and not w["to"]:
        return "all years"
    return f"{w['from'] or 'start'}-{w['to'] or 'last year'}"
