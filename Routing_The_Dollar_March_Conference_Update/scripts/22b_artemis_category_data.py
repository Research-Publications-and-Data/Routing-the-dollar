"""22b: Pull category-level stablecoin volumes from Artemis API.

Gets CEX vs DeFi vs P2P breakdown for Solana and Tron.
Used for: (a) Tier 3 DeFi aggregate volumes, (b) cross-validation of Dune CEX data.
"""
import requests, pandas as pd, time, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import PRIMARY_START, PRIMARY_END, ARTEMIS_API_KEY
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json, save_csv

BASE_URL = "https://data-svc.artemisxyz.com/data/api"

# Chains and their available category breakdowns
# Only eth, sol, base support category prefixes (cex-, defi-, etc.)
CHAIN_CATEGORIES = {
    "sol": ["sol", "cex-sol", "defi-sol"],
    "tron": ["tron"],  # Tron may not support category prefixes
}


def fetch_metric(symbols, metric, start, end, granularity="MONTH"):
    """Fetch a metric from Artemis API."""
    url = (f"{BASE_URL}/{metric}?symbols={symbols}"
           f"&startDate={start}&endDate={end}&granularity={granularity}"
           f"&APIKey={ARTEMIS_API_KEY}")
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 429:
            print("    Rate limited, waiting 5s...")
            time.sleep(5)
            return fetch_metric(symbols, metric, start, end, granularity)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                syms = data.get("data", {})
                if isinstance(syms, dict):
                    syms = syms.get("symbols", syms)
                    if isinstance(syms, dict):
                        return syms
        else:
            print(f"    HTTP {resp.status_code} for {metric}/{symbols}: {resp.text[:200]}")
    except Exception as e:
        print(f"    Error: {e}")
    return {}


def extract_series(api_result, symbol, metric):
    """Extract a time series from API result into a pandas Series."""
    sym_data = api_result.get(symbol, {})
    if not isinstance(sym_data, dict):
        return pd.Series(dtype=float)
    vals = sym_data.get(metric, [])
    if not isinstance(vals, list) or len(vals) == 0:
        return pd.Series(dtype=float)
    return pd.Series(
        {pd.Timestamp(v["date"]): v["val"] for v in vals if "val" in v and "date" in v},
        dtype=float
    )


def pull_chain_categories(chain, symbols_list, start, end):
    """Pull total + category volumes for a chain."""
    metric = "ARTEMIS_STABLECOIN_TRANSFER_VOLUME"
    results = {}

    for symbol in symbols_list:
        print(f"  Fetching {metric} for {symbol}...")
        api_data = fetch_metric(symbol, metric, start, end)
        series = extract_series(api_data, symbol, metric)
        if len(series) > 0:
            col_name = symbol.replace("-", "_")
            results[col_name] = series
            total_vol = series.sum()
            print(f"    OK: {len(series)} months, total=${total_vol/1e9:.1f}B")
        else:
            print(f"    No data for {symbol}")
        time.sleep(0.5)

    # Also try P2P volume
    print(f"  Fetching P2P_STABLECOIN_TRANSFER_VOLUME for {chain}...")
    p2p_data = fetch_metric(chain, "P2P_STABLECOIN_TRANSFER_VOLUME", start, end)
    p2p_series = extract_series(p2p_data, chain, "P2P_STABLECOIN_TRANSFER_VOLUME")
    if len(p2p_series) > 0:
        results[f"p2p_{chain}"] = p2p_series
        print(f"    OK: {len(p2p_series)} months, total=${p2p_series.sum()/1e9:.1f}B")
    else:
        print(f"    No P2P data for {chain}")

    # Also try stablecoin supply
    print(f"  Fetching STABLECOIN_SUPPLY for {chain}...")
    supply_data = fetch_metric(chain, "STABLECOIN_SUPPLY", start, end)
    supply_series = extract_series(supply_data, chain, "STABLECOIN_SUPPLY")
    if len(supply_series) > 0:
        results[f"supply_{chain}"] = supply_series
        print(f"    OK: {len(supply_series)} months, latest=${supply_series.iloc[-1]/1e9:.1f}B")
    else:
        print(f"    No supply data for {chain}")

    return results


def main():
    if not ARTEMIS_API_KEY:
        print("ERROR: Set ARTEMIS_API_KEY in config/settings.py")
        sys.exit(1)

    print("=" * 60)
    print("ARTEMIS CATEGORY-LEVEL STABLECOIN DATA")
    print("=" * 60)

    start, end = PRIMARY_START, PRIMARY_END
    all_results = {}

    for chain, symbols in CHAIN_CATEGORIES.items():
        print(f"\n--- {chain.upper()} ---")
        results = pull_chain_categories(chain, symbols, start, end)

        if results:
            df = pd.DataFrame(results)
            df.index.name = "date"
            df = df.sort_index()

            # Compute derived metrics if we have category data
            total_col = chain
            if total_col in df.columns:
                for cat_col in df.columns:
                    if cat_col.startswith(("cex_", "defi_", "p2p_")):
                        share_col = f"{cat_col}_share"
                        df[share_col] = df[cat_col] / df[total_col] * 100

            path = DATA_RAW / f"artemis_{chain}_categories.csv"
            df.to_csv(path)
            print(f"\n  Saved: {path}")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Rows: {len(df)}")

            # Summary stats
            summary = {}
            for col in df.columns:
                if "_share" not in col and "supply" not in col:
                    summary[col] = {
                        "total": float(df[col].sum()),
                        "mean_monthly": float(df[col].mean()),
                        "latest": float(df[col].iloc[-1]) if len(df) > 0 else 0,
                    }
            all_results[chain] = summary

    # Also try cex-tron and defi-tron even if not in official supported list
    print("\n--- TRON CATEGORY EXPLORATION ---")
    for cat in ["cex-tron", "defi-tron"]:
        print(f"  Trying {cat}...")
        data = fetch_metric(cat, "ARTEMIS_STABLECOIN_TRANSFER_VOLUME", start, end)
        series = extract_series(data, cat, "ARTEMIS_STABLECOIN_TRANSFER_VOLUME")
        if len(series) > 0:
            print(f"    OK: {len(series)} months, total=${series.sum()/1e9:.1f}B")
            # Append to tron CSV if it exists
            try:
                tron_df = pd.read_csv(DATA_RAW / "artemis_tron_categories.csv",
                                      index_col=0, parse_dates=True)
                col_name = cat.replace("-", "_")
                tron_df[col_name] = series
                tron_df.to_csv(DATA_RAW / "artemis_tron_categories.csv")
                all_results.setdefault("tron", {})[col_name] = {
                    "total": float(series.sum()),
                    "mean_monthly": float(series.mean()),
                }
            except FileNotFoundError:
                pass
        else:
            print(f"    No data (category may not be supported for Tron)")
        time.sleep(0.5)

    save_json(all_results, "artemis_category_summary.json")

    print("\n" + "=" * 60)
    print("ARTEMIS CATEGORY DATA COMPLETE")
    for chain, data in all_results.items():
        print(f"  {chain}: {len(data)} metrics")
        for metric, vals in data.items():
            print(f"    {metric}: total=${vals['total']/1e9:.1f}B")
    print("=" * 60)


if __name__ == "__main__":
    main()
