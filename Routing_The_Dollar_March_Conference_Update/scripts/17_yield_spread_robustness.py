"""Sprint 5b: Compound V3 yield-spread Granger causality confirmation.

Tests whether the T-bill-minus-DeFi yield spread Granger-causes weekly
stablecoin supply growth using the pre-built exhibit4_yield_spread_weekly.csv
(156-week matched sample, Feb 2023 – Jan 2026).

Paper claim: F = 17.70, p < 0.0001 at lag 1.

Outputs:
  data/processed/yield_spread_robustness.csv — Granger F-stats at lags 1–4

Data:
  data/processed/exhibit4_yield_spread_weekly.csv — spread + supply_growth
"""
import pandas as pd
import numpy as np
import warnings
import sys
from pathlib import Path

warnings.filterwarnings("ignore")

from statsmodels.tsa.stattools import grangercausalitytests

ROOT = Path(__file__).resolve().parent.parent
DATA_PROC = ROOT / "data" / "processed"


def main():
    print("=" * 60)
    print("YIELD-SPREAD GRANGER CAUSALITY ROBUSTNESS")
    print("=" * 60)

    # Load pre-built yield spread data
    path = DATA_PROC / "exhibit4_yield_spread_weekly.csv"
    if not path.exists():
        print(f"  ERROR: {path} not found")
        print("  Run build_exhibit4_data.py first.")
        sys.exit(1)

    df = pd.read_csv(path, index_col=0, parse_dates=True)
    print(f"  Loaded: {len(df)} weeks, columns: {list(df.columns)}")

    # The CSV has 'spread' and 'supply_growth'
    if "spread" not in df.columns or "supply_growth" not in df.columns:
        print(f"  ERROR: Expected columns 'spread' and 'supply_growth'")
        print(f"  Got: {list(df.columns)}")
        sys.exit(1)

    df = df.dropna()
    n = len(df)
    print(f"  Clean sample: {n} weeks")

    # Granger causality: spread → supply_growth
    print("\n  Granger causality: yield spread → supply growth")
    max_lag = 4
    data = df[["supply_growth", "spread"]].values  # Y first, X second

    results_rows = []
    try:
        gc = grangercausalitytests(data, maxlag=max_lag, verbose=False)
        for lag in range(1, max_lag + 1):
            f_stat = gc[lag][0]["ssr_ftest"][0]
            p_val = gc[lag][0]["ssr_ftest"][1]
            sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""
            results_rows.append({
                "lag": lag,
                "F_stat": round(float(f_stat), 2),
                "p_value": round(float(p_val), 6),
                "significant_5pct": p_val < 0.05,
            })
            print(f"    Lag {lag}: F = {f_stat:.2f}, p = {p_val:.6f} {sig}")
    except Exception as e:
        print(f"  ERROR in Granger test: {e}")
        sys.exit(1)

    # Reverse direction: supply_growth → spread
    print("\n  Reverse Granger: supply growth → yield spread")
    data_rev = df[["spread", "supply_growth"]].values
    try:
        gc_rev = grangercausalitytests(data_rev, maxlag=max_lag, verbose=False)
        for lag in range(1, max_lag + 1):
            f_stat = gc_rev[lag][0]["ssr_ftest"][0]
            p_val = gc_rev[lag][0]["ssr_ftest"][1]
            sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""
            results_rows.append({
                "lag": lag,
                "F_stat": round(float(f_stat), 2),
                "p_value": round(float(p_val), 6),
                "significant_5pct": p_val < 0.05,
                "direction": "reverse",
            })
            print(f"    Lag {lag}: F = {f_stat:.2f}, p = {p_val:.6f} {sig}")
    except Exception as e:
        print(f"  Reverse test error: {e}")

    # Add direction label to forward rows
    for row in results_rows:
        if "direction" not in row:
            row["direction"] = "spread_to_growth"

    # Save
    out = pd.DataFrame(results_rows)
    out.to_csv(DATA_PROC / "yield_spread_robustness.csv", index=False)
    print(f"\n  Saved: {DATA_PROC / 'yield_spread_robustness.csv'}")

    # Verification
    lag1 = [r for r in results_rows
            if r["lag"] == 1 and r["direction"] == "spread_to_growth"]
    if lag1:
        f1 = lag1[0]["F_stat"]
        p1 = lag1[0]["p_value"]
        print(f"\n  Paper claim: F = 17.70 at lag 1")
        print(f"  Computed:    F = {f1:.2f} at lag 1, p = {p1:.6f}")
        if abs(f1 - 17.70) < 3.0 and p1 < 0.001:
            print("  STATUS: CONSISTENT with paper claim")
        else:
            print("  STATUS: CHECK — may differ due to sample alignment")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
