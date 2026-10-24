"""common/plotlook.py : run a plot script with another look, without changing the script or its data.

    python ../common/plotlook.py [--text 1.3] [--size 1.2] [--dpi 300] [--formats pdf,tiff] [--palette colourblind] <Sheet>_plot.py [the script's own arguments]

The application uses it when the project's plot settings (Settings, "Look of the plots") differ from the defaults; without it a plot script draws with its own look.
  --text      multiplies every font size of the picture (titles, labels, tick labels, legends, annotations)
  --size      multiplies the width and height of the picture
  --dpi       resolution of the raster files (PNG, TIFF); journals usually ask for 300 or 600
  --formats   also writes a PDF and/or a TIFF next to every PNG the script writes (same name)
  --palette   colourblind: the plot colours are swapped for the Okabe-Ito palette, which people with any common colour-vision deficiency can tell apart
              (sequential colour maps such as Blues and viridis are already safe and stay as they are)
It works by wrapping matplotlib's Figure.savefig: just before a picture is saved, its texts, size and colours are changed. Needs matplotlib.
"""
import argparse
import runpy
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np
from matplotlib import colors as mcolors, rcParams
from matplotlib.figure import Figure
from matplotlib.text import Text

OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]
TAB10 = ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD", "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF"]
SWAP = {                                                     # the colours the plot scripts use -> their Okabe-Ito counterpart
    "#2F6DB5": "#0072B2", "#4C78A8": "#0072B2", "#2E86C1": "#0072B2", "#F28E2B": "#E69F00", "#F58518": "#E69F00", "#E67E22": "#E69F00", "#F39C12": "#E69F00",
    "#59A14F": "#009E73", "#27AE60": "#009E73", "#D6504A": "#D55E00", "#E8372C": "#D55E00", "#C0392B": "#D55E00", "#CD853F": "#D55E00",
    "#9B6BB5": "#CC79A7", "#8E44AD": "#CC79A7", "#46C7C7": "#56B4E9", "#16A085": "#56B4E9", "#CFECEC": "#D3E9F6", "#F1C40F": "#F0E442",
    **{t: OKABE_ITO[i % 7] for i, t in enumerate(TAB10[:7])}}


def parse(argv):
    """the wrapper's own arguments (before the script name) and the script with its arguments"""
    i = next((k for k, a in enumerate(argv) if a.endswith(".py")), None)
    if i is None:
        sys.exit("plotlook.py: give the plot script to run, e.g.  python plotlook.py --text 1.3 03_Annual_Production_plot.py")
    ap = argparse.ArgumentParser(prog="plotlook.py")
    ap.add_argument("--text", type=float, default=1.0)
    ap.add_argument("--size", type=float, default=1.0)
    ap.add_argument("--dpi", type=int, default=0)
    ap.add_argument("--formats", default="")
    ap.add_argument("--palette", choices=["standard", "colourblind"], default="standard")
    return ap.parse_args(argv[:i]), argv[i], argv[i + 1:]


def _safe(c):
    """the colour-blind safe colour for c, with the same transparency; None when c is not one of the plot colours"""
    try:
        r, g, b, a = mcolors.to_rgba(c)
    except (ValueError, TypeError):
        return None
    new = SWAP.get(mcolors.to_hex((r, g, b)).upper())
    return None if new is None else mcolors.to_rgba(new, a)


def recolour(fig):
    for art in fig.findobj():
        if hasattr(art, "get_array") and art.get_array() is not None:      # coloured by a colour map (heat maps, bubbles): left as it is
            continue
        for prop in ("facecolor", "edgecolor", "color", "markerfacecolor", "markeredgecolor"):
            get, put = getattr(art, "get_" + prop, None), getattr(art, "set_" + prop, None)
            if get is None or put is None:
                continue
            try:
                cur = get()
            except Exception:
                continue
            if isinstance(cur, np.ndarray) and cur.ndim == 2:                # a collection: one colour per item
                new = [_safe(c) for c in cur]
                if any(new):
                    put([n or tuple(c) for n, c in zip(new, cur)])
            elif not isinstance(cur, np.ndarray) or cur.ndim == 1:
                new = _safe(cur)
                if new is not None:
                    put(new)


def bigger_text(fig, k):
    for t in fig.findobj(Text):
        t.set_fontsize(t.get_fontsize() * k)
    for ax in fig.axes:                                  # tick labels made later (at drawing time) must get the new size as well
        for axis in (ax.xaxis, ax.yaxis):
            ticks = axis.get_major_ticks()
            if ticks:
                axis.set_tick_params(which="both", labelsize=ticks[0].label1.get_fontsize())


def main(argv):
    look, script, rest = parse(argv)
    formats = [f.strip().lower() for f in look.formats.split(",") if f.strip()]
    if look.palette == "colourblind":
        rcParams["axes.prop_cycle"] = matplotlib.cycler(color=OKABE_ITO)
    original = Figure.savefig

    def savefig(fig, fname, *a, **kw):
        if not getattr(fig, "_plotlook_done", False):           # a script saves the same picture as PNG and SVG: change it only once
            if look.palette == "colourblind":
                recolour(fig)
            if look.text != 1.0:
                bigger_text(fig, look.text)
            if look.size != 1.0:
                w, h = fig.get_size_inches()
                fig.set_size_inches(w * look.size, h * look.size)
            fig._plotlook_done = True
        name = str(fname)
        if look.dpi and name.lower().endswith((".png", ".tif", ".tiff", ".jpg")):
            kw["dpi"] = look.dpi
        original(fig, fname, *a, **kw)
        if name.lower().endswith(".png"):
            for f in formats:
                extra = dict(kw)
                if f == "tiff":
                    extra["dpi"] = look.dpi or kw.get("dpi") or 300
                    extra["pil_kwargs"] = {"compression": "tiff_lzw"}
                    original(fig, name[:-4] + ".tif", *a, **extra)
                elif f == "pdf":
                    extra.pop("dpi", None)
                    original(fig, name[:-4] + ".pdf", *a, **extra)
    Figure.savefig = savefig
    sys.argv = [script] + rest
    sys.path.insert(0, str(Path(script).resolve().parent))
    runpy.run_path(script, run_name="__main__")
    if formats:
        print(f"plotlook: also wrote {' and '.join(f.upper() for f in formats)} next to every PNG")


if __name__ == "__main__":
    main(sys.argv[1:])
