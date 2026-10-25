"""Plots of the sheet "03_Annual_Production":
  annual_production   documents (bars) and total citations (line) per year
  annual_trend        documents per year (bars from light yellow to dark red as the years go by, with their numbers) and a log trend line: the exponential
                      ln(documents) = a + b x year fitted by least squares, with R^2 (on the log scale) and the growth per year e^b - 1. Years without papers
                      cannot be fitted (ln 0); years after the last complete year (still being indexed) are drawn hatched and left out of the fit.
Input : 03_Annual_Production.csv in this folder (run 03_Annual_Production.py first)        Output: annual_production and annual_trend (.png and .svg, same folder)
Run   : python3 03_Annual_Production_plot.py   (needs matplotlib)
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


def read(name="03_Annual_Production.csv"):
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
start, end = year_window(t["Year"], t["Documents"], *year_args())
xlab = year_label(t["Year"], t["Documents"], start, end)
t = t[(t["Year"] >= start) & (t["Year"] <= end)]
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.bar(t["Year"], t["Documents"], color=BLUE, width=0.6, label="Documents")
ax.set_xlabel(xlab)
year_axis(ax, t["Year"])
ax.set_ylabel("Documents")
ax2 = ax.twinx()
ax2.plot(t["Year"], t["Total Citations"], color=ORANGE, marker="o", lw=2.5, label="Total citations")
ax2.set_ylabel("Total citations")
ax2.grid(False)
ax2.spines["right"].set_visible(True)
h1, l1 = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
ax.set_title("Annual scientific production")
save(fig, "annual_production")

# 2. the log trend line
last = datetime.date.today().year - 1                       # the last complete year; later years are still being indexed
fit = t[(t["Documents"] > 0) & (t["Year"] <= last)]
fig, ax = plt.subplots(figsize=(12, 5.5))
shade = plt.get_cmap("YlOrRd")(0.2 + 0.75 * (t["Year"] - start) / max(1, end - start))
late = (t["Year"] > last).to_numpy()
ax.bar(t["Year"], t["Documents"], color=shade, width=0.8, edgecolor="white", hatch=None)
if late.any():
    ax.bar(t["Year"][late], t["Documents"][late], color="none", width=0.8, edgecolor="#555555", hatch="//", lw=0, label="Not in the fit (year still being indexed)")
for x, v in zip(t["Year"], t["Documents"]):
    ax.text(x, v, f"{v:,}", ha="center", va="bottom", fontsize=9, color="#333333")
if len(fit) >= 3:
    b, a = np.polyfit(fit["Year"], np.log(fit["Documents"]), 1)
    y = np.log(fit["Documents"].to_numpy(dtype=float))
    r2 = 1 - ((y - (a + b * fit["Year"].to_numpy())) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    xs = np.linspace(fit["Year"].min(), fit["Year"].max(), 200)
    ax.plot(xs, np.exp(a + b * xs), color="#1F3FD6", lw=2.8, label="Log trend line")
    ax.text(0.1, 0.86, f"ln(documents) = {a:.2f} + {b:.2f} \u00d7 year   (R\u00b2 = {r2:.2f})", transform=ax.transAxes, fontsize=12, fontweight="bold", color="#333333")
    ax.text(0.1, 0.79, f"growth of {100 * (np.exp(b) - 1):.2f} % per year ({fit['Year'].min()}-{fit['Year'].max()})", transform=ax.transAxes, fontsize=11, color="#333333")
    print(f"log trend line {fit['Year'].min()}-{fit['Year'].max()}: ln(documents) = {a:.2f} + {b:.4f} x year, R2 = {r2:.2f}, growth {100 * (np.exp(b) - 1):.2f} % per year")
else:
    print("log trend line: fewer than 3 years with papers, no line drawn")
ax.set_xlabel(xlab)
year_axis(ax, t["Year"])
ax.set_ylabel("Number of documents")
ax.set_ylim(0, t["Documents"].max() * 1.12)
ax.grid(axis="x", visible=False)
if ax.get_legend_handles_labels()[0]:
    ax.legend(loc="upper left", frameon=True)
ax.set_title("Annual scientific production with a log trend line")
save(fig, "annual_trend")
