# scripts/utils.py
import os, json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"
EXHIBITS = ROOT / "data" / "exhibits"
for d in [DATA_RAW, DATA_PROC, EXHIBITS]:
    d.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(ROOT / "config"))
from settings import CHART_STYLE

def setup_plot_style():
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": [CHART_STYLE["font_body"], "Times New Roman", "DejaVu Serif"],
        "font.size": CHART_STYLE["label_size"],
        "axes.titlesize": CHART_STYLE["title_size"], "axes.titleweight": "bold",
        "axes.grid": True, "grid.color": CHART_STYLE["grid_color"],
        "grid.linestyle": CHART_STYLE["grid_style"], "grid.alpha": 0.7,
        "figure.dpi": CHART_STYLE["dpi"], "savefig.dpi": CHART_STYLE["dpi"],
        "legend.fontsize": 9,
    })

def save_exhibit(fig, filename, source_text="Source: Authors' calculations."):
    fig.text(0.02, 0.01, source_text, fontsize=CHART_STYLE["source_size"],
             fontstyle="italic", color="#666666", transform=fig.transFigure)
    path = EXHIBITS / filename
    fig.savefig(path, dpi=CHART_STYLE["dpi"], bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {path}")

def save_json(data, filename):
    path = DATA_PROC / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Saved: {path}")

def save_csv(df, filename, directory=None):
    path = (directory or DATA_PROC) / filename
    df.to_csv(path, index=True)
    print(f"  Saved: {path}")

def color(name):
    return CHART_STYLE["colors"].get(name, "#333333")
