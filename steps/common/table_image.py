"""common/table_image.py : a picture of a table (PNG and SVG), for papers and slides; the CSV stays the full, exact data.

    python3 table_image.py <table.csv> [--rows 50] [--title "Annual production"] [--from-year 2016 --to-year 2025]

Writes <table>_table.png and <table>_table.svg next to the CSV. The cells are shown exactly as the CSV has them (no rounding, no reformatting);
very long cells are shortened with "..." (the CSV keeps them whole). Only the first --rows rows are drawn (0 = all, at most 1000); the title then
says "first N of M rows". --from-year / --to-year (0 = open) keep the years the plots draw: the rows whose Year column is in the range, or, in a
table whose columns are years (1994, 1995, ...), those columns only; the title names the years. Numbers are right-aligned, text left-aligned, the header is bold and every other row is shaded. The SVG keeps the text
as text, so it can be edited. Needs pandas and matplotlib (the project's environment has them).
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

MAX_ROWS = 1000
MAX_CHARS = 60                     # a longer cell is shortened in the picture
FONT = 10
CHAR_W = 0.083                     # inches per character at FONT (DejaVu Sans, average)
ROW_H = 0.30


def is_number(s):
    try:
        float(str(s).replace(",", ""))
        return str(s).strip() != ""
    except ValueError:
        return False


def short(s, n=MAX_CHARS):
    s = "" if pd.isna(s) else str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def in_range(y, lo, hi):
    try:
        y = int(float(y))
    except ValueError:
        return True                                   # not a year (a total row, an empty cell): kept
    return (not lo or y >= lo) and (not hi or y <= hi)


def draw(csv_path, rows=50, title=None, lo=0, hi=0):
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    years = ""
    if lo or hi:
        year_cols = [c for c in df.columns if c.strip().isdigit() and len(c.strip()) == 4]
        if "Year" in df.columns:
            df = df[df["Year"].map(lambda y: in_range(y, lo, hi))]
        elif len(year_cols) >= 3:
            kept = [c for c in year_cols if in_range(c, lo, hi)]
            df = df[[c for c in df.columns if c not in year_cols or c in kept]].copy()
            for tot in [c for c in df.columns if c.strip().lower() in ("grand total", "total")]:
                # the total of the file counts every year: recount it over the years shown, and say so
                nums = df[kept].apply(lambda col: pd.to_numeric(col.str.replace(",", ""), errors="coerce")).fillna(0)
                df[tot] = nums.sum(axis=1).map(lambda v: f"{v:g}")
                df = df.rename(columns={tot: f"Total {lo or 'start'}–{hi or 'last year'}"})
        if "Year" in df.columns or len(year_cols) >= 3:
            years = f", {lo or 'start'}–{hi or 'last year'}"
    total = len(df)
    n = total if rows <= 0 else min(rows, total)
    n = min(n, MAX_ROWS)
    show = df.head(n)
    cols = list(show.columns)
    cells = [[short(v) for v in r] for r in show.itertuples(index=False)]
    # characters per column: the longest cell, or the header (bold text is about 15% wider), plus padding; never narrower than 6
    widths = [max(6, round(len(short(c)) * 1.15), *[len(r[i]) for r in cells]) + 3 for i, c in enumerate(cols)]
    numeric = [n > 0 and all(is_number(r[i]) or r[i] == "" for r in cells) and any(is_number(r[i]) for r in cells) for i in range(len(cols))]
    tw = sum(widths) * CHAR_W                          # width of the table itself
    head = (title or csv_path.stem.replace("_", " ")) + (f"  (first {n} of {total} rows{years})" if n < total else f"  ({total} rows{years})")
    fig_w = max(tw + 0.4, len(head) * CHAR_W * 1.32 + 0.5)       # the title is bold and 2 pt larger than the cells
    fig_h = (n + 1) * ROW_H + 0.75
    plt.rcParams["svg.fonttype"] = "none"
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(fig_h, 0)
    ax.axis("off")
    ax.text(0.2, 0.35, head, fontsize=FONT + 2, fontweight="bold", va="center", ha="left")
    top = 0.65
    ax.add_patch(plt.Rectangle((0.2, top), tw, ROW_H, color="#1f3b63", lw=0))
    for k in range(n):
        if k % 2 == 1:
            ax.add_patch(plt.Rectangle((0.2, top + (k + 1) * ROW_H), tw, ROW_H, color="#eef2f7", lw=0))
    ax.plot([0.2, 0.2 + tw], [top + (n + 1) * ROW_H] * 2, color="#1f3b63", lw=1)
    x = 0.2
    for i, c in enumerate(cols):
        w = widths[i] * CHAR_W
        left = x + 0.08
        right = x + w - 0.08
        ax.text(right if numeric[i] else left, top + ROW_H / 2, short(c), fontsize=FONT, fontweight="bold", color="white",
                va="center", ha="right" if numeric[i] else "left")
        for k, r in enumerate(cells):
            ax.text(right if numeric[i] else left, top + (k + 1.5) * ROW_H, r[i], fontsize=FONT, va="center", ha="right" if numeric[i] else "left")
        x += w
    out = csv_path.with_name(csv_path.stem + "_table")
    fig.savefig(out.with_suffix(".png"), dpi=150)
    fig.savefig(out.with_suffix(".svg"))
    plt.close(fig)
    print(f"written {out.name}.png and {out.name}.svg ({n} of {total} rows)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--rows", type=int, default=50, help="rows drawn (0 = all, at most 1000)")
    ap.add_argument("--title", default=None)
    ap.add_argument("--from-year", type=int, default=0)
    ap.add_argument("--to-year", type=int, default=0)
    a = ap.parse_args()
    draw(a.csv, a.rows, a.title, a.from_year, a.to_year)
