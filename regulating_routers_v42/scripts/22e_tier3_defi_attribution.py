"""22e: Create synthetic Tier 3 DeFi gateway volumes from Artemis aggregates.

For Solana DEX protocols (Jupiter, Raydium, Orca) and Tron DeFi (SunSwap,
JustLend), direct address queries are structurally impossible because program
IDs don't appear in from_owner/to_owner. Instead, we use Artemis category
data (defi-sol) and attribute to individual protocols using published market
share ratios from DeFiLlama.
"""
import pandas as pd, numpy as np, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import PRIMARY_START, PRIMARY_END
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json, save_csv

# DeFi protocol market shares (from DeFiLlama DEX volume rankings, 2024)
# These are stablecoin-specific estimates, not total DEX volume
SOLANA_DEFI_SHARES = {
    "Jupiter": 0.60,   # ~60% of Solana DEX stablecoin routing
    "Raydium": 0.25,   # ~25% (main AMM)
    "Orca": 0.15,      # ~15% (Whirlpools concentrated liquidity)
}

# Tron DeFi shares (SunSwap dominates, JustLend for lending)
TRON_DEFI_SHARES = {
    "SunSwap": 0.75,   # ~75% of Tron DEX volume
    "JustLend": 0.25,  # ~25% lending/staking USDT
}

# Tier and CLII from gateway registry
ENTITY_META = {
    "Jupiter": {"tier": 3, "clii": 0.12},
    "Raydium": {"tier": 3, "clii": 0.10},
    "Orca": {"tier": 3, "clii": 0.10},
    "SunSwap": {"tier": 3, "clii": 0.10},
    "JustLend": {"tier": 3, "clii": 0.10},
}


def build_synthetic_rows(defi_series, shares, chain, token_default="USDC"):
    """Build synthetic monthly gateway rows from aggregate DeFi data."""
    rows = []
    for date, total_vol in defi_series.items():
        if pd.isna(total_vol) or total_vol <= 0:
            continue
        for entity, share in shares.items():
            meta = ENTITY_META.get(entity, {"tier": 3, "clii": 0.10})
            entity_vol = total_vol * share
            rows.append({
                "month": date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date),
                "entity": entity,
                "token": token_default,
                "n_transfers": 0,  # Not available from aggregate data
                "tier": meta["tier"],
                "volume_usd": round(entity_vol, 2),
                "volume_raw": round(entity_vol * 1e6, 0),  # Reverse to match schema
                "data_source": "artemis_attributed",
            })
    return pd.DataFrame(rows)


def main():
    print("=" * 60)
    print("TIER 3 DeFi ATTRIBUTION (Artemis → Entity)")
    print("=" * 60)

    methodology = {
        "description": "Synthetic entity-level DeFi gateway volumes derived from "
                      "Artemis category aggregates (defi-sol) and published DeFiLlama "
                      "market share ratios. NOT direct on-chain address measurements.",
        "solana_shares": SOLANA_DEFI_SHARES,
        "tron_shares": TRON_DEFI_SHARES,
        "sources": [
            "Artemis Analytics: ARTEMIS_STABLECOIN_TRANSFER_VOLUME (defi-sol)",
            "DeFiLlama DEX volume rankings (2024 avg market shares)",
            "Jupiter: ~60% of Solana DEX stablecoin routing",
            "Raydium: ~25% (dominant AMM pool)",
            "Orca: ~15% (Whirlpools concentrated liquidity)",
        ],
        "caveats": [
            "Market shares are approximations based on 2024 averages",
            "Actual share varies month-to-month",
            "n_transfers is not available from aggregate data (set to 0)",
            "These volumes should be clearly disclosed as estimates in the paper",
        ],
    }

    # Solana DeFi
    print("\n--- Solana DeFi Attribution ---")
    try:
        sol_df = pd.read_csv(DATA_RAW / "artemis_sol_categories.csv",
                             index_col=0, parse_dates=True)
        if "defi_sol" in sol_df.columns:
            defi_series = sol_df["defi_sol"].dropna()
            print(f"  Artemis defi-sol: {len(defi_series)} months, "
                  f"total=${defi_series.sum()/1e9:.1f}B")

            synthetic_sol = build_synthetic_rows(defi_series, SOLANA_DEFI_SHARES,
                                                  "solana", token_default="USDC")
            path = DATA_RAW / "dune_solana_tier3_synthetic.csv"
            synthetic_sol.to_csv(path, index=False)
            print(f"  Generated: {len(synthetic_sol)} rows")
            for entity in SOLANA_DEFI_SHARES:
                ent_vol = synthetic_sol[synthetic_sol["entity"] == entity]["volume_usd"].sum()
                print(f"    {entity}: ${ent_vol/1e9:.1f}B "
                      f"({SOLANA_DEFI_SHARES[entity]*100:.0f}% share)")
            methodology["solana_total_defi"] = float(defi_series.sum())
            methodology["solana_rows"] = len(synthetic_sol)
        else:
            print("  WARNING: defi_sol column not found in Artemis data")
    except FileNotFoundError:
        print("  WARNING: artemis_sol_categories.csv not found. Run 22b first.")

    # Tron DeFi — no direct defi-tron from Artemis, estimate from total - p2p
    print("\n--- Tron DeFi Attribution ---")
    try:
        tron_df = pd.read_csv(DATA_RAW / "artemis_tron_categories.csv",
                              index_col=0, parse_dates=True)
        # Try direct defi column first
        if "defi_tron" in tron_df.columns:
            defi_series = tron_df["defi_tron"].dropna()
        elif "tron" in tron_df.columns and "p2p_tron" in tron_df.columns:
            # Estimate: DeFi ≈ Total - P2P (rough, includes CEX too)
            # This overestimates DeFi, so use a conservative 5% of total
            total = tron_df["tron"]
            defi_series = total * 0.05  # Conservative: ~5% of Tron volume is DeFi
            print("  NOTE: Using 5% of total as DeFi estimate (no direct category data)")
        else:
            defi_series = pd.Series(dtype=float)

        if len(defi_series) > 0:
            print(f"  Tron DeFi estimate: {len(defi_series)} months, "
                  f"total=${defi_series.sum()/1e9:.1f}B")

            synthetic_tron = build_synthetic_rows(defi_series, TRON_DEFI_SHARES,
                                                   "tron", token_default="USDT")
            path = DATA_RAW / "dune_tron_tier3_synthetic.csv"
            synthetic_tron.to_csv(path, index=False)
            print(f"  Generated: {len(synthetic_tron)} rows")
            for entity in TRON_DEFI_SHARES:
                ent_vol = synthetic_tron[synthetic_tron["entity"] == entity]["volume_usd"].sum()
                print(f"    {entity}: ${ent_vol/1e9:.1f}B "
                      f"({TRON_DEFI_SHARES[entity]*100:.0f}% share)")
            methodology["tron_total_defi_estimate"] = float(defi_series.sum())
            methodology["tron_rows"] = len(synthetic_tron)
        else:
            print("  No Tron DeFi data available")
    except FileNotFoundError:
        print("  WARNING: artemis_tron_categories.csv not found. Run 22b first.")

    # Save methodology
    save_json(methodology, "tier3_attribution_methodology.json")

    print("\n" + "=" * 60)
    print("TIER 3 ATTRIBUTION COMPLETE")
    print("NOTE: These are estimates. Flag as 'artemis_attributed' in paper.")
    print("=" * 60)


if __name__ == "__main__":
    main()
