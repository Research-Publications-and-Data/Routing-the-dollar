"""Task 3: Pull extended stablecoin supply (2019-2026) from DefiLlama + CoinGecko."""
import requests, pandas as pd, numpy as np, time, sys, datetime
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "config"))
from settings import EXTENDED_START, PRIMARY_END, COINGECKO_API_KEY, STABLECOIN_IDS_DEFILLAMA, STABLECOIN_IDS_COINGECKO
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_csv, save_json

def pull_defillama(stablecoin_id, name):
    try:
        resp = requests.get(f"https://stablecoins.llama.fi/stablecoincharts/all?stablecoin={stablecoin_id}", timeout=30)
        resp.raise_for_status()
        rows = []
        for d in resp.json():
            ts = d["date"]
            # Handle unix timestamps (seconds)
            dt = datetime.datetime.utcfromtimestamp(int(ts))
            mcap = d.get("totalCirculating", {}).get("peggedUSD", 0)
            if mcap is None:
                mcap = 0
            rows.append({"date": pd.Timestamp(dt), f"{name}_mcap": float(mcap)})
        df = pd.DataFrame(rows).set_index("date")
        print(f"  DefiLlama {name}: {len(df)} days")
        return df
    except Exception as e:
        print(f"  DefiLlama {name}: FAILED ({e})")
        return pd.DataFrame()

def pull_coingecko(coin_id, name):
    """Use CoinGecko Pro market_chart endpoint."""
    headers = {}
    base_url = "https://api.coingecko.com/api/v3"
    if COINGECKO_API_KEY:
        headers["x-cg-pro-api-key"] = COINGECKO_API_KEY
        base_url = "https://pro-api.coingecko.com/api/v3"
    all_rows = []
    # Break into yearly chunks
    start = pd.Timestamp(EXTENDED_START)
    end = pd.Timestamp(PRIMARY_END)
    current = start
    while current < end:
        chunk_end = min(current + pd.Timedelta(days=364), end)
        start_ts = int(current.timestamp())
        end_ts = int(chunk_end.timestamp())
        try:
            resp = requests.get(f"{base_url}/coins/{coin_id}/market_chart/range",
                               params={"vs_currency": "usd", "from": start_ts, "to": end_ts},
                               headers=headers, timeout=30)
            if resp.status_code == 429:
                print(f"    Rate limited, waiting 60s...")
                time.sleep(60)
                resp = requests.get(f"{base_url}/coins/{coin_id}/market_chart/range",
                                   params={"vs_currency": "usd", "from": start_ts, "to": end_ts},
                                   headers=headers, timeout=30)
            resp.raise_for_status()
            for ts, mcap in resp.json().get("market_caps", []):
                dt = pd.Timestamp(datetime.datetime.utcfromtimestamp(ts / 1000)).normalize()
                all_rows.append({"date": dt, f"{name}_mcap": mcap})
        except Exception as e:
            print(f"    CoinGecko {name} chunk {current.date()}-{chunk_end.date()}: {e}")
        current = chunk_end + pd.Timedelta(days=1)
        time.sleep(6)  # Rate limit: 10-30 calls/min on free tier
    if all_rows:
        df = pd.DataFrame(all_rows).drop_duplicates("date").set_index("date")
        print(f"  CoinGecko {name}: {len(df)} days")
        return df
    print(f"  CoinGecko {name}: no data")
    return pd.DataFrame()

def main():
    print("Extended Stablecoin Supply Data\n")
    frames = {}

    # DefiLlama first (free, no auth, better coverage)
    for dl_id, name in STABLECOIN_IDS_DEFILLAMA.items():
        df = pull_defillama(dl_id, name)
        if len(df) > 0: frames[name] = df
        time.sleep(1)

    # CoinGecko for any missing (skip if already have >500 days from DefiLlama)
    for cg_id, name in STABLECOIN_IDS_COINGECKO.items():
        if name in frames and len(frames[name]) > 500:
            print(f"  Skipping CoinGecko {name} (already have {len(frames[name])} days from DefiLlama)")
            continue
        df = pull_coingecko(cg_id, name)
        if len(df) > 0: frames[name] = df
        time.sleep(3)

    if not frames:
        print("ERROR: No stablecoin data retrieved. Check network/API access.")
        sys.exit(1)

    combined = pd.concat(frames.values(), axis=1).sort_index().ffill(limit=3)
    mcap_cols = [c for c in combined.columns if "_mcap" in c]
    combined["total_supply"] = combined[mcap_cols].sum(axis=1)
    combined = combined[EXTENDED_START:PRIMARY_END]
    save_csv(combined, "stablecoin_supply_extended.csv", directory=DATA_RAW)

    # Merge with FRED
    unified = None
    try:
        fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
        unified = combined.join(fred, how="outer").sort_index()[EXTENDED_START:PRIMARY_END]
        save_csv(unified, "unified_extended_dataset.csv")
    except FileNotFoundError:
        print("WARNING: FRED data not found. Run Task 1 first.")

    # Subsample correlations
    if unified is not None:
        try:
            weekly = unified[["total_supply", "WSHOMCB"]].resample("W-WED").last().dropna()
            subsamples = {"pre_covid": ("2019-01-01", "2020-02-29"),
                          "covid_qe": ("2020-03-01", "2022-03-31"),
                          "tightening": ("2022-04-01", "2024-08-31"),
                          "easing": ("2024-09-01", "2026-01-31"),
                          "full": (EXTENDED_START, PRIMARY_END)}
            results = {}
            for name, (s, e) in subsamples.items():
                sub = weekly[s:e].dropna()
                if len(sub) > 10:
                    r = sub["total_supply"].corr(sub["WSHOMCB"])
                    results[name] = {"r": round(r, 4), "n": len(sub)}
                    print(f"  {name}: r = {r:.4f} (n={len(sub)})")
            save_json(results, "subsample_correlations.json")
        except Exception as e:
            print(f"  Subsample analysis: {e}")

    # Validate
    print("\nValidation:")
    for date, (lo, hi) in {"2021-01-15": (20, 35), "2022-05-15": (150, 200), "2026-01-15": (280, 330)}.items():
        try:
            val = combined.loc[date:date, "total_supply"].iloc[0] / 1e9
            print(f"  {date}: ${val:.1f}B (expected ${lo}-${hi}B) {'OK' if lo <= val <= hi else 'MISMATCH'}")
        except:
            print(f"  {date}: no data available")
    print("Done")

if __name__ == "__main__":
    main()
