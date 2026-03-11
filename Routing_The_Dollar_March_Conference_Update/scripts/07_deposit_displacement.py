"""Task 7: Deposit displacement analysis."""
import pandas as pd, numpy as np, matplotlib.pyplot as plt, matplotlib.dates as mdates, sys
from scipy import stats
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json, save_csv, save_exhibit, setup_plot_style, color

def main():
    print("Deposit Displacement Analysis\n")
    fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
    try:
        unified = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv", index_col=0, parse_dates=True)
        supply = unified["total_supply"]
    except:
        supply = pd.read_csv(DATA_RAW / "stablecoin_supply_extended.csv", index_col=0, parse_dates=True)["total_supply"]

    weekly_supply = supply.resample("W-WED").last()
    # Use corrected series ID
    dep_col = "DPSACBW027SBOG" if "DPSACBW027SBOG" in fred.columns else "DPSACBW057SBOG"
    total_dep = fred[dep_col].resample("W-WED").last()

    comp = pd.DataFrame({"sc_B": weekly_supply / 1e9, "dep_B": total_dep}).dropna()
    if comp["sc_B"].max() > 1e6: comp["sc_B"] /= 1e9  # normalize if needed

    # Index to 100
    idx_date = comp.index[comp.index >= "2023-02-01"][0]
    for c in ["sc_B", "dep_B"]:
        comp[f"{c}_idx"] = comp[c] / comp.loc[idx_date, c] * 100
    save_csv(comp, "deposit_stablecoin_comparison.csv")

    # Correlations
    r_lvl, p_lvl = stats.pearsonr(comp["sc_B"].dropna(), comp["dep_B"].dropna())
    diff = comp[["sc_B", "dep_B"]].diff().dropna()
    r_diff, p_diff = stats.pearsonr(diff.iloc[:, 0], diff.iloc[:, 1])
    results = {"level_r": round(r_lvl, 4), "level_p": round(p_lvl, 4),
               "diff_r": round(r_diff, 4), "diff_p": round(p_diff, 4)}
    print(f"  Level: r={r_lvl:.4f}, Diff: r={r_diff:.4f}")

    # Deposit composition
    sav_col = "SAVINGSL" if "SAVINGSL" in fred.columns else None
    dem_col = "DEMDEPSL" if "DEMDEPSL" in fred.columns else None
    if sav_col and dem_col:
        savings = fred[sav_col]
        demand = fred[dem_col]
        s_m = pd.to_numeric(savings, errors='coerce').resample("ME").last()
        d_m = pd.to_numeric(demand, errors='coerce').resample("ME").last()
        t_m = pd.to_numeric(fred[dep_col], errors='coerce').resample("ME").last()
        retail_share = ((s_m + d_m) / t_m * 100).dropna()
        if len(retail_share) > 5:
            results["retail_start"] = round(float(retail_share.iloc[0]), 1)
            results["retail_end"] = round(float(retail_share.iloc[-1]), 1)
            print(f"  Retail share: {results['retail_start']:.1f}% -> {results['retail_end']:.1f}%")
    save_json(results, "deposit_displacement_results.json")

    # Exhibit 17
    setup_plot_style()
    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(comp.index, comp["sc_B_idx"], color=color("primary"), lw=2, label="Stablecoin Supply")
    ax1.set_ylabel("Stablecoin (indexed=100)", color=color("primary"))
    ax2 = ax1.twinx()
    ax2.plot(comp.index, comp["dep_B_idx"], color=color("secondary"), lw=2, ls="--", label="Bank Deposits")
    ax2.set_ylabel("Deposits (indexed=100)", color=color("secondary"))
    ax1.set_title("Stablecoin Supply vs. Bank Deposits")
    lines = ax1.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
    labels = ax1.get_legend_handles_labels()[1] + ax2.get_legend_handles_labels()[1]
    ax1.legend(lines, labels, loc="upper left")
    save_exhibit(fig, "exhibit17_deposits_vs_stablecoins.png", "Source: FRED (H.8), DefiLlama.")

    print("\n  Interpretation:")
    if r_diff < -0.1 and p_diff < 0.05: print("  -> Significant negative: displacement evidence")
    elif abs(r_diff) < 0.1: print("  -> No relationship: consistent with recycle/restructure channel")
    else: print("  -> Positive: stablecoins additive at current scale")
    print("Done")

if __name__ == "__main__":
    main()
