"""Draw the application icon (needs matplotlib) and build The Data Application.app/Contents/Resources/AppIcon.icns (macOS: sips, iconutil).

    python3 docs/icon/make_icon.py        (from the application folder)
A blue rounded square on the macOS icon grid (824 px on a 1024 canvas), white bars and a yellow trend line.
"""
import subprocess
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "The Data Application.app" / "Contents" / "Resources" / "AppIcon.icns"

fig = plt.figure(figsize=(10.24, 10.24), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1024); ax.set_ylim(0, 1024); ax.axis("off")
fig.patch.set_alpha(0)
ax.add_patch(FancyBboxPatch((106, 86), 824, 824, boxstyle="round,pad=0,rounding_size=185", fc=(0, 0, 0, 0.22), ec="none"))
im = ax.imshow(np.linspace(0, 1, 256).reshape(-1, 1), extent=(100, 924, 100, 924), origin="lower",
               cmap=matplotlib.colors.LinearSegmentedColormap.from_list("b", ["#0a3f86", "#2f80e8"]))
clip = FancyBboxPatch((100, 100), 824, 824, boxstyle="round,pad=0,rounding_size=185", fc="none", ec="none")
ax.add_patch(clip); im.set_clip_path(clip)
for x, h in zip([265, 405, 545, 685], [200, 320, 260, 450]):
    ax.add_patch(FancyBboxPatch((x - 50, 245), 100, h, boxstyle="round,pad=0,rounding_size=22", fc=(1, 1, 1, 0.93), ec="none"))
lx, ly = [265, 405, 545, 685, 790], [520, 600, 585, 735, 790]
ax.plot(lx, ly, color="#ffcf4d", lw=26, solid_capstyle="round", solid_joinstyle="round")
for x, y in zip(lx, ly):
    ax.add_patch(Circle((x, y), 30, fc="#ffcf4d", ec="#0a3f86", lw=8))
ax.plot([185, 840], [235, 235], color=(1, 1, 1, 0.85), lw=14, solid_capstyle="round")
with tempfile.TemporaryDirectory() as tmp:
    png, iconset = Path(tmp) / "icon_1024.png", Path(tmp) / "AppIcon.iconset"
    fig.savefig(png, dpi=100, transparent=True)
    iconset.mkdir()
    for s in (16, 32, 128, 256, 512):
        for size, name in ((s, f"icon_{s}x{s}.png"), (2 * s, f"icon_{s}x{s}@2x.png")):
            subprocess.run(["sips", "-z", str(size), str(size), str(png), "--out", str(iconset / name)], check=True, capture_output=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(OUT)], check=True)
print("written", OUT)
