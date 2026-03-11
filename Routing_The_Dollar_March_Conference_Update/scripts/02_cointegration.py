"""Task 2: Johansen cointegration test, VECM, impulse responses."""
import pandas as pd, numpy as np, matplotlib.pyplot as plt, json, sys, warnings
warnings.filterwarnings("ignore")
from statsmodels.tsa.vector_ar.vecm import coint_johansen, VECM
from statsmodels.tsa.vector_ar.var_model import VAR
from statsmodels.tsa.stattools import adfuller, coint as eg_coint

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, EXHIBITS, save_json, save_exhibit, setup_plot_style, color

def load_data():
    fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
    # Quick stablecoin supply pull if not yet available
    try:
        sc = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv", index_col=0, parse_dates=True)
        supply = sc["total_supply"]
    except FileNotFoundError:
        print("  Pulling stablecoin supply from DefiLlama...")
        import requests
        resp = requests.get("https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=1", timeout=30)
        usdt = [(pd.to_datetime(d["date"], unit="s"), d.get("totalCirculating", {}).get("peggedUSD", 0)) for d in resp.json()]
        resp2 = requests.get("https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2", timeout=30)
        usdc = [(pd.to_datetime(d["date"], unit="s"), d.get("totalCirculating", {}).get("peggedUSD", 0)) for d in resp2.json()]
        usdt_s = pd.Series(dict(usdt), name="usdt")
        usdc_s = pd.Series(dict(usdc), name="usdc")
        supply = (usdt_s + usdc_s.reindex(usdt_s.index, fill_value=0))
        supply.name = "total_supply"
    merged = fred[["WSHOMCB", "RRPONTSYD"]].join(pd.DataFrame(supply), how="inner").dropna(subset=["WSHOMCB"])
    merged["RRPONTSYD"] = merged["RRPONTSYD"].ffill()
    weekly = merged.resample("W-WED").last().dropna()
    primary = weekly["2023-02-01":"2026-01-31"]
    print(f"  Primary sample: {len(primary)} weeks, {primary.index[0].date()} to {primary.index[-1].date()}")
    return primary

def main():
    print("=" * 60)
    print("COINTEGRATION AND VECM ANALYSIS")
    print("=" * 60)
    df = load_data()
    log_df = np.log(df.replace(0, np.nan).dropna())
    var_names = list(log_df.columns)

    # ADF tests
    print("\nADF Tests (levels and first differences):")
    adf = {}
    for col in log_df.columns:
        s = log_df[col].dropna()
        lev = adfuller(s, autolag="AIC")
        dif = adfuller(s.diff().dropna(), autolag="AIC")
        adf[col] = {"level_p": round(lev[1], 4), "diff_p": round(dif[1], 4)}
        print(f"  {col}: level p={lev[1]:.4f}, diff p={dif[1]:.4f}")

    # Johansen
    print("\nJohansen Cointegration Test:")
    var_model = VAR(log_df)
    lag = var_model.select_order(maxlags=8).aic
    print(f"  VAR lag (AIC): {lag}")
    k = max(1, lag - 1)
    joh = coint_johansen(log_df, det_order=0, k_ar_diff=k)
    n_vars = log_df.shape[1]
    johansen_results = {"var_lag_aic": lag, "k_ar_diff": k, "trace": [], "max_eigenvalue": []}
    coint_rank = 0
    for i in range(n_vars):
        reject = bool(joh.lr1[i] > joh.cvt[i, 1])
        johansen_results["trace"].append({
            "rank": i, "stat": round(float(joh.lr1[i]), 2),
            "cv95": round(float(joh.cvt[i, 1]), 2), "reject": reject})
        johansen_results["max_eigenvalue"].append({
            "rank": i, "stat": round(float(joh.lr2[i]), 2),
            "cv95": round(float(joh.cvm[i, 1]), 2), "reject": bool(joh.lr2[i] > joh.cvm[i, 1])})
        if reject: coint_rank += 1
        status = "REJECT" if reject else "fail"
        print(f"  H0: rank <= {i}: stat={joh.lr1[i]:.2f}, cv95={joh.cvt[i,1]:.2f} -> {status}")
    johansen_results["rank"] = coint_rank
    johansen_results["cointegrated"] = coint_rank > 0

    # VECM or VAR
    vecm_results = {}
    if coint_rank > 0:
        print(f"\nVECM (rank={coint_rank}):")
        vecm = VECM(log_df, k_ar_diff=k, coint_rank=coint_rank).fit()
        vecm_results = {"beta": vecm.beta.tolist(), "alpha": vecm.alpha.tolist()}
        print(f"  Cointegrating vector: {vecm.beta.T}")
        print(f"  Adjustment coefficients: {vecm.alpha}")

        # Extract alpha standard errors, t-stats, p-values from summary
        summary_text = str(vecm.summary())
        vecm_results["summary_text"] = summary_text
        try:
            alpha_se = vecm.stderr_alpha.tolist()
            alpha_t = vecm.tvalues_alpha.tolist()
            alpha_p = vecm.pvalues_alpha.tolist()
            vecm_results["alpha_stderr"] = alpha_se
            vecm_results["alpha_tvalues"] = alpha_t
            vecm_results["alpha_pvalues"] = alpha_p
            print(f"\n  Alpha standard errors, t-stats, p-values:")
            for i, name in enumerate(var_names):
                a = vecm.alpha[i, 0]
                se = alpha_se[i][0]
                t = alpha_t[i][0]
                p = alpha_p[i][0]
                sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""
                print(f"    {name}: alpha={a:.6f}, SE={se:.6f}, t={t:.3f}, p={p:.4f}{sig}")
        except AttributeError:
            print("  (stderr_alpha not available as attribute, parsing summary)")
            vecm_results["alpha_stderr_note"] = "Extracted from summary text; see summary_text field"

        irf = vecm.irf(26)
    else:
        print("\nNo cointegration. VAR in first differences:")
        diff = log_df.diff().dropna()
        var_fit = VAR(diff).fit(maxlags=8, ic="aic")
        vecm_results = {"note": "No cointegration. VAR in differences.", "var_lag": var_fit.k_ar}
        irf = var_fit.irf(26)

    # IRF plot
    setup_plot_style()
    fig, axes = plt.subplots(n_vars, n_vars, figsize=(12, 10))
    fig.suptitle("Impulse Response Functions (26-Week Horizon)", fontsize=14, fontweight="bold")
    for i in range(n_vars):
        for j in range(n_vars):
            ax = axes[i, j]
            ax.plot(range(27), irf.irfs[:, i, j], color=color("primary"), linewidth=1.5)
            ax.axhline(0, color="black", linewidth=0.5)
            ax.set_title(f"{var_names[j]} -> {var_names[i]}", fontsize=9)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    save_exhibit(fig, "exhibit10_impulse_response.png", "Source: FRED, DefiLlama.")

    # Engle-Granger bivariate
    print("\nEngle-Granger (Fed assets vs supply):")
    eg_stat, eg_p, eg_crit = eg_coint(log_df["total_supply"].values, log_df["WSHOMCB"].values)
    eg_result = {"stat": round(float(eg_stat), 3), "p": round(float(eg_p), 4),
                 "cointegrated_5pct": bool(eg_p < 0.05)}
    print(f"  stat={eg_stat:.3f}, p={eg_p:.4f}, cointegrated={eg_result['cointegrated_5pct']}")

    # Save
    save_json({"adf": adf, "johansen": johansen_results, "engle_granger": eg_result}, "cointegration_results.json")
    save_json(vecm_results, "vecm_coefficients.json")

    print("\n" + "=" * 60)
    if johansen_results["cointegrated"]:
        print("RESULT: Cointegration FOUND. r = -0.94 reflects structural relationship.")
        print("ACTION: Revise abstract to 'cointegrated with Fed balance sheet assets'")
    else:
        print("RESULT: No cointegration. r = -0.94 is spurious (co-movement of I(1) series).")
        print("ACTION: Lead with Granger causality. Relegate level correlation to descriptive.")
    print("=" * 60)

if __name__ == "__main__":
    main()
