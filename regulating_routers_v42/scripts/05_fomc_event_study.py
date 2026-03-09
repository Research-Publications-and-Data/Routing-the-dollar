"""Task 5: FOMC event study -- stablecoin supply response."""
import pandas as pd, numpy as np, matplotlib.pyplot as plt, sys
from scipy import stats
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "config"))
from settings import FOMC_DATES
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json, save_csv, save_exhibit, setup_plot_style, color

def main():
    print("FOMC Event Study\n")
    try:
        data = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv", index_col=0, parse_dates=True)
        supply = data["total_supply"].dropna()
    except:
        data = pd.read_csv(DATA_RAW / "stablecoin_supply_extended.csv", index_col=0, parse_dates=True)
        supply = data["total_supply"].dropna()

    horizons = [1, 3, 5, 10]
    events = []
    for date_str, bps, cls in FOMC_DATES:
        date = pd.Timestamp(date_str)
        if date < supply.index[0] or date > supply.index[-1]: continue
        idx = supply.index.searchsorted(date)
        if idx >= len(supply): continue
        event = {"fomc_date": date_str, "decision_bps": bps, "classification": cls,
                 "supply_at_event": float(supply.iloc[idx])}
        pre_start = max(0, idx - 10)
        pre_avg = float(supply.iloc[pre_start:idx].diff().dropna().mean()) if idx > pre_start + 1 else 0
        for h in horizons:
            post_idx = min(idx + h, len(supply) - 1)
            pct = (supply.iloc[post_idx] - supply.iloc[idx]) / supply.iloc[idx] * 100
            event[f"pct_change_t{h}"] = round(float(pct), 4)
        events.append(event)

    df = pd.DataFrame(events)
    save_csv(df.set_index("fomc_date"), "fomc_events.csv")

    results = {"n_events": len(events), "by_class": {}}
    for cls in ["dovish", "neutral", "hawkish"]:
        sub = df[df["classification"] == cls]
        if len(sub) == 0: continue
        cls_r = {"n": len(sub)}
        for h in horizons:
            vals = sub[f"pct_change_t{h}"].dropna()
            t, p = stats.ttest_1samp(vals, 0) if len(vals) > 1 else (0, 1)
            cls_r[f"t{h}"] = {"mean": round(float(vals.mean()), 4), "t": round(float(t), 3), "p": round(float(p), 4)}
            sig = "**" if p < 0.05 else "*" if p < 0.10 else ""
            print(f"  {cls} t+{h}: mean={vals.mean():.4f}%, t={t:.2f}, p={p:.3f}{sig}")
        results["by_class"][cls] = cls_r
    save_json(results, "fomc_results.json")

    # Plot
    setup_plot_style()
    fig, ax = plt.subplots(figsize=(8, 5))
    for cls, c, m in [("dovish", color("positive"), "o"), ("neutral", color("tertiary"), "s"), ("hawkish", color("stress"), "^")]:
        sub = df[df["classification"] == cls]
        if len(sub) == 0: continue
        means = [sub[f"pct_change_t{h}"].mean() for h in horizons]
        ax.plot(horizons, means, label=f"{cls.title()} (n={len(sub)})", color=c, marker=m, linewidth=2, markersize=6)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("Days After FOMC"); ax.set_ylabel("Cumulative Supply Change (%)")
    ax.set_title("Stablecoin Supply Response to FOMC Announcements"); ax.legend(); ax.set_xticks(horizons)
    save_exhibit(fig, "exhibit12_fomc_event_study.png", "Source: FRED, DefiLlama, federalreserve.gov.")
    print("Done")

if __name__ == "__main__":
    main()
