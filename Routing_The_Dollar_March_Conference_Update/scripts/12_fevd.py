"""12_fevd.py — Forecast Error Variance Decomposition from existing VECM.

Even though individual cross-variable IRFs aren't significant at 90% CI,
FEVD can show that Fed shocks explain a meaningful share of supply forecast
error variance in aggregate. This is the "magnitude" evidence vector.

Output: data/processed/fevd_results.json, data/exhibits/exhibit_fevd.png
"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt, json, sys, warnings
warnings.filterwarnings("ignore")
from statsmodels.tsa.vector_ar.vecm import VECM
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, EXHIBITS, save_json, save_exhibit, setup_plot_style, color

def load_weekly_log_data():
    fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
    try:
        sc = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv", index_col=0, parse_dates=True)
        supply = sc["total_supply"]
    except FileNotFoundError:
        import requests
        resp = requests.get("https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=1", timeout=30)
        usdt = {pd.to_datetime(d["date"], unit="s"): d.get("totalCirculating", {}).get("peggedUSD", 0) for d in resp.json()}
        resp2 = requests.get("https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2", timeout=30)
        usdc = {pd.to_datetime(d["date"], unit="s"): d.get("totalCirculating", {}).get("peggedUSD", 0) for d in resp2.json()}
        supply = pd.Series(usdt).add(pd.Series(usdc), fill_value=0).sort_index()
        supply.name = "total_supply"
    merged = fred[["WSHOMCB", "RRPONTSYD"]].join(pd.DataFrame(supply), how="inner").dropna(subset=["WSHOMCB"])
    merged["RRPONTSYD"] = merged["RRPONTSYD"].ffill()
    weekly = merged.resample("W-WED").last().dropna()
    primary = weekly["2023-02-01":"2026-01-31"]
    return np.log(primary.replace(0, np.nan).dropna())

def main():
    print("=" * 60)
    print("FORECAST ERROR VARIANCE DECOMPOSITION (FEVD)")
    print("=" * 60)

    log_df = load_weekly_log_data()
    var_names = ["Fed Assets", "ON RRP", "Stablecoin Supply"]
    col_names = list(log_df.columns)
    periods = 26
    print(f"Sample: {len(log_df)} weeks")

    # Fit VECM at AIC-optimal lag
    vecm_fit = VECM(log_df, k_ar_diff=7, coint_rank=1).fit()
    irf_obj = vecm_fit.irf(periods)

    # Compute FEVD from orthogonalized (Cholesky) IRFs
    # FEVD[h,i,j] = sum_{s=0}^{h} orth[s,i,j]^2 / sum_{s=0}^{h} sum_k orth[s,i,k]^2
    orth = irf_obj.orth_irfs  # shape: (periods+1, n_vars, n_vars)
    T, n, _ = orth.shape
    fevd = np.zeros((T, n, n))
    for h in range(T):
        for i in range(n):
            total_var = sum(np.dot(orth[s, i, :], orth[s, i, :]) for s in range(h + 1))
            for j in range(n):
                var_j = sum(orth[s, i, j] ** 2 for s in range(h + 1))
                fevd[h, i, j] = var_j / total_var if total_var > 0 else 0

    print(f"\nFEVD computed from orthogonalized IRFs (Cholesky ordering: {var_names})")

    # Key horizons
    key_horizons = [1, 4, 8, 12, 26]
    results = {"horizons": {}, "var_names": var_names}

    print(f"\n{'Horizon':>8}  {'Fed→Supply':>12}  {'RRP→Supply':>12}  {'Own→Supply':>12}")
    print("-" * 50)
    for h in key_horizons:
        # Row = stablecoin supply (idx 2), columns = shock sources
        fed_share = float(fevd[h, 2, 0]) * 100
        rrp_share = float(fevd[h, 2, 1]) * 100
        own_share = float(fevd[h, 2, 2]) * 100
        print(f"{h:>8}  {fed_share:>11.1f}%  {rrp_share:>11.1f}%  {own_share:>11.1f}%")

        results["horizons"][str(h)] = {
            "supply_variance_from_fed": round(fed_share, 2),
            "supply_variance_from_rrp": round(rrp_share, 2),
            "supply_variance_from_own": round(own_share, 2),
        }

    # Also get FEVD for Fed assets and ON RRP
    print(f"\n{'Horizon':>8}  {'Supply→Fed':>12}  {'RRP→Fed':>12}  {'Own→Fed':>12}")
    print("-" * 50)
    for h in key_horizons:
        supply_to_fed = float(fevd[h, 0, 2]) * 100
        rrp_to_fed = float(fevd[h, 0, 1]) * 100
        own_fed = float(fevd[h, 0, 0]) * 100
        print(f"{h:>8}  {supply_to_fed:>11.1f}%  {rrp_to_fed:>11.1f}%  {own_fed:>11.1f}%")
        results["horizons"][str(h)]["fed_variance_from_supply"] = round(supply_to_fed, 2)
        results["horizons"][str(h)]["fed_variance_from_rrp"] = round(rrp_to_fed, 2)
        results["horizons"][str(h)]["fed_variance_from_own"] = round(own_fed, 2)

    # Summary statistics
    fed_to_supply_26 = float(fevd[26, 2, 0]) * 100
    rrp_to_supply_26 = float(fevd[26, 2, 1]) * 100
    policy_total_26 = fed_to_supply_26 + rrp_to_supply_26

    results["summary"] = {
        "fed_share_of_supply_at_26w": round(fed_to_supply_26, 2),
        "rrp_share_of_supply_at_26w": round(rrp_to_supply_26, 2),
        "policy_total_at_26w": round(policy_total_26, 2),
    }

    # Verdict
    if policy_total_26 > 20:
        verdict = "strong"
        results["verdict"] = f"STRONG: Fed + ON RRP explain {policy_total_26:.1f}% of supply forecast error variance at 26 weeks"
        results["paper_sentence"] = (
            f"Forecast error variance decomposition indicates that Federal Reserve balance sheet "
            f"and ON RRP facility shocks jointly explain {policy_total_26:.1f} percent of stablecoin "
            f"supply forecast error variance at the 26-week horizon, confirming that monetary policy "
            f"variables are economically meaningful predictors of supply dynamics even when individual "
            f"impulse response functions do not achieve statistical significance."
        )
    elif policy_total_26 > 10:
        verdict = "moderate"
        results["verdict"] = f"MODERATE: Fed + ON RRP explain {policy_total_26:.1f}% at 26 weeks"
        results["paper_sentence"] = (
            f"Forecast error variance decomposition shows Fed and ON RRP shocks jointly account "
            f"for {policy_total_26:.1f} percent of supply variance at 26 weeks — a non-trivial but "
            f"modest contribution, consistent with the cointegrating relationship operating through "
            f"slow equilibrium adjustment rather than sharp impulse responses."
        )
    else:
        verdict = "weak"
        results["verdict"] = f"WEAK: Fed + ON RRP explain only {policy_total_26:.1f}% at 26 weeks"
        results["paper_sentence"] = (
            f"The FEVD indicates that monetary policy shocks explain only {policy_total_26:.1f} percent "
            f"of supply variance at 26 weeks, with stablecoin supply primarily driven by its own "
            f"dynamics. The cointegrating relationship documented in Section IV operates through "
            f"very slow equilibrium correction rather than direct transmission."
        )

    print(f"\nVERDICT: {results['verdict']}")
    print(f"\nPaper sentence: {results['paper_sentence']}")
    save_json(results, "fevd_results.json")

    # Stacked area chart: supply variance decomposition over horizons
    setup_plot_style()
    fig, ax = plt.subplots(figsize=(8, 5))
    horizons = np.arange(periods + 1)
    fed_shares = [float(fevd[h, 2, 0]) * 100 for h in horizons]
    rrp_shares = [float(fevd[h, 2, 1]) * 100 for h in horizons]
    own_shares = [float(fevd[h, 2, 2]) * 100 for h in horizons]

    ax.stackplot(horizons, own_shares, rrp_shares, fed_shares,
                 labels=["Own (Supply)", "ON RRP", "Fed Assets"],
                 colors=[color("tertiary"), color("secondary"), color("primary")],
                 alpha=0.8)
    ax.set_xlabel("Forecast Horizon (Weeks)")
    ax.set_ylabel("Share of Forecast Error Variance (%)")
    ax.set_title("Stablecoin Supply: Forecast Error Variance Decomposition")
    ax.set_xlim(0, periods)
    ax.set_ylim(0, 100)
    ax.legend(loc="center right")
    fig.subplots_adjust(bottom=0.15)
    save_exhibit(fig, "exhibit_fevd.png",
                 "Source: Authors' VECM estimation using FRED and DefiLlama data.")

    print("\n✓ Done")

if __name__ == "__main__":
    main()
