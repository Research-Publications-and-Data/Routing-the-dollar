"""Task 4: Extended rolling correlation chart."""
import pandas as pd, numpy as np, matplotlib.pyplot as plt, matplotlib.dates as mdates, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import DATA_PROC, save_exhibit, setup_plot_style, color

def main():
    data = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv", index_col=0, parse_dates=True)
    weekly = data[["total_supply", "WSHOMCB"]].resample("W-WED").last().dropna()
    setup_plot_style()
    fig, ax = plt.subplots(figsize=(8, 5))
    for window, lw, alpha, ls in [(90, 1, 0.5, "--"), (180, 2, 1.0, "-")]:
        r = weekly["total_supply"].rolling(window // 7).corr(weekly["WSHOMCB"])
        ax.plot(r.index, r, color=color("primary"), linewidth=lw, alpha=alpha,
                linestyle=ls, label=f"{window}-day window")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.axvspan(pd.Timestamp("2024-09-18"), weekly.index[-1], alpha=0.1, color=color("positive"), label="Easing")
    ax.set_ylabel("Pearson Correlation"); ax.set_ylim(-1.1, 1.1)
    ax.set_title("Rolling Correlation: Fed Assets vs. Stablecoin Supply (Extended)")
    ax.legend(loc="lower left"); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    save_exhibit(fig, "exhibit11_extended_rolling_corr.png", "Source: FRED, DefiLlama.")
    print("Exhibit 11 done")

if __name__ == "__main__":
    main()
