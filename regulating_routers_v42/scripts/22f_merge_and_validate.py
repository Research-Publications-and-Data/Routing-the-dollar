"""22f: Final merge of all new data and cross-validation.

Merges:
- Discovered Tron entity data (from 22d)
- Synthetic Tier 3 DeFi data (from 22e)
- Artemis category data for cross-validation (from 22b)

Updates gateway CSVs and re-runs unification logic.
"""
import pandas as pd, numpy as np, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import PRIMARY_START, PRIMARY_END
from gateway_registry import get_gateways_by_chain, ALL_GATEWAYS
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json, save_csv


def merge_tier3_into_gateway(chain, gateway_csv, tier3_csv):
    """Merge synthetic Tier 3 data into existing gateway CSV."""
    print(f"\n--- Merging Tier 3 into {chain} gateway ---")

    frames = []

    # Load existing gateway data
    gw_path = DATA_RAW / gateway_csv
    if gw_path.exists():
        existing = pd.read_csv(gw_path)
        for col in ["volume_usd", "volume_raw", "n_transfers"]:
            if col in existing.columns:
                existing[col] = pd.to_numeric(existing[col], errors="coerce")
        frames.append(existing)
        print(f"  Existing: {len(existing)} rows, "
              f"{existing['entity'].nunique() if 'entity' in existing.columns else '?'} entities")

    # Load synthetic Tier 3 data
    t3_path = DATA_RAW / tier3_csv
    if t3_path.exists():
        t3 = pd.read_csv(t3_path)
        for col in ["volume_usd", "volume_raw", "n_transfers"]:
            if col in t3.columns:
                t3[col] = pd.to_numeric(t3[col], errors="coerce")
        frames.append(t3)
        print(f"  Tier 3 synthetic: {len(t3)} rows, "
              f"{t3['entity'].nunique() if 'entity' in t3.columns else '?'} entities")
    else:
        print(f"  Tier 3 file not found: {t3_path}")

    if not frames:
        print(f"  No data to merge for {chain}")
        return None

    merged = pd.concat(frames, ignore_index=True)

    # Deduplicate by entity + month + token (keep highest volume)
    dedup_cols = ["entity", "month"]
    if "token" in merged.columns:
        dedup_cols.append("token")

    if all(c in merged.columns for c in dedup_cols):
        before = len(merged)
        merged = merged.sort_values("volume_usd", ascending=False)
        merged = merged.drop_duplicates(subset=dedup_cols, keep="first")
        if before != len(merged):
            print(f"  Deduped: {before} → {len(merged)} rows")

    merged.to_csv(gw_path, index=False)
    entities = merged['entity'].nunique() if 'entity' in merged.columns else 0
    total_vol = merged['volume_usd'].sum() if 'volume_usd' in merged.columns else 0
    print(f"  Updated: {len(merged)} rows, {entities} entities, "
          f"${total_vol/1e9:.1f}B total")
    return merged


def cross_validate_with_artemis(chain, gateway_csv, artemis_csv):
    """Cross-validate Dune gateway volumes against Artemis category data."""
    print(f"\n--- Cross-validation: {chain} ---")

    validation = {"chain": chain}

    try:
        gw = pd.read_csv(DATA_RAW / gateway_csv)
        gw["volume_usd"] = pd.to_numeric(gw.get("volume_usd", 0), errors="coerce")
        gw_total = gw["volume_usd"].sum()
        validation["gateway_total"] = float(gw_total)
    except FileNotFoundError:
        print(f"  Gateway CSV not found: {gateway_csv}")
        return validation

    try:
        art = pd.read_csv(DATA_RAW / artemis_csv, index_col=0, parse_dates=True)
    except FileNotFoundError:
        print(f"  Artemis CSV not found: {artemis_csv}")
        return validation

    # Compare gateway total against Artemis total
    total_col = chain.replace("solana", "sol")
    if total_col in art.columns:
        art_total = art[total_col].sum()
        validation["artemis_total"] = float(art_total)
        if art_total > 0:
            ratio = gw_total / art_total
            validation["gateway_to_artemis_ratio"] = round(ratio, 4)
            print(f"  Gateway: ${gw_total/1e9:.1f}B")
            print(f"  Artemis total: ${art_total/1e9:.1f}B")
            print(f"  Ratio: {ratio:.2%}")
            if ratio > 2.0:
                print(f"  WARNING: Gateway volume >2x Artemis total — possible normalization issue")
            elif ratio > 1.0:
                print(f"  NOTE: Gateway > Artemis (likely double-counting in/out)")

    # Compare CEX subset
    cex_col = f"cex_{total_col}"
    if cex_col in art.columns:
        art_cex = art[cex_col].sum()
        # Get Tier 2 gateway volumes (exchanges)
        gw_tier2 = gw[gw.get("tier", 0) == 2]["volume_usd"].sum() if "tier" in gw.columns else 0
        validation["artemis_cex"] = float(art_cex)
        validation["gateway_tier2"] = float(gw_tier2)
        if art_cex > 0:
            ratio = gw_tier2 / art_cex
            validation["tier2_to_cex_ratio"] = round(ratio, 4)
            print(f"  Gateway Tier 2: ${gw_tier2/1e9:.1f}B vs Artemis CEX: ${art_cex/1e9:.1f}B")
            print(f"  CEX ratio: {ratio:.2%}")

    # Compare DeFi subset
    defi_col = f"defi_{total_col}"
    if defi_col in art.columns:
        art_defi = art[defi_col].sum()
        gw_tier3 = gw[gw.get("tier", 0) == 3]["volume_usd"].sum() if "tier" in gw.columns else 0
        validation["artemis_defi"] = float(art_defi)
        validation["gateway_tier3"] = float(gw_tier3)
        if art_defi > 0:
            ratio = gw_tier3 / art_defi
            validation["tier3_to_defi_ratio"] = round(ratio, 4)
            print(f"  Gateway Tier 3: ${gw_tier3/1e9:.1f}B vs Artemis DeFi: ${art_defi/1e9:.1f}B")
            print(f"  DeFi ratio: {ratio:.2%}")

    return validation


def summarize_improvements():
    """Summarize data improvements from expansion effort."""
    print("\n" + "=" * 60)
    print("DATA IMPROVEMENT SUMMARY")
    print("=" * 60)

    improvements = {}

    for chain, csv_name in [("solana", "dune_solana_gateway.csv"),
                             ("tron", "dune_tron_gateway.csv")]:
        try:
            df = pd.read_csv(DATA_RAW / csv_name)
            df["volume_usd"] = pd.to_numeric(df.get("volume_usd", 0), errors="coerce")
            entities = df["entity"].nunique() if "entity" in df.columns else 0
            total_vol = df["volume_usd"].sum()
            has_synthetic = "data_source" in df.columns and (df["data_source"] == "artemis_attributed").any()

            improvements[chain] = {
                "total_rows": len(df),
                "entities": entities,
                "total_volume": float(total_vol),
                "has_synthetic_data": bool(has_synthetic),
                "entity_list": sorted(df["entity"].unique().tolist()) if "entity" in df.columns else [],
            }
            print(f"\n  {chain}:")
            print(f"    Rows: {len(df)}")
            print(f"    Entities: {entities}")
            print(f"    Volume: ${total_vol/1e9:.1f}B")
            print(f"    Synthetic: {'Yes' if has_synthetic else 'No'}")
            if "entity" in df.columns:
                for ent in sorted(df["entity"].unique()):
                    ent_vol = df[df["entity"] == ent]["volume_usd"].sum()
                    print(f"      {ent}: ${ent_vol/1e9:.1f}B")
        except FileNotFoundError:
            print(f"\n  {chain}: NOT FOUND")

    return improvements


def main():
    print("=" * 60)
    print("FINAL MERGE & CROSS-VALIDATION")
    print("=" * 60)

    results = {"merges": {}, "validations": {}}

    # 1. Merge Tier 3 synthetic data into Solana gateway
    sol_merged = merge_tier3_into_gateway(
        "solana", "dune_solana_gateway.csv", "dune_solana_tier3_synthetic.csv")
    if sol_merged is not None:
        results["merges"]["solana"] = {
            "rows": len(sol_merged),
            "entities": int(sol_merged["entity"].nunique()) if "entity" in sol_merged.columns else 0,
        }

    # 2. Merge Tier 3 synthetic data into Tron gateway
    tron_merged = merge_tier3_into_gateway(
        "tron", "dune_tron_gateway.csv", "dune_tron_tier3_synthetic.csv")
    if tron_merged is not None:
        results["merges"]["tron"] = {
            "rows": len(tron_merged),
            "entities": int(tron_merged["entity"].nunique()) if "entity" in tron_merged.columns else 0,
        }

    # 3. Cross-validation with Artemis
    sol_validation = cross_validate_with_artemis(
        "solana", "dune_solana_gateway.csv", "artemis_sol_categories.csv")
    results["validations"]["solana"] = sol_validation

    tron_validation = cross_validate_with_artemis(
        "tron", "dune_tron_gateway.csv", "artemis_tron_categories.csv")
    results["validations"]["tron"] = tron_validation

    # 4. Summary of improvements
    improvements = summarize_improvements()
    results["improvements"] = improvements

    # 5. Save results
    save_json(results, "merge_validation_results.json")

    print("\n" + "=" * 60)
    print("NEXT STEP: Run python scripts/21_crosschain_unification.py")
    print("to regenerate all concentration and coverage metrics.")
    print("=" * 60)


if __name__ == "__main__":
    main()
