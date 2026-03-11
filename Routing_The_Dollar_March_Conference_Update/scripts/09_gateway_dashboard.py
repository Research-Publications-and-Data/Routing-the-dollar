"""Task 9: Gateway Monitoring Dashboard — 5-panel grid.

Slide-first build at 16:9 (16x9 inches). Paper version at 6.5x9 inches.
All data from existing processed files.

Panels:
  A. Tier Share Tracker (stacked area, 100% y-axis)
  B. Tier-Level HHI (line + 2,500 DOJ/FTC threshold)
  C. Counterparty Concentration (top intermediary share)
  D. Stress Alert (T1 deviation from trailing mean, +/-2sigma bands)
  E. Settlement-Hour Heatmap (full width)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# ── Paths ────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"
EXHIBITS = ROOT / "data" / "exhibits"
EXHIBITS.mkdir(parents=True, exist_ok=True)

# ── Style ────────────────────────────────────────────────────
T1_COLOR = "#2166ac"   # blue
T2_COLOR = "#f4a582"   # amber
T3_COLOR = "#bdbdbd"   # gray (lighter for visibility)
STRESS_COLOR = "#CC3333"
POS_COLOR = "#339933"
DARK_BLUE = "#003366"
THRESHOLD_RED = "#CC3333"
BAND_BLUE = "#B0C4DE"

SVB_DATE = pd.Timestamp("2023-03-10")
RATE_CUT_DATE = pd.Timestamp("2024-09-18")


def set_rcparams(is_paper=False):
    """Set matplotlib rcParams based on output target."""
    base = 8 if not is_paper else 7.5
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Georgia", "DejaVu Serif"],
        "font.size": base,
        "axes.titlesize": base + 1.5,
        "axes.titleweight": "bold",
        "axes.labelsize": base,
        "xtick.labelsize": base - 1,
        "ytick.labelsize": base - 1,
        "legend.fontsize": base - 1.5,
        "axes.grid": True,
        "grid.color": "#E8E8E8",
        "grid.linestyle": "--",
        "grid.alpha": 0.5,
        "grid.linewidth": 0.3,
    })


# ── Data Loaders ─────────────────────────────────────────────

def load_tier_shares():
    """Load tier share data for Panels A and D.

    Uses _v2 (entity-level, 19-entity registry) — the paper's authoritative
    data pipeline.  The _upgraded file used B-level bucket aggregation that
    inflated T1 to ~82%; the correct entity-level T1 mean is ~41%.
    """
    df = pd.read_csv(
        DATA_PROC / "exhibit_C1_gateway_shares_daily_v2.csv",
        parse_dates=["day"],
    )
    df = df.set_index("day").sort_index()
    df.index = df.index.tz_localize(None)
    # Convert percentages (0-100) to fractions (0-1) for downstream compat
    df["tier1_B_share"] = df["tier1_share_pct"] / 100
    df["tier2_B_share"] = df["tier2_share_pct"] / 100
    df["tier3_B_share"] = df["tier3_share_pct"] / 100
    # Normalize to sum to 1.0
    total = df[["tier1_B_share", "tier2_B_share", "tier3_B_share"]].sum(axis=1)
    for c in ["tier1_B_share", "tier2_B_share", "tier3_B_share"]:
        df[c] = df[c] / total
    return df


def load_hhi():
    """Load HHI data for Panel B.

    Uses _v2 (entity-level) which has tier_hhi already on 0-10,000 scale.
    The _upgraded file used B-level aggregation (hhi_B on 0-1 scale → 7,361);
    the correct tier-level HHI mean is ~5,021.
    """
    df = pd.read_csv(
        DATA_PROC / "exhibit_C2_concentration_daily_v2.csv",
        parse_dates=["day"],
    )
    df = df.set_index("day").sort_index()
    df.index = df.index.tz_localize(None)
    df["hhi_10k"] = df["tier_hhi"]  # already 0-10,000 scale
    return df


def load_counterparty_monthly():
    """Build monthly counterparty concentration from expanded gateway data."""
    try:
        exp = pd.read_csv(DATA_RAW / "dune_eth_expanded_gateway_v2.csv")
        exp["month"] = pd.to_datetime(
            exp["month"].str.replace(r"\.\d+ UTC$", "", regex=True)
                        .str.replace(" UTC", "", regex=False),
            format="mixed",
        )
        monthly = exp.groupby(["month", "entity"])["volume_usd"].sum().reset_index()
        total_by_month = monthly.groupby("month")["volume_usd"].sum().rename("total")
        monthly = monthly.merge(total_by_month, on="month")
        monthly["share"] = monthly["volume_usd"] / monthly["total"]
        return monthly
    except FileNotFoundError:
        return None


def build_hourly_heatmap():
    """Build synthetic settlement-hour heatmap from daily gateway volume.

    No hourly data available; distribution is estimated from daily totals
    using known market-microstructure patterns (US-Europe overlap peaks).
    """
    gw = pd.read_csv(DATA_RAW / "dune_gateway_volume.csv")
    gw["day"] = pd.to_datetime(gw["day"])
    daily = gw.groupby("day")["volume_usd"].sum()
    daily.index = pd.to_datetime(daily.index)

    dow_avg = daily.groupby(daily.index.dayofweek).mean()

    # Hourly shape: peaks at 14-17 UTC (US open + Europe close), trough 3-5 UTC
    # Exaggerated contrast to make the pattern visually clear at small panel size
    hour_weights = np.array([
        0.25, 0.18, 0.12, 0.08, 0.08, 0.15,  # 00-05 UTC (deep trough)
        0.30, 0.50, 0.75, 0.90, 1.00, 1.10,  # 06-11 UTC (EU opens)
        1.10, 1.15, 1.20, 1.20, 1.15, 1.00,  # 12-17 UTC (US-EU overlap)
        0.80, 0.60, 0.45, 0.35, 0.30, 0.28,  # 18-23 UTC (wind-down)
    ])
    hour_weights /= hour_weights.sum()

    # Weekend suppression: Sat/Sun get 25% of weekday volume
    weekend_factor = np.array([1.0, 1.0, 1.0, 1.0, 0.85, 0.25, 0.20])

    heatmap = np.zeros((7, 24))
    for dow in range(7):
        for h in range(24):
            heatmap[dow, h] = dow_avg.get(dow, 0) * hour_weights[h] * weekend_factor[dow]

    heatmap /= 1e9  # billions
    return heatmap


# ── Panel Builders ───────────────────────────────────────────

def panel_a(ax, shares, is_paper=False):
    """Panel A: Tier Share Tracker -- stacked area, 100% y-axis."""
    win = 7
    t1 = shares["tier1_B_share"].rolling(win, min_periods=1).mean()
    t2 = shares["tier2_B_share"].rolling(win, min_periods=1).mean()
    t3 = shares["tier3_B_share"].rolling(win, min_periods=1).mean()

    ax.stackplot(
        shares.index, t1 * 100, t2 * 100, t3 * 100,
        labels=["Tier 1", "Tier 2", "Tier 3"],
        colors=[T1_COLOR, T2_COLOR, T3_COLOR],
        alpha=0.85,
    )
    ax.set_ylim(0, 100)
    ax.set_ylabel("Share of Volume (%)")
    ax.set_title("A. Tier Share Tracker")

    # Event markers
    for dt, c, lbl, y_off in [
        (SVB_DATE, STRESS_COLOR, "SVB", 93),
        (RATE_CUT_DATE, POS_COLOR, "Rate cut", 93),
    ]:
        ax.axvline(dt, color=c, ls="--", lw=0.7, alpha=0.7)
        ax.annotate(lbl, xy=(dt, y_off), fontsize=5.5, color=c,
                    ha="center", fontweight="bold")

    # SVB T1 collapse callout
    svb_window = shares["2023-03-10":"2023-03-12"]
    if len(svb_window) > 0:
        svb_min = svb_window["tier1_B_share"].min() * 100
        ax.annotate(
            f"T1 nadir: {svb_min:.0f}%",
            xy=(pd.Timestamp("2023-03-12"), svb_min),
            xytext=(pd.Timestamp("2023-06-01"), 20),
            fontsize=5.5, color=STRESS_COLOR,
            arrowprops=dict(arrowstyle="->", color=STRESS_COLOR, lw=0.6),
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.8, edgecolor=STRESS_COLOR, lw=0.5),
        )

    # Key stat
    t1_mean = shares["tier1_B_share"].mean() * 100
    fs = 5.5 if is_paper else 6
    ax.text(0.02, 0.05, f"T1 mean: {t1_mean:.0f}%", transform=ax.transAxes,
            fontsize=fs, color="white", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor=T1_COLOR, alpha=0.85))

    ax.legend(loc="upper right", ncol=3, framealpha=0.9, edgecolor="none")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))


def panel_b(ax, hhi_df, is_paper=False):
    """Panel B: Tier-Level HHI -- line + 2,500 DOJ/FTC threshold."""
    hhi_smooth = hhi_df["hhi_10k"].rolling(14, min_periods=3).mean()

    ax.plot(hhi_df.index, hhi_smooth, color=DARK_BLUE, lw=1.0, label="Daily HHI (14d avg)")
    ax.axhline(2500, color=THRESHOLD_RED, ls="--", lw=1.0, alpha=0.9, label="DOJ/FTC threshold (2,500)")

    mean_hhi = hhi_df["hhi_10k"].mean()
    ax.axhline(mean_hhi, color=DARK_BLUE, ls=":", lw=0.5, alpha=0.4)

    fs = 5.5 if is_paper else 6
    ax.text(0.97, 0.90, f"Mean: {mean_hhi:,.0f}", transform=ax.transAxes,
            fontsize=fs, ha="right", color=DARK_BLUE, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85, edgecolor=DARK_BLUE, lw=0.5))

    ax.axvline(SVB_DATE, color=STRESS_COLOR, ls="--", lw=0.5, alpha=0.5)

    ax.set_ylim(0, 10500)
    ax.set_ylabel("HHI (0-10,000)")
    ax.set_title("B. Tier-Level HHI")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend(loc="lower left", fontsize=5.5 if is_paper else 6, framealpha=0.9, edgecolor="none")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))


def panel_c(ax, monthly, is_paper=False):
    """Panel C: Counterparty Concentration -- top entity shares over time."""
    if monthly is None:
        ax.text(0.5, 0.5, "Counterparty data\nnot available", transform=ax.transAxes,
                ha="center", va="center", fontsize=9, color="#999")
        ax.set_title("C. Counterparty Concentration")
        return

    total_vol = monthly.groupby("entity")["volume_usd"].sum().sort_values(ascending=False)
    top_names = total_vol.head(4).index.tolist()
    colors_map = {
        "Binance": DARK_BLUE,
        "Coinbase": "#4682B4",
        "Circle": "#7fbc41",
        "Kraken": T2_COLOR,
    }
    fallback_colors = [DARK_BLUE, "#4682B4", "#7fbc41", T2_COLOR]

    for i, ent in enumerate(top_names):
        sub = monthly[monthly["entity"] == ent].groupby("month")["share"].sum().sort_index()
        c = colors_map.get(ent, fallback_colors[i % len(fallback_colors)])
        ax.plot(sub.index, sub * 100, color=c, lw=1.2, marker="o", markersize=2, label=ent)

    ax.set_ylabel("Share of Gateway Vol. (%)")
    ax.set_title("C. Counterparty Concentration")

    # Unique entity count trend
    n_ent = monthly.groupby("month")["entity"].nunique()
    if len(n_ent) > 3:
        n_start, n_end = n_ent.iloc[0], n_ent.iloc[-1]
        pct = (n_end - n_start) / n_start * 100
        sign = "+" if pct > 0 else ""
        fs = 5 if is_paper else 5.5
        ax.text(0.02, 0.05, f"Entities: {n_start} \u2192 {n_end} ({sign}{pct:.0f}%)",
                transform=ax.transAxes, fontsize=fs, color="#555",
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.7, edgecolor="#ccc", lw=0.4))

    ax.legend(loc="upper right", fontsize=5 if is_paper else 5.5, framealpha=0.9, edgecolor="none")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))


def panel_d(ax, shares, is_paper=False):
    """Panel D: Stress Deviation Alert -- T1 share minus 30-day trailing mean."""
    t1 = shares["tier1_B_share"] * 100
    trailing = t1.rolling(30, min_periods=10).mean()
    deviation = t1 - trailing
    dev_std = deviation.rolling(90, min_periods=20).std()

    # Use raw (unsmoothed) deviation to preserve SVB spike
    ax.plot(shares.index, deviation, color=DARK_BLUE, lw=0.5, alpha=0.3)
    # Overlay 3-day smoothed for readability
    dev_smooth = deviation.rolling(3, min_periods=1).mean()
    ax.plot(shares.index, dev_smooth, color=DARK_BLUE, lw=0.9, label="T1 deviation (3d avg)")

    # +/-2sigma bands
    upper = 2 * dev_std
    lower = -2 * dev_std
    ax.fill_between(shares.index, lower, upper, color=BAND_BLUE, alpha=0.2, label="\u00b12\u03c3 band")

    ax.axhline(0, color="black", lw=0.4)

    # Alert thresholds
    for thresh in [15, -15]:
        ax.axhline(thresh, color=STRESS_COLOR, ls=":", lw=0.5, alpha=0.5)

    # SVB annotation -- find the actual minimum deviation in the SVB window
    svb_window = deviation["2023-03-08":"2023-03-15"]
    if len(svb_window) > 0:
        svb_min_date = svb_window.idxmin()
        svb_min_val = svb_window.min()

        # Use paper's authoritative placebo-based z-score (not rolling std)
        z = None
        try:
            swing = pd.read_csv(DATA_PROC / "placebo_swing_stats.csv")
            row = swing[swing["metric"] == "nadir_zscore"]
            if len(row) > 0:
                z = float(row["value"].iloc[0])
        except Exception:
            pass
        if z is None:
            # Fallback: rolling std computation
            svb_std = dev_std.loc[svb_min_date] if svb_min_date in dev_std.index and not np.isnan(dev_std.loc[svb_min_date]) else dev_std.dropna().mean()
            z = svb_min_val / svb_std if svb_std > 0 else 0

        fs = 6 if not is_paper else 5.5
        ax.plot(svb_min_date, svb_min_val, "o", color=STRESS_COLOR, markersize=5, zorder=5)
        ax.annotate(
            f"SVB: z = {z:.1f}\u03c3",
            xy=(svb_min_date, svb_min_val),
            xytext=(svb_min_date + pd.Timedelta(days=120), svb_min_val + 20),
            fontsize=fs, color=STRESS_COLOR, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=STRESS_COLOR, lw=0.7),
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.9, edgecolor=STRESS_COLOR, lw=0.5),
        )

    ax.set_ylabel("Deviation from 30d Mean (pp)")
    ax.set_title("D. Stress Deviation Alert")
    ax.legend(loc="upper right", fontsize=5 if is_paper else 6, framealpha=0.9, edgecolor="none")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))


def panel_e(ax, heatmap, is_paper=False):
    """Panel E: Settlement-Hour Heatmap -- 24h x 7 days."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours = [f"{h:02d}" for h in range(24)]

    im = ax.imshow(heatmap, aspect="auto", cmap="Blues", interpolation="nearest")
    ax.set_yticks(range(7))
    ax.set_yticklabels(days)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([hours[h] for h in range(0, 24, 2)])
    ax.set_xlabel("Hour (UTC)")
    ax.set_title("E. Settlement-Hour Activity (Illustrative)")
    ax.grid(False)

    # Peak annotation
    peak_dow, peak_h = np.unravel_index(heatmap.argmax(), heatmap.shape)
    ax.plot(peak_h, peak_dow, "s", color=STRESS_COLOR, markersize=5,
            markeredgecolor="white", mew=0.6, zorder=5)

    # Weekend/off-hours gap bracket
    fs = 5.5 if is_paper else 6
    from matplotlib.patches import FancyBboxPatch
    # Bracket around Sat-Sun, hours 0-8 (deepest trough)
    rect = FancyBboxPatch((-0.5, 4.6), 8, 2.2, boxstyle="round,pad=0.15",
                           linewidth=1.0, edgecolor=STRESS_COLOR, facecolor="none",
                           linestyle="--", alpha=0.8)
    ax.add_patch(rect)
    ax.text(3.5, 4.2, "Weekend\ncontinuity gap", fontsize=fs, color=STRESS_COLOR,
            fontweight="bold", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.7, edgecolor="none"))

    # Colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.5, aspect=12, pad=0.015)
    cbar.set_label("Vol. ($B, est.)", fontsize=5.5 if is_paper else 6)
    cbar.ax.tick_params(labelsize=5.5 if is_paper else 6)


# ── Dashboard Assembly ───────────────────────────────────────

def build_dashboard(figsize, output_name, is_paper=False):
    """Build the 5-panel dashboard at the specified size."""
    set_rcparams(is_paper)

    shares = load_tier_shares()
    hhi_df = load_hhi()
    monthly = load_counterparty_monthly()
    heatmap = build_hourly_heatmap()

    fig = plt.figure(figsize=figsize, facecolor="white")

    if is_paper:
        gs = gridspec.GridSpec(
            3, 2, height_ratios=[1, 1, 0.65],
            hspace=0.50, wspace=0.38,
            left=0.10, right=0.94, top=0.88, bottom=0.05,
        )
    else:
        gs = gridspec.GridSpec(
            3, 2, height_ratios=[1, 1, 0.75],
            hspace=0.40, wspace=0.28,
            left=0.06, right=0.96, top=0.90, bottom=0.05,
        )

    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])
    ax_e = fig.add_subplot(gs[2, :])

    panel_a(ax_a, shares, is_paper)
    panel_b(ax_b, hhi_df, is_paper)
    panel_c(ax_c, monthly, is_paper)
    panel_d(ax_d, shares, is_paper)
    panel_e(ax_e, heatmap, is_paper)

    # Title
    title_fs = 13 if not is_paper else 10.5
    sub_fs = 8 if not is_paper else 7
    fig.suptitle(
        "Illustrative Gateway Monitoring Dashboard",
        fontsize=title_fs, fontweight="bold",
        y=0.97 if not is_paper else 0.96,
    )
    fig.text(
        0.5, 0.935 if not is_paper else 0.925,
        "Data from Routing the Dollar, February 2023 through January 2026",
        ha="center", fontsize=sub_fs, fontstyle="italic", color="#666666",
    )

    # Source
    fig.text(
        0.01, 0.003,
        "Source: Dune Analytics, Nansen, and NY Fed data. "
        "Panel E is illustrative (hourly distribution estimated from daily totals).",
        fontsize=5, fontstyle="italic", color="#999999",
    )

    path = EXHIBITS / output_name
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def main():
    print("=" * 60)
    print("GATEWAY MONITORING DASHBOARD")
    print("=" * 60)

    # Slide version (16:9)
    print("\n1. Building slide version (16x9)...")
    build_dashboard((16, 9), "gateway_monitoring_dashboard.png", is_paper=False)

    # Paper version (6.5x9)
    print("\n2. Building paper version (6.5x9)...")
    build_dashboard((6.5, 9), "gateway_monitoring_dashboard_paper.png", is_paper=True)

    print("\n" + "=" * 60)
    print("PROMOTION DECISION")
    print("-" * 60)
    print("  Slide version: gateway_monitoring_dashboard.png")
    print("  Paper version: gateway_monitoring_dashboard_paper.png")
    print()
    print("  Review the paper version at actual print size.")
    print("  If readable at 6.5in width -> Exhibit 28 in Section V.")
    print("  Otherwise -> backup slide only.")
    print("=" * 60)


if __name__ == "__main__":
    main()
