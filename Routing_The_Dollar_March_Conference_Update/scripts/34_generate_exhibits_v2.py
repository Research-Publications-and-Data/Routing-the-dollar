"""34_generate_exhibits_v2.py — Generate publication-quality exhibits from daily expanded data.

Produces:
  - exhibit08_gateway_volume_by_tier_v2.png + .pdf
  - exhibit10_gateway_concentration_hhi_v2.png + .pdf
  - exhibit_svb_retention_v2.png + .pdf
"""
import pandas as pd, numpy as np, json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, EXHIBITS, save_exhibit, setup_plot_style, color

EXHIBITS_DIR = Path(__file__).resolve().parent.parent / "data" / "exhibits"
EXHIBITS_DIR.mkdir(parents=True, exist_ok=True)


def exhibit08_gateway_volume_by_tier():
    """Exhibit 8: Gateway Transfer Volume by Tier (Daily)."""
    print("  Generating Exhibit 8: Gateway Volume by Tier...")

    shares = pd.read_csv(DATA_PROC / "exhibit_C1_gateway_shares_daily_v2.csv", index_col=0, parse_dates=True)

    setup_plot_style()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Panel A: Stacked area of daily volumes
    vol = shares["total_volume"] / 1e9  # to billions
    t1_vol = vol * shares.get("tier1_share_pct", 0) / 100
    t2_vol = vol * shares.get("tier2_share_pct", 0) / 100
    t3_vol = vol * shares.get("tier3_share_pct", 0) / 100

    # 7-day rolling average for readability
    t1_r = t1_vol.rolling(7, min_periods=1).mean()
    t2_r = t2_vol.rolling(7, min_periods=1).mean()
    t3_r = t3_vol.rolling(7, min_periods=1).mean()

    ax1.plot(shares.index, t1_r, color="#003366", linewidth=1.8, label="Tier 1 (Regulated)")
    ax1.plot(shares.index, t2_r, color="#d68910", linewidth=1.5, label="Tier 2 (Offshore)")
    ax1.plot(shares.index, t3_r, color="#145a32", linewidth=1.5, label="Tier 3 (DeFi)")
    ax1.axvline(pd.Timestamp("2023-03-10"), color="#CC3333", linestyle="--", linewidth=1.2, alpha=0.7)
    ymax = ax1.get_ylim()[1]
    ax1.text(pd.Timestamp("2023-03-12"), ymax * 0.88, " SVB", color="#CC3333", fontsize=9, fontweight="bold")
    ax1.set_ylabel("Gateway Volume ($B, 7-day avg)")
    ax1.set_ylim(bottom=0)
    ax1.legend(loc="upper right", fontsize=9)
    ax1.set_title("Gateway Transfer Volume by Tier", fontweight="bold", fontsize=11)

    # Panel B: Tier 1 share
    t1_share = shares.get("tier1_share_pct", pd.Series(0, index=shares.index))
    t1_rolling = t1_share.rolling(7, min_periods=1).mean()
    mean_share = t1_share.mean()

    ax2.fill_between(shares.index, 0, t1_rolling, color="#003366", alpha=0.3)
    ax2.plot(shares.index, t1_rolling, color="#003366", linewidth=1.5)
    ax2.axhline(mean_share, color="#666666", linestyle="--", linewidth=1.0, alpha=0.8)
    ax2.text(shares.index[-1], mean_share - 4.5, f"Mean: {mean_share:.1f}%",
             fontsize=9, ha="right", color="#666666")
    ax2.axvline(pd.Timestamp("2023-03-10"), color="#CC3333", linestyle="--", linewidth=1.2, alpha=0.7)
    ax2.set_ylabel("Tier 1 Share (%)")
    ax2.set_ylim(0, 100)
    ax2.set_title("Tier 1 Volume Share", fontweight="bold", fontsize=11)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    fig.suptitle("Gateway Transfer Volume by Tier (Expanded Registry)",
                 fontweight="bold", fontsize=13, y=1.02)
    fig.tight_layout()

    for ext in [".png", ".pdf"]:
        fig.savefig(EXHIBITS_DIR / f"exhibit08_gateway_volume_by_tier_v2{ext}",
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"    Tier 1 mean share: {mean_share:.1f}%")


def exhibit10_gateway_concentration_hhi():
    """Exhibit 10: HHI Concentration (Daily)."""
    print("  Generating Exhibit 10: Gateway Concentration HHI...")

    hhi = pd.read_csv(DATA_PROC / "exhibit_C2_concentration_daily_v2.csv", index_col=0, parse_dates=True)

    setup_plot_style()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Panel A: Tier shares stacked area
    shares = pd.read_csv(DATA_PROC / "exhibit_C1_gateway_shares_daily_v2.csv", index_col=0, parse_dates=True)
    t1 = shares.get("tier1_share_pct", 0) / 100
    t2 = shares.get("tier2_share_pct", 0) / 100
    t3 = shares.get("tier3_share_pct", 0) / 100

    ax1.stackplot(shares.index, t1, t2, t3,
                  labels=["Tier 1 (Regulated)", "Tier 2 (Offshore)", "Tier 3 (DeFi)"],
                  colors=["#1a5276", "#d68910", "#145a32"], alpha=0.8)
    ax1.axvspan(pd.Timestamp("2023-03-08"), pd.Timestamp("2023-03-15"),
                color="#ffcccc", alpha=0.3, label="SVB Crisis")
    ax1.set_ylabel("Share of Volume")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f"{x*100:.0f}%"))
    ax1.set_ylim(0, 1)
    ax1.legend(loc="upper right", fontsize=9)
    ax1.set_title("Gateway Tier Volume Shares", fontweight="bold", fontsize=11)

    # Panel B: Dual HHI
    tier_hhi_r = hhi["tier_hhi"].rolling(7, min_periods=1).mean()
    entity_hhi_r = hhi["entity_hhi"].rolling(7, min_periods=1).mean()

    ax2.plot(hhi.index, tier_hhi_r, color="#003366", linewidth=1.5, label="Tier-level HHI (7-day avg)")
    ax2.plot(hhi.index, entity_hhi_r, color="#d68910", linewidth=1.5, label="Entity-level HHI (7-day avg)")
    ax2.axhline(2500, color="#CC3333", linestyle=":", linewidth=1.2, alpha=0.7)
    ax2.text(hhi.index[-1], 2300, "DOJ/FTC Threshold (2,500)",
             fontsize=8, color="#CC3333", fontstyle="italic", ha="right", va="top")
    ax2.axhline(hhi["tier_hhi"].mean(), color="#003366", linestyle="--", linewidth=0.8, alpha=0.5)
    ax2.axhline(hhi["entity_hhi"].mean(), color="#d68910", linestyle="--", linewidth=0.8, alpha=0.5)
    ax2.axvspan(pd.Timestamp("2023-03-08"), pd.Timestamp("2023-03-15"),
                color="#ffcccc", alpha=0.3)
    ax2.set_ylabel("Herfindahl-Hirschman Index")
    ax2.set_ylim(0, 10000)
    ax2.legend(loc="upper right", fontsize=9)
    ax2.set_title("Gateway Routing Concentration (HHI)", fontweight="bold", fontsize=11)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    fig.suptitle("Gateway Routing Concentration (Expanded Registry)",
                 fontweight="bold", fontsize=13, y=1.02)
    fig.tight_layout()

    for ext in [".png", ".pdf"]:
        fig.savefig(EXHIBITS_DIR / f"exhibit10_gateway_concentration_hhi_v2{ext}",
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"    Tier HHI mean: {hhi['tier_hhi'].mean():,.0f}")
    print(f"    Entity HHI mean: {hhi['entity_hhi'].mean():,.0f}")


def exhibit_svb_retention():
    """SVB Detail: Flow Retention by Entity."""
    print("  Generating Exhibit: SVB Flow Retention...")

    with open(DATA_PROC / "svb_retention_v2.json") as f:
        svb = json.load(f)

    retention = svb.get("retention_by_entity", {})
    if not retention:
        print("    No retention data available")
        return

    # Filter to entities with material volume
    entities = []
    values = []
    tiers = []
    for entity, data in sorted(retention.items(), key=lambda x: -x[1]["retention"]):
        if data["normal_daily_avg_B"] > 0.01:  # >$10M daily
            entities.append(entity)
            values.append(data["retention"])
            tiers.append(data["tier"])

    if not entities:
        print("    No entities with material volume")
        return

    setup_plot_style()
    fig, ax = plt.subplots(figsize=(10, 6))

    tier_colors = {1: "#003366", 2: "#d68910", 3: "#145a32"}
    colors = [tier_colors.get(t, "#999999") for t in tiers]

    bars = ax.barh(range(len(entities)), values, color=colors, height=0.6)
    ax.set_yticks(range(len(entities)))
    ax.set_yticklabels(entities)
    ax.axvline(1.0, color="#CC3333", linestyle="--", linewidth=1.2, alpha=0.7)
    ax.text(1.02, len(entities) - 0.5, "Normal = 1.0x", fontsize=8, color="#CC3333")
    ax.set_xlabel("Flow Retention Ratio (SVB stress / pre-SVB normal)")
    ax.set_title("SVB Crisis Flow Retention by Gateway Entity\n(March 9-15 vs Feb 9 - Mar 8, 2023)",
                 fontweight="bold", fontsize=11)

    # Legend for tiers
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#003366", label="Tier 1 (Regulated)"),
        Patch(facecolor="#d68910", label="Tier 2 (Offshore)"),
        Patch(facecolor="#145a32", label="Tier 3 (DeFi)"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=9)

    # Add value labels (smaller font for large values near edge)
    for i, (v, bar) in enumerate(zip(values, bars)):
        fs = 7.5 if v > 8 else 9
        ax.text(v + 0.02, i, f"{v:.2f}x", va="center", fontsize=fs)

    fig.tight_layout()
    for ext in [".png", ".pdf"]:
        fig.savefig(EXHIBITS_DIR / f"exhibit_svb_retention_v2{ext}",
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"    {len(entities)} entities plotted")


def main():
    print("=" * 70)
    print("GENERATE UPDATED EXHIBITS (v2)")
    print("=" * 70)

    exhibit08_gateway_volume_by_tier()
    exhibit10_gateway_concentration_hhi()
    exhibit_svb_retention()

    print("\n  Output files:")
    for f in sorted(EXHIBITS_DIR.glob("*_v2.*")):
        print(f"    {f.name}")
    print("\nDone.")


if __name__ == "__main__":
    main()
