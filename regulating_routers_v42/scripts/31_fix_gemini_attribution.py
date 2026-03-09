"""31_fix_gemini_attribution.py — Fix Gemini/Binance address mislabeling.

Root cause: The codex_package Dune query used address 0x21a31ee1afc51d94c2efccaa2092ad1028285549
labeled as "Gemini" (Tier 1). This address is actually "Binance 36" per Etherscan, Dune, and
Arkham entity labels. The expanded registry already has it correctly as Binance.

Impact: All "Gemini" volume in the original 12-address data is actually Binance. This moves
substantial volume from Tier 1 to Tier 2, significantly changing tier shares, HHI, and the
"Circle-Gemini duopoly" narrative.

Steps:
  1. Relabel "Gemini" -> "Binance" and Tier1 -> Tier2 in exhibit_A_gateway_transfers.csv
  2. Recompute exhibit_C_gateway_concentration.csv from corrected exhibit_A
  3. Recompute original-data metrics (tier shares, HHI, SVB retention, tier correlations)
  4. Regenerate exhibits 8 and 10
"""
import pandas as pd, numpy as np, json, sys
from pathlib import Path
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json, save_csv

MEDIA = Path(__file__).resolve().parent.parent / "media"
MEDIA.mkdir(parents=True, exist_ok=True)


def fix_exhibit_A():
    """Relabel Gemini -> Binance (Tier2) in exhibit_A raw data."""
    print("=" * 70)
    print("STEP 1: Fix exhibit_A_gateway_transfers.csv")
    print("=" * 70)

    a = pd.read_csv(DATA_RAW / "exhibit_A_gateway_transfers.csv")

    # Count before
    gemini_rows = (a["gateway"] == "Gemini").sum()
    binance_rows = (a["gateway"] == "Binance").sum()
    print(f"  Before: Gemini rows={gemini_rows}, Binance rows={binance_rows}")

    # Relabel
    mask = a["gateway"] == "Gemini"
    a.loc[mask, "gateway"] = "Binance"
    a.loc[mask, "tier"] = "Tier2"

    # Count after
    binance_after = (a["gateway"] == "Binance").sum()
    gemini_after = (a["gateway"] == "Gemini").sum()
    print(f"  After:  Gemini rows={gemini_after}, Binance rows={binance_after}")
    print(f"  Moved {gemini_rows} rows from Gemini(Tier1) to Binance(Tier2)")

    # Save corrected file
    a.to_csv(DATA_RAW / "exhibit_A_gateway_transfers.csv", index=False)
    print(f"  Saved: {DATA_RAW / 'exhibit_A_gateway_transfers.csv'}")

    return a


def recompute_exhibit_C(a):
    """Recompute exhibit_C tier aggregations from corrected exhibit_A."""
    print("\n" + "=" * 70)
    print("STEP 2: Recompute exhibit_C_gateway_concentration.csv")
    print("=" * 70)

    a["date"] = pd.to_datetime(a["date"], utc=True).dt.tz_localize(None)
    a["total_vol"] = a["inflow_usd"].abs() + a["outflow_usd"].abs()

    # Daily volume by tier
    daily_tier = a.groupby(["date", "tier"])["total_vol"].sum().reset_index()
    daily_total = a.groupby("date")["total_vol"].sum().reset_index()
    daily_total.columns = ["date", "day_total"]

    merged = daily_tier.merge(daily_total, on="date")
    merged["share_pct"] = merged["total_vol"] / merged["day_total"] * 100
    merged["hhi_component"] = (merged["share_pct"]) ** 2

    # Rename columns to match original format
    out = merged[["date", "hhi_component", "share_pct", "tier", "total_vol"]].copy()
    out.columns = ["date", "hhi_component", "share_pct", "tier", "volume_usd"]

    # Convert dates back to UTC string format
    out["date"] = out["date"].dt.strftime("%Y-%m-%d %H:%M:%S.000 UTC")
    out = out.sort_values(["date", "tier"]).reset_index(drop=True)

    out.to_csv(DATA_RAW / "exhibit_C_gateway_concentration.csv", index=False)
    print(f"  Saved: {DATA_RAW / 'exhibit_C_gateway_concentration.csv'}")

    # Validate
    c = out.copy()
    c["date_dt"] = pd.to_datetime(c["date"])
    for tier in ["Tier1", "Tier2", "Tier3"]:
        sub = c[c["tier"] == tier]
        mean_share = sub["share_pct"].mean()
        print(f"  {tier} mean share: {mean_share:.1f}%")

    daily_hhi = c.groupby("date_dt")["hhi_component"].sum()
    print(f"  HHI mean: {daily_hhi.mean():,.0f}")
    print(f"  HHI range: {daily_hhi.min():,.0f} - {daily_hhi.max():,.0f}")

    return out


def recompute_metrics(a_raw):
    """Recompute original-data metrics with corrected attribution."""
    print("\n" + "=" * 70)
    print("STEP 3: Recompute Original-Data Metrics")
    print("=" * 70)

    a = a_raw.copy()
    a["date"] = pd.to_datetime(a["date"], utc=True).dt.tz_localize(None)
    a["total_vol"] = a["inflow_usd"].abs() + a["outflow_usd"].abs()

    results = {}

    # --- Entity-level summary ---
    entity_vol = a.groupby(["gateway", "tier"])["total_vol"].sum().reset_index()
    total = entity_vol["total_vol"].sum()
    entity_vol["share_pct"] = entity_vol["total_vol"] / total * 100
    entity_vol = entity_vol.sort_values("total_vol", ascending=False)

    print(f"\n  Entity volumes (corrected, 12-address data):")
    print(f"  {'Gateway':25s} {'Tier':5s} {'Volume':>12s} {'Share':>7s}")
    for _, row in entity_vol.iterrows():
        print(f"  {row['gateway']:25s} {row['tier']:5s} ${row['total_vol']/1e9:>9.1f}B {row['share_pct']:>6.1f}%")
    results["entity_volumes"] = {
        row["gateway"]: {"tier": row["tier"], "volume_B": round(row["total_vol"] / 1e9, 1),
                         "share_pct": round(row["share_pct"], 1)}
        for _, row in entity_vol.iterrows()
    }

    # --- Tier shares ---
    tier_vol = a.groupby("tier")["total_vol"].sum()
    t1 = tier_vol.get("Tier1", 0) / total * 100
    t2 = tier_vol.get("Tier2", 0) / total * 100
    t3 = tier_vol.get("Tier3", 0) / total * 100
    results["tier_shares"] = {"Tier1": round(t1, 1), "Tier2": round(t2, 1), "Tier3": round(t3, 1)}
    print(f"\n  Tier shares: T1={t1:.1f}%, T2={t2:.1f}%, T3={t3:.1f}%")
    print(f"  (Before fix: T1=81.6%, T2=9.7%, T3=8.7%)")

    # --- Within-Tier 1 ---
    t1_entities = entity_vol[entity_vol["tier"] == "Tier1"]
    t1_total = t1_entities["total_vol"].sum()
    within = {}
    for _, row in t1_entities.iterrows():
        within[row["gateway"]] = round(row["total_vol"] / t1_total * 100, 1) if t1_total > 0 else 0
    results["within_tier1"] = within
    print(f"\n  Within Tier 1: {within}")

    # --- Entity-level HHI ---
    shares = entity_vol["total_vol"] / total * 100
    hhi_entity = (shares ** 2).sum()
    results["hhi_entity"] = round(hhi_entity)
    print(f"\n  Entity HHI: {hhi_entity:.0f} (before fix: 4,849)")

    # --- Tier-level HHI ---
    tier_shares_sq = pd.Series({"Tier1": t1, "Tier2": t2, "Tier3": t3})
    hhi_tier = (tier_shares_sq ** 2).sum()
    results["hhi_tier_mean"] = round(hhi_tier)
    print(f"  Tier HHI (static): {hhi_tier:.0f} (before fix: 7,361)")

    # --- Daily HHI ---
    daily_tier_vol = a.groupby(["date", "tier"])["total_vol"].sum().unstack(fill_value=0)
    daily_total = daily_tier_vol.sum(axis=1).replace(0, np.nan)
    daily_shares = daily_tier_vol.div(daily_total, axis=0).fillna(0) * 100
    daily_hhi = (daily_shares ** 2).sum(axis=1)
    results["daily_hhi_mean"] = round(daily_hhi.mean())
    results["daily_hhi_median"] = round(daily_hhi.median())
    print(f"  Daily HHI: mean={daily_hhi.mean():,.0f}, median={daily_hhi.median():,.0f}")

    # --- SVB flow retention ---
    stress = a[(a["date"] >= "2023-03-08") & (a["date"] <= "2023-03-15")]
    normal = a[(a["date"] < "2023-03-08") | (a["date"] > "2023-03-15")]
    stress_total = stress["total_vol"].sum()
    normal_total = normal["total_vol"].sum()
    stress_shares = stress.groupby("gateway")["total_vol"].sum() / stress_total
    normal_shares = normal.groupby("gateway")["total_vol"].sum() / normal_total
    retention = {}
    for gw in normal_shares.index:
        if gw in stress_shares.index:
            n = float(normal_shares[gw])
            s = float(stress_shares[gw])
            if n > 0.001:
                retention[gw] = round(s / n, 2)
    results["svb_retention"] = retention
    print(f"\n  SVB retention (corrected):")
    for gw, r in sorted(retention.items(), key=lambda x: -x[1]):
        print(f"    {gw}: {r:.2f}x")

    # --- Tier correlations ---
    try:
        fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
        daily_tier_shares = daily_shares / 100  # back to 0-1
        weekly_shares = daily_tier_shares.resample("W-WED").mean()
        weekly_fred = fred[["WSHOMCB"]].resample("W-WED").last()
        merged = weekly_shares.join(weekly_fred, how="inner").dropna()
        tier_corr = {}
        for tc in ["Tier1", "Tier2", "Tier3"]:
            if tc in merged.columns:
                r, p = stats.pearsonr(merged[tc], merged["WSHOMCB"])
                tier_corr[tc] = {"r": round(r, 4), "p": round(p, 4)}
                print(f"  Tier correlation: {tc} vs Fed Assets: r={r:.4f}, p={p:.4f}")
        results["tier_correlations"] = tier_corr
    except Exception as e:
        print(f"  Tier correlations: {e}")

    save_json(results, "gemini_fix_original_metrics.json")
    return results


def regenerate_exhibits():
    """Regenerate exhibits 8 and 10 from corrected exhibit_C data."""
    print("\n" + "=" * 70)
    print("STEP 4: Regenerate Exhibits 8 and 10")
    print("=" * 70)

    src = DATA_RAW / "exhibit_C_gateway_concentration.csv"
    c = pd.read_csv(src)
    c["date"] = pd.to_datetime(c["date"], utc=True).dt.tz_localize(None)

    # ── Exhibit 8: Gateway Transfer Volume by Tier ──
    print("  Generating Exhibit 8...")
    daily_vol = c.pivot_table(index="date", columns="tier",
                              values="volume_usd", aggfunc="sum").fillna(0).sort_index()
    daily_share = c.pivot_table(index="date", columns="tier",
                                values="share_pct", aggfunc="sum").fillna(0).sort_index()

    dates = daily_vol.index
    t1_vol = (daily_vol.get("Tier1", 0) / 1e9).rolling(7, min_periods=1).mean()
    t2_vol = (daily_vol.get("Tier2", 0) / 1e9).rolling(7, min_periods=1).mean()
    t3_vol = (daily_vol.get("Tier3", 0) / 1e9).rolling(7, min_periods=1).mean()

    t1_share_raw = daily_share.get("Tier1", pd.Series(0, index=dates))
    t1_share_rolling = t1_share_raw.rolling(7, min_periods=1).mean()
    mean_share = t1_share_raw.mean()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True)

    ax1.plot(dates, t1_vol, color="#003366", linewidth=2.0, label="Tier 1 (Regulated)")
    ax1.plot(dates, t2_vol, color="#d68910", linewidth=1.5, label="Tier 2 (Offshore)")
    ax1.plot(dates, t3_vol, color="#145a32", linewidth=1.5, label="Tier 3 (DeFi)")
    ax1.axvline(pd.Timestamp("2023-03-10"), color="#CC3333", linestyle="--", linewidth=1.2, alpha=0.7)
    ymax = ax1.get_ylim()[1]
    ax1.text(pd.Timestamp("2023-03-12"), ymax * 0.88, " SVB",
             color="#CC3333", fontsize=9, fontweight="bold")
    ax1.set_ylabel("Gateway Volume ($B, 7-day avg)")
    ax1.set_ylim(bottom=0)
    ax1.legend(loc="upper right", fontsize=9)
    ax1.set_title("Gateway Transfer Volume by Tier", fontweight="bold", fontsize=11)

    ax2.fill_between(dates, 0, t1_share_rolling, color="#003366", alpha=0.3)
    ax2.plot(dates, t1_share_rolling, color="#003366", linewidth=1.5)
    ax2.axhline(mean_share, color="#666666", linestyle="--", linewidth=1.0, alpha=0.8)
    ax2.text(dates[-1], mean_share + 1.5, f"Mean: {mean_share:.1f}%",
             fontsize=9, ha="right", color="#666666")
    ax2.axvline(pd.Timestamp("2023-03-10"), color="#CC3333", linestyle="--", linewidth=1.2, alpha=0.7)
    ax2.set_ylabel("Tier 1 Share (%)")
    ax2.set_ylim(0, 100)
    ax2.set_title("Tier 1 Volume Share", fontweight="bold", fontsize=11)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    fig.suptitle("Gateway Transfer Volume by Tier",
                 fontweight="bold", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(MEDIA / "exhibit08_gateway_volume_by_tier.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"    exhibit08 [T1 mean share: {mean_share:.1f}%]")

    # ── Exhibit 10: Gateway Concentration & HHI ──
    print("  Generating Exhibit 10...")
    t1_frac = daily_share.get("Tier1", 0) / 100
    t2_frac = daily_share.get("Tier2", 0) / 100
    t3_frac = daily_share.get("Tier3", 0) / 100
    daily_hhi = c.groupby("date")["hhi_component"].sum().sort_index()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True)

    ax1.stackplot(daily_share.index, t1_frac, t2_frac, t3_frac,
                  labels=["Tier 1 (Regulated)", "Tier 2 (Offshore)", "Tier 3 (DeFi)"],
                  colors=["#1a5276", "#d68910", "#145a32"], alpha=0.8)
    ax1.axvspan(pd.Timestamp("2023-03-08"), pd.Timestamp("2023-03-15"),
                color="#ffcccc", alpha=0.2, label="SVB Crisis")
    ax1.set_ylabel("Share of Volume")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f"{x*100:.0f}%"))
    ax1.set_ylim(0, 1)
    ax1.legend(loc="lower left", fontsize=9)
    ax1.set_title("Gateway Tier Volume Shares", fontweight="bold", fontsize=11)

    hhi_rolling = daily_hhi.rolling(7, min_periods=1).mean()
    hhi_mean = daily_hhi.mean()

    ax2.plot(daily_hhi.index, hhi_rolling, color="#003366", linewidth=1.5, label="HHI (7-day avg)")
    ax2.axhline(2500, color="#CC3333", linestyle=":", linewidth=1.2, alpha=0.7)
    ax2.text(daily_hhi.index[10], 2700, "DOJ/FTC Threshold (2,500)",
             fontsize=8, color="#CC3333", fontstyle="italic")
    ax2.axhline(hhi_mean, color="#666666", linestyle="--", linewidth=0.8, alpha=0.6)
    ax2.text(daily_hhi.index[-1], hhi_mean + 150, f"Mean: {hhi_mean:,.0f}",
             fontsize=8, ha="right", color="#666666")
    ax2.axvspan(pd.Timestamp("2023-03-08"), pd.Timestamp("2023-03-15"),
                color="#ffcccc", alpha=0.2)
    ax2.set_ylabel("Herfindahl-Hirschman Index")
    ax2.set_ylim(0, 10000)
    ax2.legend(loc="upper right", fontsize=9)
    ax2.set_title("Gateway Routing Concentration (HHI)", fontweight="bold", fontsize=11)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    fig.suptitle("Gateway Routing Concentration by Tier and HHI",
                 fontweight="bold", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(MEDIA / "exhibit10_gateway_concentration_hhi.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"    exhibit10 [HHI mean: {hhi_mean:,.0f}]")

    return mean_share, hhi_mean


def update_paper_claims(metrics, t1_share_mean, hhi_mean):
    """Update paper_claims_update.json with corrected baseline."""
    print("\n" + "=" * 70)
    print("STEP 5: Update Paper Claims")
    print("=" * 70)

    # Load existing claims
    try:
        with open(DATA_PROC / "paper_claims_update.json") as f:
            claims = json.load(f)
    except FileNotFoundError:
        claims = {"claims": [], "generated": "2026-02-13"}

    # Add Gemini fix context
    claims["gemini_fix"] = {
        "description": (
            "Address 0x21a31ee1afc51d94c2efccaa2092ad1028285549 was labeled 'Gemini' in the "
            "original codex_package Dune query but is confirmed as 'Binance 36' on Etherscan, "
            "Dune labels, and Arkham Intelligence. All volume previously attributed to Gemini "
            "in the 12-address original data has been relabeled to Binance and moved from "
            "Tier 1 to Tier 2."
        ),
        "impact_on_original_data": {
            "tier1_share_before": 81.6,
            "tier1_share_after": metrics["tier_shares"]["Tier1"],
            "tier2_share_before": 9.7,
            "tier2_share_after": metrics["tier_shares"]["Tier2"],
            "gemini_volume": "Moved to Binance (Tier 2)",
            "circle_within_tier1": metrics["within_tier1"].get("Circle", "?"),
            "daily_hhi_mean": round(hhi_mean),
        },
        "key_consequence": (
            "The 'Circle-Gemini duopoly' (99.4% of Tier 1) was actually Circle + Binance leakage. "
            f"After correction, Circle alone is {metrics['within_tier1'].get('Circle', '?')}% of Tier 1. "
            "Tier 1 share drops from 81.6% because the mislabeled Binance volume moved to Tier 2."
        ),
    }

    # Update individual claims
    ts = metrics["tier_shares"]
    for claim in claims.get("claims", []):
        if "Tier 1 volume share" in claim.get("claim", ""):
            claim["new_value"] = f"{ts['Tier1']}% (corrected from Gemini fix)"
            claim["action"] = (
                f"Tier 1 share is now {ts['Tier1']}% after correcting Gemini->Binance attribution. "
                f"Tier 2 rises to {ts['Tier2']}%. The Gemini mislabel inflated Tier 1 by ~{81.6 - ts['Tier1']:.0f}pp."
            )
        if "Circle and Gemini" in claim.get("claim", ""):
            claim["new_value"] = f"Circle alone: {metrics['within_tier1'].get('Circle', '?')}% of Tier 1"
            claim["action"] = (
                "The 'duopoly' was an artifact of Binance address mislabeling. Gemini has ~$0 volume. "
                f"Circle is {metrics['within_tier1'].get('Circle', '?')}% of Tier 1 after correction."
            )

    save_json(claims, "paper_claims_update.json")

    # Print summary
    print(f"  Original Tier 1 share: 81.6% -> Corrected: {ts['Tier1']}%")
    print(f"  Original Tier 2 share:  9.7% -> Corrected: {ts['Tier2']}%")
    print(f"  Circle within Tier 1: {metrics['within_tier1'].get('Circle', '?')}%")
    print(f"  Daily HHI mean: {hhi_mean:,.0f}")
    print(f"  Entity HHI: {metrics['hhi_entity']}")


def main():
    print("=" * 70)
    print("FIX GEMINI ATTRIBUTION")
    print("(Address 0x21a31... is Binance 36, not Gemini)")
    print("=" * 70)

    # Step 1: Fix raw data
    a = fix_exhibit_A()

    # Step 2: Recompute exhibit_C
    recompute_exhibit_C(a)

    # Step 3: Recompute metrics
    # Re-read from corrected file for clean state
    a_fresh = pd.read_csv(DATA_RAW / "exhibit_A_gateway_transfers.csv")
    metrics = recompute_metrics(a_fresh)

    # Step 4: Regenerate exhibits
    t1_share_mean, hhi_mean = regenerate_exhibits()

    # Step 5: Update claims
    update_paper_claims(metrics, t1_share_mean, hhi_mean)

    print("\n" + "=" * 70)
    print("GEMINI FIX COMPLETE")
    print("=" * 70)
    print("  Files modified:")
    print("    data/raw/exhibit_A_gateway_transfers.csv  (Gemini->Binance, Tier1->Tier2)")
    print("    data/raw/exhibit_C_gateway_concentration.csv  (recomputed tier aggregations)")
    print("    data/processed/gemini_fix_original_metrics.json  (corrected metrics)")
    print("    data/processed/paper_claims_update.json  (updated claims)")
    print("    media/exhibit08_gateway_volume_by_tier.png  (regenerated)")
    print("    media/exhibit10_gateway_concentration_hhi.png  (regenerated)")


if __name__ == "__main__":
    main()
