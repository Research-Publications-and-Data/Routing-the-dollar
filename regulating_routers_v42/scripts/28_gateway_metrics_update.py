"""Task 8-9: Tier correlations + gateway coverage ratio from original exhibit_A data.

Outputs:
  data/processed/tier_correlations.json   — tier share vs FRED correlations
  data/processed/gateway_coverage.json    — updated coverage ratio from exhibit_A
  data/processed/gateway_restoration_audit.json — entity name/address verification
"""
import pandas as pd, numpy as np, json, sys
from scipy import stats
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import GATEWAYS


def compute_tier_correlations():
    """Compute correlations between tier volume shares and FRED macro variables."""
    print("\n[1/3] Tier-Level Correlations")

    a = pd.read_csv(DATA_RAW / "exhibit_A_gateway_transfers.csv")
    a["date"] = pd.to_datetime(a["date"], utc=True)
    a["total_vol"] = a["inflow_usd"].abs() + a["outflow_usd"].abs()

    # Daily tier shares
    daily_tier = a.groupby(["date", "tier"])["total_vol"].sum().unstack(fill_value=0)
    total = daily_tier.sum(axis=1).replace(0, np.nan)
    tier_shares = daily_tier.div(total, axis=0).fillna(0)
    tier_shares.index = pd.to_datetime(tier_shares.index, utc=True).tz_localize(None)

    # Load FRED
    fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)

    # Merge on weekly basis
    weekly_shares = tier_shares.resample("W-WED").mean()
    weekly_fred = fred[["WSHOMCB", "DFF", "RRPONTSYD"]].resample("W-WED").last()
    merged = weekly_shares.join(weekly_fred, how="inner").dropna()

    results = {}
    tier_map = {"Tier1": "tier1", "Tier2": "tier2", "Tier3": "tier3"}

    for tier_col in tier_shares.columns:
        tier_key = tier_map.get(tier_col, tier_col)
        tier_results = {}
        for macro_col, macro_name in [("WSHOMCB", "fed_assets"), ("DFF", "fed_funds"), ("RRPONTSYD", "on_rrp")]:
            if macro_col in merged.columns and tier_col in merged.columns:
                valid = merged[[tier_col, macro_col]].dropna()
                if len(valid) > 10:
                    r, p = stats.pearsonr(valid[tier_col], valid[macro_col])
                    tier_results[macro_name] = {"r": round(r, 4), "p": round(p, 4), "n": len(valid)}
                    print(f"  {tier_key} vs {macro_name}: r={r:.4f}, p={p:.4f}")
        results[tier_key] = tier_results

    # Also compute paper-cited correlations (tier shares vs fed assets)
    if "Tier1" in merged.columns and "WSHOMCB" in merged.columns:
        print(f"\n  Paper validation:")
        for tier_col, expected in [("Tier1", -0.67), ("Tier2", -0.29), ("Tier3", 0.43)]:
            if tier_col in merged.columns:
                r, _ = stats.pearsonr(merged[tier_col], merged["WSHOMCB"])
                print(f"    {tier_col} vs Fed Assets: r={r:.4f} (paper cites {expected})")

    save_json(results, "tier_correlations.json")
    return results


def compute_coverage_ratio():
    """Compute bidirectional gateway volume and coverage ratio from exhibit_A."""
    print("\n[2/3] Gateway Coverage Ratio")

    a = pd.read_csv(DATA_RAW / "exhibit_A_gateway_transfers.csv")
    a["total_vol"] = a["inflow_usd"].abs() + a["outflow_usd"].abs()

    gateway_total = a["total_vol"].sum()
    print(f"  Total bidirectional gateway volume: ${gateway_total/1e12:.2f}T")

    # Per-gateway breakdown
    by_gw = a.groupby("gateway")["total_vol"].sum().sort_values(ascending=False)
    print(f"\n  Per-gateway volume:")
    for gw, vol in by_gw.items():
        print(f"    {gw}: ${vol/1e9:.1f}B ({vol/gateway_total*100:.1f}%)")

    # Per-tier breakdown
    by_tier = a.groupby("tier")["total_vol"].sum().sort_values(ascending=False)
    print(f"\n  Per-tier volume:")
    for tier, vol in by_tier.items():
        print(f"    {tier}: ${vol/1e12:.2f}T ({vol/gateway_total*100:.1f}%)")

    # Load existing coverage data for total Ethereum volume reference
    existing = {}
    try:
        with open(DATA_PROC / "gateway_coverage.json") as f:
            existing = json.load(f)
    except FileNotFoundError:
        pass

    total_eth = existing.get("total_volume_ethereum", 27_950_735_948_472.184)
    coverage = gateway_total / total_eth

    result = {
        "coverage_ratio": round(coverage, 4),
        "gateway_volume": float(gateway_total),
        "total_volume_ethereum": float(total_eth),
        "gateway_volume_T": round(gateway_total / 1e12, 2),
        "total_volume_ethereum_T": round(total_eth / 1e12, 2),
        "n_gateways": len(by_gw),
        "by_gateway": {gw: round(float(vol) / 1e9, 1) for gw, vol in by_gw.items()},
        "by_tier": {tier: round(float(vol) / 1e12, 2) for tier, vol in by_tier.items()},
    }

    # Preserve multi-chain data if present
    for key in ["total_volume_tron", "total_volume_solana",
                "ethereum_share_of_multichain", "tron_share_of_multichain", "solana_share_of_multichain"]:
        if key in existing:
            result[key] = existing[key]

    print(f"\n  Coverage: ${gateway_total/1e12:.2f}T / ${total_eth/1e12:.2f}T = {coverage:.1%}")

    save_json(result, "gateway_coverage.json")
    return result


def verify_entity_names():
    """Verify that entity names in settings.py match exhibit_A data."""
    print("\n[3/3] Entity Name Verification")

    a = pd.read_csv(DATA_RAW / "exhibit_A_gateway_transfers.csv")
    exhibit_gateways = sorted(a["gateway"].unique())
    settings_gateways = sorted(set(v["name"] for v in GATEWAYS.values()))

    audit = {
        "exhibit_A_gateways": exhibit_gateways,
        "settings_gateways": settings_gateways,
        "match": exhibit_gateways == settings_gateways,
        "in_exhibit_not_settings": [g for g in exhibit_gateways if g not in settings_gateways],
        "in_settings_not_exhibit": [g for g in settings_gateways if g not in exhibit_gateways],
        "n_gateways_exhibit": len(exhibit_gateways),
        "n_gateways_settings": len(settings_gateways),
        "address_registry": {addr: meta["name"] for addr, meta in GATEWAYS.items()},
    }

    if audit["match"]:
        print("  Entity names MATCH between exhibit_A and settings.py")
    else:
        print(f"  MISMATCH detected:")
        if audit["in_exhibit_not_settings"]:
            print(f"    In exhibit_A but not settings: {audit['in_exhibit_not_settings']}")
        if audit["in_settings_not_exhibit"]:
            print(f"    In settings but not exhibit_A: {audit['in_settings_not_exhibit']}")

    for gw in exhibit_gateways:
        tier_in_data = a[a["gateway"] == gw]["tier"].iloc[0]
        # Check settings
        settings_tier = None
        for v in GATEWAYS.values():
            if v["name"] == gw:
                settings_tier = f"Tier{v['tier']}"
                break
        match = "OK" if tier_in_data == settings_tier else f"MISMATCH ({tier_in_data} vs {settings_tier})"
        print(f"    {gw}: {tier_in_data} [{match}]")

    save_json(audit, "gateway_restoration_audit.json")
    return audit


def main():
    print("=" * 60)
    print("GATEWAY METRICS UPDATE (Tasks 8-9)")
    print("=" * 60)

    correlations = compute_tier_correlations()
    coverage = compute_coverage_ratio()
    audit = verify_entity_names()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Coverage ratio: {coverage['coverage_ratio']:.1%}")
    print(f"  Gateway volume: ${coverage['gateway_volume_T']}T")
    print(f"  Entity names match: {audit['match']}")
    print("Done.")


if __name__ == "__main__":
    main()
