"""B.5: VECM IRF with bootstrap confidence bands."""
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
    print("B.5: IRF WITH BOOTSTRAP CONFIDENCE BANDS")
    print("=" * 60)

    log_df = load_weekly_log_data()
    periods = 26
    n_boot = 500
    var_names = ["Fed Assets", "ON RRP", "Stablecoin Supply"]
    col_names = list(log_df.columns)
    print(f"Sample: {len(log_df)} weeks")

    # Fit VECM at AIC-optimal lag (k_ar_diff=7 means VAR lag=8)
    vecm_fit = VECM(log_df, k_ar_diff=7, coint_rank=1).fit()

    # Point estimate IRFs
    irf_obj = vecm_fit.irf(periods=periods)
    irf_point = irf_obj.irfs  # shape: (periods+1, 3, 3)

    # Bootstrap IRFs using residual resampling
    print(f"Running {n_boot} bootstrap replications...")
    boot_irfs = []
    residuals = vecm_fit.resid  # shape: (T-p, 3)
    n_obs = len(log_df)
    successful = 0

    for b in range(n_boot):
        if (b + 1) % 100 == 0:
            print(f"  Bootstrap {b + 1}/{n_boot} (successful: {successful})")
        try:
            # Resample residual indices
            idx = np.random.choice(len(residuals), size=len(residuals), replace=True)
            boot_resid = residuals[idx]

            # Reconstruct: fitted + resampled residuals
            fitted = vecm_fit.fittedvalues
            boot_y = fitted + boot_resid

            # Re-estimate VECM on bootstrapped data
            boot_df = pd.DataFrame(boot_y, columns=col_names)
            boot_vecm = VECM(boot_df, k_ar_diff=7, coint_rank=1).fit()
            boot_irf = boot_vecm.irf(periods=periods).irfs
            boot_irfs.append(boot_irf)
            successful += 1
        except:
            continue

    print(f"Successful bootstraps: {successful}/{n_boot}")

    if successful < 50:
        print("WARNING: Too few successful bootstraps for reliable CIs")

    boot_array = np.array(boot_irfs)  # shape: (n_successful, periods+1, 3, 3)
    ci_lo = np.percentile(boot_array, 5, axis=0)
    ci_hi = np.percentile(boot_array, 95, axis=0)
    ci16 = np.percentile(boot_array, 16, axis=0)
    ci84 = np.percentile(boot_array, 84, axis=0)

    # Cache bootstrap results for fast replotting
    cache_path = DATA_PROC / "irf_bootstrap_cache.npz"
    np.savez(cache_path, irf_point=irf_point, ci_lo=ci_lo, ci_hi=ci_hi, ci16=ci16, ci84=ci84)
    print(f"  Cached bootstrap arrays to {cache_path}")

    # Plot 3x3 IRF grid with 90% bootstrap bands
    setup_plot_style()
    fig, axes = plt.subplots(3, 3, figsize=(11, 9))
    x = np.arange(periods + 1)

    for i in range(3):  # response variable
        for j in range(3):  # shock variable
            ax = axes[i, j]
            ax.plot(x, irf_point[:, i, j], color=color("primary"), linewidth=1.8, label="Point estimate")
            ax.fill_between(x, ci_lo[:, i, j], ci_hi[:, i, j],
                            alpha=0.15, color=color("secondary"), label="90% CI")
            ax.fill_between(x, ci16[:, i, j], ci84[:, i, j],
                            alpha=0.25, color=color("secondary"), label="68% CI")
            ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
            title = f"{var_names[i]} (own shock)" if i == j else f"{var_names[j]} → {var_names[i]}"
            ax.set_title(title, fontsize=9)
            if i == 2:
                ax.set_xlabel("Weeks", fontsize=8)
            if j == 0:
                ax.set_ylabel("Response", fontsize=8)

    # Legend on first panel only
    axes[0, 0].legend(fontsize=7, loc="upper right")

    fig.suptitle("VECM Impulse Response Functions\n(90% Bootstrap CI, 500 replications)",
                 fontsize=12, fontweight="bold", y=1.02)
    fig.tight_layout(rect=[0, 0.02, 1, 0.98])
    save_exhibit(fig, "exhibit11_irf_bootstrap.png",
                 "Source: Authors' calculations using FRED and DefiLlama data. "
                 f"Bootstrap: {successful} of {n_boot} replications successful.")

    # Check which IRFs have CIs that exclude zero at various horizons
    print("\nIRF significance (90% CI excludes zero):")
    key_horizons = [4, 8, 12, 26]
    sig_results = {}
    for i in range(3):
        for j in range(3):
            label = f"{var_names[j]} -> {var_names[i]}"
            sig_results[label] = {}
            for h in key_horizons:
                lo = ci_lo[h, i, j]
                hi = ci_hi[h, i, j]
                excludes_zero = (lo > 0) or (hi < 0)
                sig_results[label][f"week_{h}"] = {
                    "point": round(float(irf_point[h, i, j]), 6),
                    "ci90_lo": round(float(lo), 6),
                    "ci90_hi": round(float(hi), 6),
                    "significant": excludes_zero,
                }
                sig_mark = "✓" if excludes_zero else " "
                print(f"  {label} at week {h:2d}: [{lo:.5f}, {hi:.5f}] {sig_mark}")

    # Save bootstrap summary
    save_json({
        "n_boot_attempted": n_boot,
        "n_boot_successful": successful,
        "k_ar_diff": 7,
        "coint_rank": 1,
        "periods": periods,
        "significance": sig_results,
    }, "irf_bootstrap_results.json")

    # Also generate at lag=4 for robustness comparison
    print("\nGenerating lag=4 robustness IRF...")
    try:
        vecm4 = VECM(log_df, k_ar_diff=3, coint_rank=1).fit()
        irf4 = vecm4.irf(periods=periods).irfs

        fig2, axes2 = plt.subplots(3, 3, figsize=(11, 9))
        for i in range(3):
            for j in range(3):
                ax = axes2[i, j]
                # Compare lag=8 and lag=4
                ax.plot(x, irf_point[:, i, j], color=color("primary"), linewidth=1.5,
                        alpha=0.5, linestyle="--", label="Lag=8")
                ax.plot(x, irf4[:, i, j], color=color("stress"), linewidth=1.5, label="Lag=4")
                ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
                title = f"{var_names[i]} (own shock)" if i == j else f"{var_names[j]} → {var_names[i]}"
                ax.set_title(title, fontsize=9)
                if i == 2: ax.set_xlabel("Weeks", fontsize=8)
                if j == 0: ax.set_ylabel("Response", fontsize=8)
        axes2[0, 0].legend(fontsize=7, loc="upper right")
        fig2.suptitle("IRF Lag Robustness: Lag=8 (AIC) vs Lag=4",
                      fontsize=12, fontweight="bold", y=1.02)
        fig2.tight_layout(rect=[0, 0.02, 1, 0.98])
        save_exhibit(fig2, "exhibit11_irf_lag4_comparison.png",
                     "Source: FRED (WSHOMCB, RRPONTSYD) and DefiLlama (stablecoin supply). VECM with Johansen cointegration rank = 1.")
        print("Saved exhibit11_irf_lag4_comparison.png")
    except Exception as e:
        print(f"Lag=4 IRF failed: {e}")

    print("\n✓ Done")

if __name__ == "__main__":
    main()
