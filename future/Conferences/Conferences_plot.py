"""Plots of the sheet "Conferences": the conferences that were held at least n times (n = your choice, in the application; default 3)
  conference_timeline      timeline: one row per conference, a bubble for every conference year with papers (size = papers, darker = more citations per year)
  conference_editions_bars bars: number of editions of every such conference, with its papers and citations written next to the bar
Input : Conferences.csv and Conferences_timeline.csv in this folder (run Conferences.py first)        Output: .png and .svg of both plots, same folder
Run   : python3 Conferences_plot.py   (needs matplotlib, pandas)
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


def read(name="11_Sources_Over_Time.csv"):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Author ID": str})


def short(text, n=48):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "..."


def save(fig, name):
    fig.savefig(HERE / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"written {name}.png and {name}.svg")



T = read("Conferences.csv")
T = T[T["In plots"] == 1]
if T.empty:
    fig, ax = plt.subplots(figsize=(8, 2.5))
    ax.axis("off")
    ax.text(0.5, 0.5, "No conference has the minimum number of editions chosen.\nChoose a smaller number and generate the data again.", ha="center", va="center", fontsize=13)
    save(fig, "conference_editions_bars")
    raise SystemExit("No conference reaches the minimum number of editions: choose a smaller number.")

# 1. bars: editions per conference
b = T.sort_values(["Editions", "Papers"], ascending=True)
fig, ax = plt.subplots(figsize=(10, 0.5 * len(b) + 1.8))
ax.barh([short(s, 60) for s in b["Conference"]], b["Editions"], color=BLUE)
for i, (e, p, c_) in enumerate(zip(b["Editions"], b["Papers"], b["Citations"])):
    ax.text(e + 0.05, i, f"{e} editions   ({p} papers, {c_} citations)", va="center", fontsize=10)
ax.set_xlabel("Editions (different conference years) in the data")
ax.set_xlim(0, b["Editions"].max() * 1.6)
ax.set_xticks(range(0, int(b["Editions"].max()) + 2))
ax.set_title("Conferences with at least %d editions" % T["Editions"].min())
save(fig, "conference_editions_bars")

# second option: the timeline of Biblioshiny: one row per conference, a line from the first to the last year, a bubble for every year with papers
# (size = papers of the year, darker = more citations per year); the most productive on top
tl = read("Conferences_timeline.csv")
order = list(dict.fromkeys(tl["Conference"]))
ypos = {a: len(order) - 1 - i for i, a in enumerate(order)}
from matplotlib.colors import LinearSegmentedColormap
BLUES_FROM_LIGHT = LinearSegmentedColormap.from_list("blues_light", ["#BFD5EA", "#0B2F6B"])      # the lightest bubble stays visible on white
def bubble(n):
    """area of a bubble: grows with the papers of the year; the largest value of this plot always gets the same (biggest) size"""
    return 50 + 650 * pd.Series(n) / tl["Papers"].max() if hasattr(n, "__len__") else 50 + 650 * n / tl["Papers"].max()


fig, ax = plt.subplots(figsize=(11, 0.5 * len(order) + 2.2))
for a, g in tl.groupby("Conference"):
    ax.plot([g["Year"].min(), g["Year"].max()], [ypos[a]] * 2, color="#C9A0A0", lw=2.5, zorder=1, solid_capstyle="round")
sc = ax.scatter(tl["Year"], [ypos[a] for a in tl["Conference"]], s=bubble(tl["Papers"]), c=tl["TC per year"], cmap=BLUES_FROM_LIGHT, vmin=0, vmax=tl["TC per year"].max(), alpha=0.85, edgecolor="#1F3F6B", linewidth=0.6, zorder=2)
ax.set_yticks([ypos[a] for a in order], [short(a, 52) for a in order], fontweight="bold")
ax.set_xticks(range(int(tl["Year"].min()), int(tl["Year"].max()) + 1))
ax.set_xlim(tl["Year"].min() - 0.6, tl["Year"].max() + 0.6)
ax.set_ylim(-0.7, len(order) - 0.3)
ax.grid(axis="y")
ax.grid(axis="x", visible=False)
ax.set_xlabel("Conference year")
ax.set_ylabel("Conference")
ax.set_title("Conferences with several editions: papers per conference year")
cb = fig.colorbar(sc, ax=ax, pad=0.02, shrink=0.5)
cb.set_label("TC per year")
sizes = sorted({1, int(tl["Papers"].max()), max(int(tl["Papers"].max()) // 2, 1)})
ax.legend([plt.scatter([], [], s=bubble(n), c="#7FA6D0", edgecolor="#1F3F6B") for n in sizes], [str(n) for n in sizes], title="Papers", frameon=False, loc="upper left", bbox_to_anchor=(1.12, 0.35), labelspacing=1.4)
save(fig, "conference_timeline")
