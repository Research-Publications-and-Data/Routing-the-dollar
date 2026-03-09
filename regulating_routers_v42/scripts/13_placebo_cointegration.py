"""13_placebo_cointegration.py — Falsification test using BTC and ETH.

If BTC/ETH market cap do NOT cointegrate with Fed assets + ON RRP,
it proves the stablecoin result is dollar-specific, not a generic
crypto-macro relationship. This is the "falsification" evidence vector.

Output: data/processed/placebo_cointegration.json
"""
import pandas as pd, numpy as np, json, sys, time, warnings
warnings.filterwarnings("ignore")
from statsmodels.tsa.vector_ar.vecm import coint_johansen
from statsmodels.tsa.stattools import adfuller
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json

LAGS = [4, 6, 8, 10, 12]

def fetch_price_defillama(coin_id, start="2023-02-01", end="2026-01-31"):
    """Fetch weekly prices from DefiLlama historical endpoint, derive pseudo-mcap.

    DefiLlama's /prices/historical/{timestamp}/coingecko:{id} gives price at a
    specific time. We sample weekly to stay within rate limits. For cointegration
    we only need relative movement, so price * a fixed supply approximation works
    (or we can just use price, since mcap = price * supply and supply changes slowly).
    """
    import requests
    dates = pd.date_range(start, end, freq="W-WED")
    prices = {}
    for dt in dates:
        ts = int(dt.timestamp())
        try:
            resp = requests.get(
                f"https://coins.llama.fi/prices/historical/{ts}/coingecko:{coin_id}",
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json().get("coins", {}).get(f"coingecko:{coin_id}", {})
                p = data.get("price")
                if p:
                    prices[dt] = p
        except:
            pass
        time.sleep(0.1)  # be gentle

    s = pd.Series(prices, name=f"{coin_id}_mcap")
    # Scale to approximate mcap (BTC ~19.8M supply, ETH ~120M supply)
    supply_approx = {"bitcoin": 19_800_000, "ethereum": 120_000_000}
    if coin_id in supply_approx:
        s = s * supply_approx[coin_id]
    return s

def run_johansen_multi_lag(log_df, lags):
    """Run Johansen at multiple lags, return results dict."""
    results = {}
    for lag in lags:
        k = max(1, lag - 1)
        try:
            joh = coint_johansen(log_df, det_order=0, k_ar_diff=k)
            trace_pass = bool(joh.lr1[0] > joh.cvt[0, 1])
            maxeig_pass = bool(joh.lr2[0] > joh.cvm[0, 1])
            results[lag] = {
                "trace_stat": round(float(joh.lr1[0]), 2),
                "trace_cv95": round(float(joh.cvt[0, 1]), 2),
                "trace_pass": trace_pass,
                "maxeig_stat": round(float(joh.lr2[0]), 2),
                "maxeig_cv95": round(float(joh.cvm[0, 1]), 2),
                "maxeig_pass": maxeig_pass,
            }
        except Exception as e:
            results[lag] = {"error": str(e)}
    return results

def main():
    print("=" * 60)
    print("PLACEBO COINTEGRATION: BTC & ETH vs FED + ON RRP")
    print("=" * 60)

    # Load Fed data
    fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
    fed_weekly = fred[["WSHOMCB", "RRPONTSYD"]].resample("W-WED").last().dropna()
    fed_weekly["RRPONTSYD"] = fed_weekly["RRPONTSYD"].ffill()
    fed_primary = fed_weekly["2023-02-01":"2026-01-31"]

    results = {"placebos": {}, "stablecoin_reference": {}}

    # Fetch BTC and ETH
    for coin_id, name in [("bitcoin", "BTC"), ("ethereum", "ETH")]:
        print(f"\n--- {name} ---")
        try:
            mcap = fetch_price_defillama(coin_id)
            print(f"  Fetched {len(mcap)} weekly observations via DefiLlama")
        except Exception as e:
            print(f"  ERROR fetching {name}: {e}")
            results["placebos"][name] = {"error": str(e)}
            time.sleep(5)
            continue

        # Merge with Fed data (already weekly from DefiLlama)
        merged = fed_primary.join(pd.DataFrame(mcap), how="inner").dropna()
        if len(merged) < 50:
            print(f"  Only {len(merged)} observations after merge, skipping")
            results["placebos"][name] = {"error": f"Insufficient data: {len(merged)} obs"}
            continue

        log_df = np.log(merged.replace(0, np.nan).dropna())
        log_df.columns = ["WSHOMCB", "RRPONTSYD", f"{name}_mcap"]
        print(f"  Sample: {len(log_df)} weeks")

        # ADF tests
        adf_level = adfuller(log_df[f"{name}_mcap"], autolag="AIC")
        adf_diff = adfuller(log_df[f"{name}_mcap"].diff().dropna(), autolag="AIC")
        print(f"  ADF level p={adf_level[1]:.4f}, diff p={adf_diff[1]:.4f}")

        coin_result = {
            "n_weeks": len(log_df),
            "adf_level_p": round(adf_level[1], 4),
            "adf_diff_p": round(adf_diff[1], 4),
            "johansen": {},
        }

        # Run Johansen at all lags
        joh_results = run_johansen_multi_lag(log_df, LAGS)
        coin_result["johansen"] = joh_results

        pass_count = sum(1 for v in joh_results.values()
                         if isinstance(v, dict) and v.get("trace_pass", False))
        coin_result["trace_pass_count"] = pass_count
        coin_result["cointegrated"] = pass_count > 0

        print(f"\n  {'Lag':<6}{'Trace':<10}{'cv95':<10}{'Pass?':<8}")
        print("  " + "-" * 34)
        for lag in LAGS:
            r = joh_results.get(lag, {})
            if "error" in r:
                print(f"  {lag:<6} ERROR: {r['error']}")
            else:
                mark = "✓" if r["trace_pass"] else "✗"
                print(f"  {lag:<6}{r['trace_stat']:<10}{r['trace_cv95']:<10}{mark}")

        if pass_count == 0:
            coin_result["verdict"] = f"{name} does NOT cointegrate with Fed variables at any lag"
            print(f"\n  ✓ FALSIFICATION PASSES: {name} not cointegrated")
        else:
            coin_result["verdict"] = f"{name} cointegrates at {pass_count}/{len(LAGS)} lags — falsification FAILS"
            print(f"\n  ✗ UNEXPECTED: {name} cointegrates at {pass_count} lags")

        results["placebos"][name] = coin_result

    # Also record stablecoin reference (from lag_sensitivity.json)
    try:
        with open(DATA_PROC / "lag_sensitivity.json") as f:
            lag_ref = json.load(f)
        results["stablecoin_reference"] = {
            "trace_pass_count": lag_ref["summary"]["trace_pass_95_count"],
            "note": "From B.1 lag sensitivity"
        }
    except:
        results["stablecoin_reference"] = {"note": "Run B.1 first"}

    # Overall verdict
    btc_coint = results["placebos"].get("BTC", {}).get("cointegrated", None)
    eth_coint = results["placebos"].get("ETH", {}).get("cointegrated", None)

    if btc_coint is False and eth_coint is False:
        results["overall_verdict"] = "CLEAN FALSIFICATION"
        results["paper_sentence"] = (
            "As a falsification check, we repeat the Johansen procedure replacing stablecoin "
            "supply with Bitcoin and Ethereum market capitalization. Neither crypto asset "
            "cointegrates with Federal Reserve balance sheet variables at any tested lag "
            f"specification (lags {', '.join(str(l) for l in LAGS)}), confirming that the "
            "cointegrating relationship documented above is specific to dollar-denominated "
            "stablecoins rather than a generic feature of crypto-macro co-movement."
        )
        print(f"\n{'='*60}")
        print("OVERALL: CLEAN FALSIFICATION — stablecoin result is dollar-specific")
    elif btc_coint is False or eth_coint is False:
        which_fails = "BTC" if btc_coint else "ETH"
        which_passes = "ETH" if btc_coint else "BTC"
        results["overall_verdict"] = "PARTIAL FALSIFICATION"
        results["paper_sentence"] = (
            f"As a falsification check, {which_fails} market capitalization does not cointegrate "
            f"with Fed variables at any lag, but {which_passes} does at some specifications. "
            f"The partial result suggests the stablecoin relationship may partly reflect "
            f"broader crypto-dollar dynamics rather than being purely stablecoin-specific."
        )
        print(f"\n{'='*60}")
        print(f"PARTIAL: {which_fails} clean, {which_passes} unexpected cointegration")
    else:
        results["overall_verdict"] = "FALSIFICATION FAILS"
        results["paper_sentence"] = (
            "Both Bitcoin and Ethereum market capitalization also cointegrate with Fed "
            "variables, suggesting the relationship may reflect a broader crypto-macro "
            "channel rather than a stablecoin-specific mechanism. This does not invalidate "
            "the gateway analysis but limits the causal specificity of the cointegration finding."
        )
        print(f"\n{'='*60}")
        print("FAILS: Both BTC and ETH also cointegrate — result not stablecoin-specific")

    print(f"\nPaper sentence: {results['paper_sentence']}")
    save_json(results, "placebo_cointegration.json")
    print("\n✓ Done")

if __name__ == "__main__":
    main()
