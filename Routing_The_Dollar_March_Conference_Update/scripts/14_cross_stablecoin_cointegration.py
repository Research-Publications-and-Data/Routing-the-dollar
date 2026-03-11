"""14_cross_stablecoin_cointegration.py — Per-issuer Johansen tests.

Tests whether USDT-only and USDC-only each individually cointegrate with
Fed + ON RRP. Determines if the aggregate result is compositional (driven
by one issuer) or structural (both respond). Also extracts per-issuer
alpha adjustment coefficients.

Output: data/processed/cross_stablecoin_cointegration.json
"""
import pandas as pd, numpy as np, json, sys, warnings
warnings.filterwarnings("ignore")
from statsmodels.tsa.vector_ar.vecm import coint_johansen, VECM
from statsmodels.tsa.stattools import adfuller
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json

LAGS = [4, 6, 8, 10, 12]

def load_individual_supplies():
    """Load USDT and USDC individual supply from the extended dataset or raw data."""
    try:
        raw = pd.read_csv(DATA_RAW / "stablecoin_supply_extended.csv", index_col=0, parse_dates=True)
        usdt_cols = [c for c in raw.columns if "USDT" in c and "mcap" in c]
        usdc_cols = [c for c in raw.columns if "USDC" in c and "mcap" in c]
        usdt = raw[usdt_cols[0]] if usdt_cols else None
        usdc = raw[usdc_cols[0]] if usdc_cols else None
        return usdt, usdc
    except FileNotFoundError:
        pass

    # Fallback: fetch from DefiLlama
    print("  Fetching individual supplies from DefiLlama...")
    import requests
    supplies = {}
    for dl_id, name in [(1, "USDT"), (2, "USDC")]:
        resp = requests.get(f"https://stablecoins.llama.fi/stablecoincharts/all?stablecoin={dl_id}", timeout=30)
        rows = {pd.to_datetime(d["date"], unit="s"): d.get("totalCirculating", {}).get("peggedUSD", 0)
                for d in resp.json()}
        supplies[name] = pd.Series(rows, name=f"{name}_mcap")
    return supplies.get("USDT"), supplies.get("USDC")

def run_johansen_multi_lag(log_df, lags):
    results = {}
    for lag in lags:
        k = max(1, lag - 1)
        try:
            joh = coint_johansen(log_df, det_order=0, k_ar_diff=k)
            results[lag] = {
                "trace_stat": round(float(joh.lr1[0]), 2),
                "trace_cv95": round(float(joh.cvt[0, 1]), 2),
                "trace_pass": bool(joh.lr1[0] > joh.cvt[0, 1]),
                "maxeig_stat": round(float(joh.lr2[0]), 2),
                "maxeig_cv95": round(float(joh.cvm[0, 1]), 2),
                "maxeig_pass": bool(joh.lr2[0] > joh.cvm[0, 1]),
            }
        except Exception as e:
            results[lag] = {"error": str(e)}
    return results

def extract_alpha(log_df, k_ar_diff, var_names):
    """Fit VECM and extract alpha coefficients with SEs."""
    try:
        vecm_fit = VECM(log_df, k_ar_diff=k_ar_diff, coint_rank=1).fit()
        alpha_info = {}
        for i, name in enumerate(var_names):
            a = float(vecm_fit.alpha[i, 0])
            try:
                se = float(vecm_fit.stderr_alpha[i, 0])
                t = float(vecm_fit.tvalues_alpha[i, 0])
                p = float(vecm_fit.pvalues_alpha[i, 0])
            except:
                se, t, p = None, None, None
            alpha_info[name] = {"alpha": round(a, 6), "se": round(se, 6) if se else None,
                                "t": round(t, 3) if t else None, "p": round(p, 4) if p else None}
        beta = vecm_fit.beta.flatten().tolist()
        return {"alpha": alpha_info, "beta": [round(b, 6) for b in beta]}
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=" * 60)
    print("CROSS-STABLECOIN COINTEGRATION: USDT vs USDC")
    print("=" * 60)

    # Load Fed data
    fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
    fed = fred[["WSHOMCB", "RRPONTSYD"]].copy()
    fed["RRPONTSYD"] = fed["RRPONTSYD"].ffill()

    # Load individual supplies
    usdt_raw, usdc_raw = load_individual_supplies()
    results = {"tokens": {}}

    for name, supply_raw in [("USDT", usdt_raw), ("USDC", usdc_raw)]:
        print(f"\n{'='*40}")
        print(f"  {name}")
        print(f"{'='*40}")

        if supply_raw is None or len(supply_raw) == 0:
            print(f"  ERROR: No data for {name}")
            results["tokens"][name] = {"error": "No data available"}
            continue

        # Merge with Fed data at weekly frequency
        supply_weekly = supply_raw.resample("W-WED").last()
        merged = fed.join(pd.DataFrame(supply_weekly), how="inner").dropna()
        merged = merged["2023-02-01":"2026-01-31"]

        if len(merged) < 50:
            print(f"  Only {len(merged)} obs, skipping")
            results["tokens"][name] = {"error": f"Insufficient data: {len(merged)}"}
            continue

        log_df = np.log(merged.replace(0, np.nan).dropna())
        col_name = log_df.columns[-1]  # supply column name
        log_df.columns = ["WSHOMCB", "RRPONTSYD", f"{name}_supply"]
        var_names = list(log_df.columns)
        print(f"  Sample: {len(log_df)} weeks, {log_df.index[0].date()} to {log_df.index[-1].date()}")

        # ADF
        adf_lev = adfuller(log_df[f"{name}_supply"], autolag="AIC")
        adf_dif = adfuller(log_df[f"{name}_supply"].diff().dropna(), autolag="AIC")
        print(f"  ADF: level p={adf_lev[1]:.4f}, diff p={adf_dif[1]:.4f}")

        # Johansen at all lags
        joh = run_johansen_multi_lag(log_df, LAGS)
        pass_count = sum(1 for v in joh.values() if isinstance(v, dict) and v.get("trace_pass", False))

        print(f"\n  {'Lag':<6}{'Trace':<10}{'cv95':<10}{'Pass?':<8}{'λ-max':<10}{'cv95':<10}{'Pass?':<8}")
        print("  " + "-" * 56)
        for lag in LAGS:
            r = joh.get(lag, {})
            if "error" in r:
                print(f"  {lag:<6} ERROR")
            else:
                tm = "✓" if r["trace_pass"] else "✗"
                mm = "✓" if r["maxeig_pass"] else "✗"
                print(f"  {lag:<6}{r['trace_stat']:<10}{r['trace_cv95']:<10}{tm:<8}{r['maxeig_stat']:<10}{r['maxeig_cv95']:<10}{mm:<8}")

        # Extract alpha at AIC-optimal lag (8)
        vecm_result = extract_alpha(log_df, k_ar_diff=7, var_names=var_names)

        token_result = {
            "n_weeks": len(log_df),
            "adf_level_p": round(adf_lev[1], 4),
            "adf_diff_p": round(adf_dif[1], 4),
            "johansen": joh,
            "trace_pass_count": pass_count,
            "cointegrated": pass_count > 0,
            "vecm_lag8": vecm_result,
        }

        if pass_count > 0:
            print(f"\n  ✓ {name} cointegrates at {pass_count}/{len(LAGS)} lags")
        else:
            print(f"\n  ✗ {name} does NOT cointegrate at any tested lag")

        # Print alpha if available
        if "alpha" in vecm_result:
            supply_alpha = vecm_result["alpha"].get(f"{name}_supply", {})
            a = supply_alpha.get("alpha", "N/A")
            p = supply_alpha.get("p", "N/A")
            sig = ""
            if isinstance(p, float):
                sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""
            print(f"  Alpha ({name} supply): {a} (p={p}){sig}")

        results["tokens"][name] = token_result

    # Comparative analysis
    usdt_coint = results["tokens"].get("USDT", {}).get("cointegrated", None)
    usdc_coint = results["tokens"].get("USDC", {}).get("cointegrated", None)
    usdt_pass = results["tokens"].get("USDT", {}).get("trace_pass_count", 0)
    usdc_pass = results["tokens"].get("USDC", {}).get("trace_pass_count", 0)

    print(f"\n{'='*60}")
    print("COMPARATIVE RESULTS")
    print(f"{'='*60}")
    print(f"  USDT: {usdt_pass}/{len(LAGS)} lags pass {'(cointegrated)' if usdt_coint else '(NOT cointegrated)'}")
    print(f"  USDC: {usdc_pass}/{len(LAGS)} lags pass {'(cointegrated)' if usdc_coint else '(NOT cointegrated)'}")

    if usdt_coint and usdc_coint:
        results["verdict"] = "STRUCTURAL"
        results["paper_sentence"] = (
            "Both USDT and USDC individually cointegrate with Federal Reserve balance sheet "
            f"variables (USDT: {usdt_pass}/5 lags, USDC: {usdc_pass}/5 lags), indicating that "
            "the aggregate relationship is structural rather than compositional. The cointegrating "
            "equilibrium operates through both major issuers independently."
        )
        print("\n  VERDICT: STRUCTURAL — both tokens cointegrate independently")
    elif usdt_coint and not usdc_coint:
        results["verdict"] = "USDT_DOMINANT"
        usdt_alpha = results["tokens"]["USDT"].get("vecm_lag8", {}).get("alpha", {}).get("USDT_supply", {})
        results["paper_sentence"] = (
            f"USDT individually cointegrates with Fed variables ({usdt_pass}/5 lags) "
            f"while USDC does not, suggesting the aggregate result is primarily driven "
            f"by Tether's reserve management practices rather than a uniform stablecoin response. "
            f"USDT's adjustment coefficient (alpha = {usdt_alpha.get('alpha', 'N/A')}) indicates "
            f"it bears the primary equilibrium-correction burden."
        )
        print("\n  VERDICT: USDT-DOMINANT — aggregate result driven by Tether")
    elif usdc_coint and not usdt_coint:
        results["verdict"] = "USDC_DOMINANT"
        usdc_alpha = results["tokens"]["USDC"].get("vecm_lag8", {}).get("alpha", {}).get("USDC_supply", {})
        results["paper_sentence"] = (
            f"USDC individually cointegrates with Fed variables ({usdc_pass}/5 lags) "
            f"while USDT does not, suggesting the aggregate result operates through "
            f"Circle's direct banking relationships and reserve composition rather than "
            f"the broader stablecoin market."
        )
        print("\n  VERDICT: USDC-DOMINANT — aggregate result driven by Circle")
    else:
        results["verdict"] = "COMPOSITIONAL"
        results["paper_sentence"] = (
            "Neither USDT nor USDC individually cointegrates with Fed variables, "
            "suggesting the aggregate cointegration is a compositional artifact arising "
            "from the combination of the two series. This limits the structural interpretation "
            "of the headline result."
        )
        print("\n  VERDICT: COMPOSITIONAL — neither token cointegrates alone")

    print(f"\n  Paper sentence: {results['paper_sentence']}")
    save_json(results, "cross_stablecoin_cointegration.json")
    print("\n✓ Done")

if __name__ == "__main__":
    main()
