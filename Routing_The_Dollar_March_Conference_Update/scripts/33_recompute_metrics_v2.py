"""33_recompute_metrics_v2.py — Recompute all metrics from daily expanded data.

Reads dune_eth_daily_expanded_v2.csv and produces:
  - gateway_volume_summary_v2.csv (entity-level volumes)
  - exhibit_C1_gateway_shares_daily_v2.csv (daily tier shares)
  - exhibit_C2_concentration_daily_v2.csv (daily HHI)
  - svb_retention_v2.json
  - tier_correlations_v2.json
  - metrics_comparison_v2.json
"""
import pandas as pd, numpy as np, json, sys
from pathlib import Path
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json, save_csv

# Entity -> tier mapping (canonical)
ENTITY_TIERS = {
    "Circle": 1, "Coinbase": 1, "Paxos": 1, "Gemini": 1, "PayPal": 1, "BitGo": 1,
    "Tether": 2, "Binance": 2, "Kraken": 2, "OKX": 2, "Bybit": 2, "Robinhood": 2,
    "Uniswap V3": 3, "Uniswap Universal Router": 3, "Curve 3pool": 3,
    "Aave V3": 3, "1inch": 3, "Compound V3": 3, "Tornado Cash": 3,
}


def load_daily_data():
    """Load expanded daily data from Dune."""
    path = DATA_RAW / "dune_eth_daily_expanded_v2.csv"
    if not path.exists():
        print("ERROR: dune_eth_daily_expanded_v2.csv not found. Run 32_dune_daily_expanded.py first.")
        sys.exit(1)
    df = pd.read_csv(path)
    df["day"] = pd.to_datetime(df["day"])
    df["tier"] = df["entity"].map(ENTITY_TIERS).fillna(df.get("tier", 3)).astype(int)
    print(f"Loaded {len(df)} rows, {df['entity'].nunique()} entities")
    print(f"Date range: {df['day'].min().date()} to {df['day'].max().date()}")
    print(f"Total volume: ${df['volume_usd'].sum() / 1e12:.2f}T")
    return df


def entity_volume_summary(df):
    """3a: Entity-level volume summary."""
    print("\n" + "=" * 70)
    print("3a: Entity-Level Volume Summary")
    print("=" * 70)
    by_entity = df.groupby(["entity", "tier"]).agg(
        total_volume=("volume_usd", "sum"),
        n_transfers=("n_transfers", "sum"),
    ).reset_index()
    total = by_entity["total_volume"].sum()
    by_entity["share_pct"] = by_entity["total_volume"] / total * 100
    # Count addresses per entity from registry
    try:
        registry = pd.read_csv(DATA_PROC.parent / "data" / "processed" / "gateway_registry_expanded.csv")
    except:
        registry = pd.read_csv(Path(__file__).resolve().parent.parent / "data" / "processed" / "gateway_registry_expanded.csv")
    addr_counts = registry.groupby("entity").size().to_dict()
    by_entity["n_addresses"] = by_entity["entity"].map(addr_counts).fillna(0).astype(int)
    by_entity = by_entity.sort_values("total_volume", ascending=False)
    save_csv(by_entity.set_index("entity"), "gateway_volume_summary_v2.csv")

    print(f"\n  {'Entity':30s} {'Tier':4s} {'Volume':>12s} {'Share':>7s} {'Addrs':>5s}")
    for _, r in by_entity.iterrows():
        print(f"  {r['entity']:30s} T{r['tier']:<3d} ${r['total_volume']/1e9:>9.1f}B {r['share_pct']:>6.1f}% {r['n_addresses']:>4d}")
    return by_entity


def tier_share_timeseries(df):
    """3b: Daily tier share time series for Exhibit 8."""
    print("\n" + "=" * 70)
    print("3b: Daily Tier Shares")
    print("=" * 70)
    daily_tier = df.groupby(["day", "tier"])["volume_usd"].sum().unstack(fill_value=0)
    daily_total = daily_tier.sum(axis=1).replace(0, np.nan)
    daily_shares = daily_tier.div(daily_total, axis=0).fillna(0) * 100
    daily_shares.columns = [f"tier{c}_share_pct" for c in daily_shares.columns]
    daily_shares["total_volume"] = daily_total
    save_csv(daily_shares, "exhibit_C1_gateway_shares_daily_v2.csv")

    for c in daily_shares.columns:
        if "share" in c:
            print(f"  {c}: mean={daily_shares[c].mean():.1f}%, median={daily_shares[c].median():.1f}%")
    return daily_shares


def hhi_timeseries(df):
    """3c: Daily HHI time series for Exhibit 10."""
    print("\n" + "=" * 70)
    print("3c: Daily HHI")
    print("=" * 70)
    # Tier-level HHI
    daily_tier = df.groupby(["day", "tier"])["volume_usd"].sum().unstack(fill_value=0)
    daily_total = daily_tier.sum(axis=1).replace(0, np.nan)
    tier_shares = daily_tier.div(daily_total, axis=0).fillna(0) * 100
    tier_hhi = (tier_shares ** 2).sum(axis=1)

    # Entity-level HHI
    daily_entity = df.groupby(["day", "entity"])["volume_usd"].sum().unstack(fill_value=0)
    entity_total = daily_entity.sum(axis=1).replace(0, np.nan)
    entity_shares = daily_entity.div(entity_total, axis=0).fillna(0) * 100
    entity_hhi = (entity_shares ** 2).sum(axis=1)

    result = pd.DataFrame({
        "tier_hhi": tier_hhi,
        "entity_hhi": entity_hhi,
        "total_volume": daily_total,
    })
    save_csv(result, "exhibit_C2_concentration_daily_v2.csv")

    print(f"  Tier HHI:   mean={tier_hhi.mean():,.0f}, median={tier_hhi.median():,.0f}")
    print(f"  Entity HHI: mean={entity_hhi.mean():,.0f}, median={entity_hhi.median():,.0f}")
    print(f"  Entity HHI > 2500: {(entity_hhi > 2500).sum()}/{len(entity_hhi)} days")
    return result


def svb_retention(df):
    """3d: SVB stress window retention ratios."""
    print("\n" + "=" * 70)
    print("3d: SVB Stress Window (March 9-15, 2023)")
    print("=" * 70)
    stress = df[(df["day"] >= "2023-03-09") & (df["day"] <= "2023-03-15")]
    normal = df[(df["day"] >= "2023-02-09") & (df["day"] < "2023-03-08")]

    stress_days = stress["day"].nunique()
    normal_days = normal["day"].nunique()

    stress_vol = stress.groupby("entity")["volume_usd"].sum()
    normal_vol = normal.groupby("entity")["volume_usd"].sum()

    # Average daily volume
    stress_avg = stress_vol / max(stress_days, 1)
    normal_avg = normal_vol / max(normal_days, 1)

    retention = {}
    for entity in sorted(set(stress_vol.index) | set(normal_vol.index)):
        s = stress_avg.get(entity, 0)
        n = normal_avg.get(entity, 0)
        if n > 1_000_000:  # Only entities with material normal volume
            retention[entity] = {
                "retention": round(s / n, 2),
                "stress_daily_avg_B": round(s / 1e9, 2),
                "normal_daily_avg_B": round(n / 1e9, 2),
                "tier": ENTITY_TIERS.get(entity, 0),
            }

    # Sort by retention ratio
    retention = dict(sorted(retention.items(), key=lambda x: -x[1]["retention"]))

    results = {
        "stress_window": "2023-03-09 to 2023-03-15",
        "normal_window": "2023-02-09 to 2023-03-08",
        "stress_days": stress_days,
        "normal_days": normal_days,
        "retention_by_entity": retention,
    }
    save_json(results, "svb_retention_v2.json")

    print(f"  {'Entity':30s} {'Retention':>10s} {'Normal $/day':>14s} {'Stress $/day':>14s} {'Tier':>4s}")
    for entity, data in retention.items():
        print(f"  {entity:30s} {data['retention']:>9.2f}x ${data['normal_daily_avg_B']:>10.1f}B ${data['stress_daily_avg_B']:>10.1f}B T{data['tier']}")
    return results


def tier_correlations(df):
    """3e: Tier-level correlations with Fed assets."""
    print("\n" + "=" * 70)
    print("3e: Tier-Level Correlations with Fed Assets")
    print("=" * 70)
    try:
        fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
    except FileNotFoundError:
        print("  WARNING: fred_wide.csv not found. Skipping correlations.")
        return {}

    # Daily gateway tier volumes -> weekly
    daily_tier = df.groupby(["day", "tier"])["volume_usd"].sum().unstack(fill_value=0)
    daily_total = daily_tier.sum(axis=1).replace(0, np.nan)
    daily_shares = daily_tier.div(daily_total, axis=0).fillna(0)

    # Normalize timezones
    if daily_shares.index.tz is not None:
        daily_shares.index = daily_shares.index.tz_localize(None)

    weekly_shares = daily_shares.resample("W-WED").mean()
    weekly_fed = fred[["WSHOMCB"]].resample("W-WED").last()
    if weekly_fed.index.tz is not None:
        weekly_fed.index = weekly_fed.index.tz_localize(None)

    merged = weekly_shares.join(weekly_fed, how="inner").dropna()

    results = {}
    for tier in sorted(daily_tier.columns):
        col = tier
        if col in merged.columns:
            r, p = stats.pearsonr(merged[col], merged["WSHOMCB"])
            results[f"Tier{tier}"] = {"r": round(r, 4), "p": round(p, 4), "n": len(merged)}
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            print(f"  Tier {tier} vs Fed Assets: r={r:.4f}, p={p:.4f}{sig} (n={len(merged)})")

    save_json(results, "tier_correlations_v2.json")
    return results


def usdt_through_tier1(df):
    """3f: USDT volume through Tier 1 entities."""
    print("\n" + "=" * 70)
    print("3f: USDT Through Tier 1")
    print("=" * 70)
    usdt = df[df["token"] == "USDT"]
    total_usdt = usdt["volume_usd"].sum()
    t1_usdt = usdt[usdt["tier"] == 1]["volume_usd"].sum()
    pct = t1_usdt / total_usdt * 100 if total_usdt > 0 else 0

    # Breakdown by entity
    usdt_by_entity = usdt.groupby("entity")["volume_usd"].sum().sort_values(ascending=False)
    print(f"  Total USDT gateway volume: ${total_usdt / 1e9:,.1f}B")
    print(f"  Tier 1 USDT volume: ${t1_usdt / 1e9:,.1f}B ({pct:.1f}%)")
    print(f"  Top USDT entities:")
    for entity, vol in usdt_by_entity.head(8).items():
        tier = ENTITY_TIERS.get(entity, 0)
        print(f"    {entity} (T{tier}): ${vol / 1e9:,.1f}B ({vol / total_usdt * 100:.1f}%)")

    return {"total_usdt_B": round(total_usdt / 1e9, 1),
            "tier1_usdt_B": round(t1_usdt / 1e9, 1),
            "tier1_usdt_pct": round(pct, 1)}


def coverage_ratio(df):
    """3g: Coverage ratio vs total Ethereum volume."""
    print("\n" + "=" * 70)
    print("3g: Coverage Ratio")
    print("=" * 70)
    gateway_total = df["volume_usd"].sum()

    # Try to get total Ethereum volume
    try:
        total_eth = pd.read_csv(DATA_RAW / "dune_eth_total_v2.csv")
        eth_total = total_eth["volume_usd"].sum()
    except FileNotFoundError:
        # Use the known total from previous session: $27.95T
        eth_total = 27.95e12
        print("  Using cached total Ethereum volume: $27.95T")

    coverage = gateway_total / eth_total * 100

    print(f"  Gateway volume: ${gateway_total / 1e12:.2f}T")
    print(f"  Total Ethereum volume: ${eth_total / 1e12:.2f}T")
    print(f"  Coverage ratio: {coverage:.1f}%")

    return {"gateway_vol_T": round(gateway_total / 1e12, 2),
            "total_eth_vol_T": round(eth_total / 1e12, 2),
            "coverage_pct": round(coverage, 1)}


def within_tier1(df):
    """3h: Within-Tier-1 concentration."""
    print("\n" + "=" * 70)
    print("3h: Within-Tier-1 Concentration")
    print("=" * 70)
    t1 = df[df["tier"] == 1]
    t1_total = t1["volume_usd"].sum()
    by_entity = t1.groupby("entity")["volume_usd"].sum().sort_values(ascending=False)

    result = {}
    for entity, vol in by_entity.items():
        pct = vol / t1_total * 100
        result[entity] = round(pct, 1)
        print(f"  {entity}: {pct:.1f}%")

    top2 = list(by_entity.head(2).index)
    top2_pct = by_entity.head(2).sum() / t1_total * 100
    print(f"  Top 2 ({'+'.join(top2)}): {top2_pct:.1f}%")

    return result


def build_comparison(entity_summary, tier_shares, hhi_ts, svb, tier_corr, usdt_t1, coverage, within_t1):
    """Build metrics_comparison_v2.json."""
    print("\n" + "=" * 70)
    print("METRICS COMPARISON")
    print("=" * 70)

    tier_share_means = {}
    for c in tier_shares.columns:
        if "share" in c:
            tier_share_means[c] = round(tier_shares[c].mean(), 1)

    comparison = {
        "generated": pd.Timestamp.now().isoformat(),
        "data_source": "dune_eth_daily_expanded_v2.csv (51 addresses, 19 entities, daily granularity)",
        "metrics": {
            "tier1_share": {
                "original_12addr": 82.0,
                "original_corrected": 62.3,
                "expanded_monthly": 42.0,
                "expanded_daily": tier_share_means.get("tier1_share_pct", None),
                "paper_location": "Throughout paper",
                "revision_needed": True,
            },
            "tier2_share": {
                "original_12addr": 10.0,
                "original_corrected": 31.9,
                "expanded_monthly": 55.0,
                "expanded_daily": tier_share_means.get("tier2_share_pct", None),
                "paper_location": "Throughout paper",
                "revision_needed": True,
            },
            "tier3_share": {
                "original_12addr": 8.0,
                "expanded_monthly": 3.0,
                "expanded_daily": tier_share_means.get("tier3_share_pct", None),
                "paper_location": "Throughout paper",
                "revision_needed": True,
            },
            "within_tier1_circle": {
                "original_12addr": 76.4,
                "expanded_monthly": 43.5,
                "expanded_daily": within_t1.get("Circle", None),
                "paper_location": "Intro, V.C",
                "revision_needed": True,
            },
            "within_tier1_coinbase": {
                "original_12addr": "<0.1%",
                "expanded_monthly": 56.4,
                "expanded_daily": within_t1.get("Coinbase", None),
                "paper_location": "V.C (was 'negligible')",
                "revision_needed": True,
            },
            "within_tier1_gemini": {
                "original_12addr": 23.1,
                "expanded_monthly": 0.0,
                "expanded_daily": within_t1.get("Gemini", 0.0),
                "paper_location": "DELETE — was Binance",
                "revision_needed": True,
            },
            "entity_hhi_mean": {
                "original_12addr": 4849,
                "original_corrected": 4393,
                "expanded_monthly": 2298,
                "expanded_daily": round(hhi_ts["entity_hhi"].mean()),
                "paper_location": "V.C",
                "revision_needed": True,
            },
            "tier_hhi_mean": {
                "original_12addr": 7361,
                "original_corrected": 5305,
                "expanded_monthly": 4801,
                "expanded_daily": round(hhi_ts["tier_hhi"].mean()),
                "paper_location": "V.C",
                "revision_needed": True,
            },
            "coverage_ratio": {
                "original_12addr": 8.1,
                "expanded_monthly": 28.7,
                "expanded_daily": coverage["coverage_pct"],
                "paper_location": "IV.A, V.C",
                "revision_needed": True,
            },
            "usdt_through_tier1": {
                "original_12addr": 39.5,
                "expanded_daily": usdt_t1["tier1_usdt_pct"],
                "paper_location": "Intro, V.C (DELETE old Gemini claim)",
                "revision_needed": True,
            },
            "tier1_r_fed_assets": {
                "original_12addr": -0.17,
                "expanded_daily": tier_corr.get("Tier1", {}).get("r", None),
                "paper_location": "V.C",
                "revision_needed": True,
            },
            "tier2_r_fed_assets": {
                "original_12addr": -0.46,
                "expanded_daily": tier_corr.get("Tier2", {}).get("r", None),
                "paper_location": "V.C",
                "revision_needed": True,
            },
            "tier3_r_fed_assets": {
                "original_12addr": 0.81,
                "expanded_daily": tier_corr.get("Tier3", {}).get("r", None),
                "paper_location": "V.C",
                "revision_needed": True,
            },
            "svb_circle_retention": {
                "original_12addr": 0.76,
                "expanded_daily": svb.get("retention_by_entity", {}).get("Circle", {}).get("retention", None),
                "paper_location": "V.C",
                "revision_needed": True,
            },
            "svb_coinbase_retention": {
                "original_12addr": "N/A (was $0)",
                "expanded_daily": svb.get("retention_by_entity", {}).get("Coinbase", {}).get("retention", None),
                "paper_location": "V.C (NEW)",
                "revision_needed": True,
            },
            "svb_gemini_retention": {
                "original_12addr": "1.24x (was Binance)",
                "expanded_daily": svb.get("retention_by_entity", {}).get("Gemini", {}).get("retention", "N/A (~$0)"),
                "paper_location": "V.C (DELETE — was Binance)",
                "revision_needed": True,
            },
        },
    }

    save_json(comparison, "metrics_comparison_v2.json")

    # Print comparison table
    print(f"\n  {'Metric':30s} {'Original':>10s} {'Corrected':>10s} {'Monthly':>10s} {'Daily':>10s}")
    for name, data in comparison["metrics"].items():
        orig = str(data.get("original_12addr", ""))
        corr = str(data.get("original_corrected", ""))
        monthly = str(data.get("expanded_monthly", ""))
        daily = str(data.get("expanded_daily", ""))
        print(f"  {name:30s} {orig:>10s} {corr:>10s} {monthly:>10s} {daily:>10s}")

    return comparison


def main():
    print("=" * 70)
    print("RECOMPUTE ALL METRICS FROM DAILY EXPANDED DATA")
    print("=" * 70)

    df = load_daily_data()

    entity_summary = entity_volume_summary(df)
    tier_shares = tier_share_timeseries(df)
    hhi_ts = hhi_timeseries(df)
    svb = svb_retention(df)
    tier_corr = tier_correlations(df)
    usdt_t1 = usdt_through_tier1(df)
    cov = coverage_ratio(df)
    within_t1 = within_tier1(df)

    comparison = build_comparison(entity_summary, tier_shares, hhi_ts, svb,
                                  tier_corr, usdt_t1, cov, within_t1)

    print("\n" + "=" * 70)
    print("METRICS RECOMPUTATION COMPLETE")
    print("=" * 70)
    print("  Output files:")
    print("    gateway_volume_summary_v2.csv")
    print("    exhibit_C1_gateway_shares_daily_v2.csv")
    print("    exhibit_C2_concentration_daily_v2.csv")
    print("    svb_retention_v2.json")
    print("    tier_correlations_v2.json")
    print("    metrics_comparison_v2.json")


if __name__ == "__main__":
    main()
