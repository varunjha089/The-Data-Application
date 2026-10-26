"""The look of a project's plots (standard library only): text size, figure size, resolution, extra file formats and a colour-blind safe palette.
Saved in project.json as "plot_look". With the defaults the plot scripts run as they are; otherwise the application runs them through
steps/common/plotlook.py, which changes only the look (never the data) and is copied into the project so the command in the log can be run again."""

DEFAULT = {"text": 1.0, "size": 1.0, "dpi": 0, "pdf": False, "tiff": False, "palette": "standard", "table_rows": 50}
TABLE_ROWS = (20, 50, 100, 0)              # suggested rows in a table picture; any number from 0 (= all, at most 1000) to 1000 is accepted
LIMITS = {"text": (0.6, 2.5), "size": (0.6, 2.5)}
DPI = (0, 150, 300, 600)                       # 0 = as the script chooses (150, the Bradford plot 300)
PALETTES = {"standard": "Standard colours", "colourblind": "Colour-blind safe (Okabe-Ito)"}


def get(project):
    saved = project.load().get("plot_look") or {}
    out = dict(DEFAULT)
    for k in ("text", "size"):
        try:
            lo, hi = LIMITS[k]
            out[k] = round(min(max(float(saved.get(k, DEFAULT[k])), lo), hi), 2)
        except (TypeError, ValueError):
            pass
    try:
        out["dpi"] = int(saved.get("dpi", 0)) if int(saved.get("dpi", 0)) in DPI else 0
    except (TypeError, ValueError):
        pass
    out["pdf"], out["tiff"] = bool(saved.get("pdf")), bool(saved.get("tiff"))
    out["palette"] = saved.get("palette") if saved.get("palette") in PALETTES else "standard"
    try:
        out["table_rows"] = min(max(int(saved.get("table_rows", 50)), 0), 1000)
    except (TypeError, ValueError):
        pass
    return out


def save(project, values):
    cur = {**(project.load().get("plot_look") or {}), **{k: v for k, v in (values or {}).items() if k in DEFAULT}}
    project.update(plot_look=cur)
    return get(project)


def table_rows(project, sheet, csv=None):
    """rows drawn in a table picture: the picture's own number (set above it on the sheet page), else the sheet's (0.9.5), else the project's (Settings)"""
    by = project.load().get("table_rows_by_sheet") or {}
    for key in ([f"{sheet}/{csv}"] if csv else []) + [sheet]:
        if key in by:
            try:
                return min(max(int(by[key]), 0), 1000)
            except (TypeError, ValueError):
                break
    return get(project)["table_rows"]


def table_rows_own(project, sheet, csv=None):
    """True when the table picture (or its sheet) has its own number instead of the project's"""
    by = project.load().get("table_rows_by_sheet") or {}
    return (csv is not None and f"{sheet}/{csv}" in by) or sheet in by


def set_table_rows(project, sheet, rows, csv=None):
    """the table picture's own number of rows (csv given) or the sheet's; None = follow the project's again"""
    by = dict(project.load().get("table_rows_by_sheet") or {})
    keys = [f"{sheet}/{csv}"] if csv else [sheet]
    if rows is None:
        keys.append(sheet)                                       # back to the project's number: the sheet's own number goes too
        for k in keys:
            by.pop(k, None)
    else:
        by[keys[0]] = min(max(int(rows), 0), 1000)
    project.update(table_rows_by_sheet=by or None)
    return table_rows(project, sheet, csv)


def args(project):
    """the arguments of steps/common/plotlook.py, or [] when the look is the default (the script then runs on its own)"""
    lk = get(project)
    out = []
    if lk["text"] != 1.0:
        out += ["--text", str(lk["text"])]
    if lk["size"] != 1.0:
        out += ["--size", str(lk["size"])]
    if lk["dpi"]:
        out += ["--dpi", str(lk["dpi"])]
    formats = [f for f in ("pdf", "tiff") if lk[f]]
    if formats:
        out += ["--formats", ",".join(formats)]
    if lk["palette"] != "standard":
        out += ["--palette", lk["palette"]]
    return out
