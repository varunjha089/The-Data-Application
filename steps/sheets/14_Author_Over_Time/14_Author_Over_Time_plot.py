"""Plot of the sheet "14_Author_Over_Time": papers per year of the ten most productive authors (heat map)
Input : 14_Author_Over_Time.csv in this folder (run 14_Author_Over_Time.py first)        Output: authors_over_time and authors_timeline (.png and .svg, same folder)
Run   : python3 14_Author_Over_Time_plot.py   (needs matplotlib)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
BLUE, ORANGE, GREEN, RED, PURPLE, GREY = "#2F6DB5", "#F28E2B", "#59A14F", "#D6504A", "#9B6BB5", "#9AA0A6"
plt.rcParams.update({"font.size": 11, "axes.titlesize": 14, "axes.titleweight": "bold", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#E3E3E3", "axes.axisbelow": True})


def read(name="14_Author_Over_Time.csv"):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Author ID": str})


def short(text, n=48):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "..."


def save(fig, name):
    fig.savefig(HERE / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"written {name}.png and {name}.svg")


import argparse
import datetime
from matplotlib.ticker import FormatStrFormatter, MaxNLocator
import numpy as np


# Year axes: a corpus can span 10 years or 55, so the axis must not draw one label per year. Numeric axis with about 10 round ticks, early-access years shaded, and a range
# of years you can choose (--from-year / --to-year, 0 = automatic; the application passes your choice). Automatic start = the first year at which 1% of the papers are reached;
# the years left out are named in the axis label. Only the picture is cut, never the table.
def year_args():
    """the first and last year asked for (0 = automatic)"""
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-year", type=int, default=0)
    ap.add_argument("--to-year", type=int, default=0)
    a, _ = ap.parse_known_args()
    lo, hi = a.from_year, a.to_year
    return (hi, lo) if lo and hi and lo > hi else (lo, hi)


def year_start(years, size, share=0.01):
    """first year at which the running total of `size` (papers per year) reaches `share` of the whole"""
    years, cum = list(years), np.cumsum(np.asarray(size, dtype=float))
    return years[int(np.argmax(cum >= share * cum[-1]))] if len(cum) and cum[-1] > 0 else (years[0] if years else 0)


def year_window(years, size, lo=0, hi=0):
    """first and last year drawn: the chosen ones, else automatic (from the 1% year to the last year of the data)"""
    start, end = lo or year_start(years, size), hi or max(years)
    if start > end:
        raise SystemExit(f"No year to draw: the range {start}-{end} is empty.")
    return start, end


def year_keep(years, start, end):
    """True for the years inside the window"""
    return [start <= y <= end for y in years]


def year_label(years, size, start, end, label="Year"):
    """axis label that says which years were left out (and how many papers they hold)"""
    years, size = list(years), np.asarray(size, dtype=float)
    hid = [y for y in years if y < start or y > end]
    if not hid or size.sum() == 0:
        return label
    n = size[[y < start or y > end for y in years]].sum()
    parts = [f"{min(y for y in hid if y < start)}-{start - 1}" if any(y < start for y in hid) else "", f"{end + 1}-{max(y for y in hid if y > end)}" if any(y > end for y in hid) else ""]
    return f"{label}   ({', '.join(p for p in parts if p)} not shown: {n:.0f} {'paper' if n == 1 else 'papers'}, {100 * n / size.sum():.1f}%)"


def year_axis(ax, years, pad=0.6):
    """about 10 integer ticks whatever the span; years after the current year (early access) are shaded"""
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=10, steps=[1, 2, 5, 10]))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%d"))
    ax.set_xlim(min(years) - pad, max(years) + pad)
    this = datetime.date.today().year
    if max(years) > this:
        ax.axvspan(this + 0.5, max(years) + 0.5, color="#888888", alpha=0.13, lw=0, zorder=0)
        ax.text((this + max(years) + 1) / 2, 0.05, "early access", transform=ax.get_xaxis_transform(), rotation=90, va="bottom", ha="center", fontsize=8, color="#555555")


def year_rows(df, col="Year"):
    """the rows of a table whose year is inside the years you chose (all rows when you chose nothing)"""
    lo, hi = year_args()
    out = df[(df[col] >= (lo or df[col].min())) & (df[col] <= (hi or df[col].max()))]
    if out.empty:
        raise SystemExit(f"No data between {lo or 'the first year'} and {hi or 'the last year'}.")
    return out


t = read()
years = [c for c in t.columns if c.isdigit()]
m = t[years].to_numpy()
yn = [int(y) for y in years]
size = m.sum(axis=0)
start, end = year_window(yn, size, *year_args())
xlab = year_label(yn, size, start, end)
keep = [i for i, y in enumerate(yn) if start <= y <= end]
years, m, size, yn = [years[i] for i in keep], m[:, keep], size[keep], [yn[i] for i in keep]
fig, ax = plt.subplots(figsize=(10, 0.55 * len(t) + 2.2))
im = ax.imshow(m, cmap="Blues", aspect="auto")
step = max(1, int(np.ceil(len(years) / 12)))        # at most about 12 labels
ax.set_xticks(range(0, len(years), step), years[::step])
if yn[-1] > datetime.date.today().year:         # early-access years are marked
    ax.axvspan(yn.index(datetime.date.today().year + 1) - 0.5, len(yn) - 0.5, color="#888888", alpha=0.25, lw=0)
ax.set_yticks(range(len(t)), [short(a, 40) for a in t["Author"]])
ax.grid(False)
for i in range(m.shape[0]):
    for j in range(m.shape[1]):
        if m[i, j]:
            ax.text(j, i, int(m[i, j]), ha="center", va="center", color="white" if m[i, j] > m.max() * 0.55 else "black")
ax.set_xlabel(xlab)
ax.set_title("Authors' production over time (papers per year)")
save(fig, "authors_over_time")

# second option: the timeline of Biblioshiny: one row per author, a line from the first to the last year, a bubble for every year with papers
# (size = papers of the year, darker = more citations per year); the 15 most productive authors, the most productive on top
tl = year_rows(read("14_Author_Timeline.csv"))
order = list(dict.fromkeys(tl["Author ID"]))
name = dict(zip(tl["Author ID"], tl["Author"]))
ypos = {a: len(order) - 1 - i for i, a in enumerate(order)}
from matplotlib.colors import LinearSegmentedColormap
BLUES_FROM_LIGHT = LinearSegmentedColormap.from_list("blues_light", ["#BFD5EA", "#0B2F6B"])      # the lightest bubble stays visible on white
def bubble(n):
    """area of a bubble: grows with the papers of the year; the largest value of this plot always gets the same (biggest) size"""
    return 50 + 650 * pd.Series(n) / tl["Papers"].max() if hasattr(n, "__len__") else 50 + 650 * n / tl["Papers"].max()


fig, ax = plt.subplots(figsize=(11, 0.5 * len(order) + 2.2))
for a, g in tl.groupby("Author ID"):
    ax.plot([g["Year"].min(), g["Year"].max()], [ypos[a]] * 2, color="#C9A0A0", lw=2.5, zorder=1, solid_capstyle="round")
sc = ax.scatter(tl["Year"], [ypos[a] for a in tl["Author ID"]], s=bubble(tl["Papers"]), c=tl["TC per year"], cmap=BLUES_FROM_LIGHT, vmin=0, vmax=tl["TC per year"].max(), alpha=0.85, edgecolor="#1F3F6B", linewidth=0.6, zorder=2)
ax.set_yticks([ypos[a] for a in order], [short(name[a], 30) for a in order], fontweight="bold")
year_axis(ax, tl["Year"])
ax.set_ylim(-0.7, len(order) - 0.3)
ax.grid(axis="y")
ax.grid(axis="x", visible=False)
ax.set_xlabel("Year")
ax.set_ylabel("Author")
ax.set_title("Authors' production over time")
cb = fig.colorbar(sc, ax=ax, pad=0.02, shrink=0.5)
cb.set_label("TC per year")
sizes = sorted({1, int(tl["Papers"].max()), max(int(tl["Papers"].max()) // 2, 1)})
ax.legend([plt.scatter([], [], s=bubble(n), c="#7FA6D0", edgecolor="#1F3F6B") for n in sizes], [str(n) for n in sizes], title="Papers", frameon=False, loc="upper left", bbox_to_anchor=(1.12, 0.35), labelspacing=1.4)
save(fig, "authors_timeline")
