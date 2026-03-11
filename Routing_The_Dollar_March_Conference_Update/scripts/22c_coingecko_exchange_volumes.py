"""22c: Pull exchange-level volume data from CoinGecko.

Gets relative market share proportions for major exchanges.
Used to disaggregate Artemis category aggregates into entity-level estimates.
"""
import requests, pandas as pd, time, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import COINGECKO_API_KEY
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json, save_csv

# Use pro API if key available, otherwise free tier
CG_BASE = "https://pro-api.coingecko.com/api/v3" if COINGECKO_API_KEY else "https://api.coingecko.com/api/v3"

EXCHANGES = [
    {"id": "binance", "entity": "Binance", "tier": 2},
    {"id": "kraken", "entity": "Kraken", "tier": 2},
    {"id": "okx", "entity": "OKX", "tier": 2},
    {"id": "gdax", "entity": "Coinbase", "tier": 1},
    {"id": "bybit_spot", "entity": "Bybit", "tier": 2},
    {"id": "huobi", "entity": "HTX", "tier": 2},
    {"id": "gemini", "entity": "Gemini", "tier": 1},
    {"id": "crypto_com", "entity": "Crypto.com", "tier": 2},
    {"id": "kucoin", "entity": "KuCoin", "tier": 2},
]


def get_headers():
    headers = {"accept": "application/json"}
    if COINGECKO_API_KEY:
        headers["x-cg-pro-api-key"] = COINGECKO_API_KEY
    return headers


def fetch_exchange_info(exchange_id):
    """Fetch exchange metadata including 24h volume."""
    try:
        resp = requests.get(f"{CG_BASE}/exchanges/{exchange_id}",
                           headers=get_headers(), timeout=30)
        if resp.status_code == 429:
            print(f"    Rate limited, waiting 30s...")
            time.sleep(30)
            return fetch_exchange_info(exchange_id)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "name": data.get("name", exchange_id),
                "trust_score": data.get("trust_score"),
                "trust_score_rank": data.get("trust_score_rank"),
                "trade_volume_24h_btc": data.get("trade_volume_24h_btc", 0),
                "trade_volume_24h_btc_normalized": data.get("trade_volume_24h_btc_normalized", 0),
                "country": data.get("country"),
                "year_established": data.get("year_established"),
            }
        else:
            print(f"    HTTP {resp.status_code} for {exchange_id}")
    except Exception as e:
        print(f"    Error: {e}")
    return None


def fetch_volume_chart(exchange_id, days=365):
    """Fetch historical volume chart for an exchange."""
    try:
        resp = requests.get(f"{CG_BASE}/exchanges/{exchange_id}/volume_chart",
                           params={"days": days},
                           headers=get_headers(), timeout=30)
        if resp.status_code == 429:
            print(f"    Rate limited, waiting 30s...")
            time.sleep(30)
            return fetch_volume_chart(exchange_id, days)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                rows = [{"date": pd.to_datetime(ts, unit="ms").normalize(),
                         "volume_btc": float(vol)}
                        for ts, vol in data]
                return pd.DataFrame(rows).set_index("date")
        else:
            print(f"    HTTP {resp.status_code} for volume_chart/{exchange_id}")
    except Exception as e:
        print(f"    Error: {e}")
    return None


def main():
    print("=" * 60)
    print("COINGECKO EXCHANGE VOLUME DATA")
    print("=" * 60)

    exchange_data = []
    volume_charts = {}

    for ex in EXCHANGES:
        eid = ex["id"]
        entity = ex["entity"]
        print(f"\n--- {entity} ({eid}) ---")

        # Exchange metadata
        info = fetch_exchange_info(eid)
        if info:
            info["exchange_id"] = eid
            info["entity"] = entity
            info["tier"] = ex["tier"]
            exchange_data.append(info)
            vol_24h = info.get("trade_volume_24h_btc_normalized", 0)
            print(f"  24h vol (BTC normalized): {vol_24h:,.0f}")
            print(f"  Trust rank: {info.get('trust_score_rank')}")
        else:
            print(f"  Failed to get info")
            exchange_data.append({"exchange_id": eid, "entity": entity, "tier": ex["tier"]})

        time.sleep(2)

        # Volume chart (365 days)
        chart = fetch_volume_chart(eid)
        if chart is not None and len(chart) > 0:
            volume_charts[entity] = chart
            print(f"  Volume chart: {len(chart)} days")
            # Monthly average
            monthly = chart.resample("ME").mean()
            print(f"  Avg monthly BTC vol: {monthly['volume_btc'].mean():,.0f}")
        else:
            print(f"  No volume chart data")

        time.sleep(2)

    # Compute market shares
    df_exchanges = pd.DataFrame(exchange_data)
    if "trade_volume_24h_btc_normalized" in df_exchanges.columns:
        total_vol = df_exchanges["trade_volume_24h_btc_normalized"].sum()
        if total_vol > 0:
            df_exchanges["market_share_pct"] = (
                df_exchanges["trade_volume_24h_btc_normalized"] / total_vol * 100
            )
        else:
            df_exchanges["market_share_pct"] = 0
    df_exchanges = df_exchanges.sort_values(
        "trade_volume_24h_btc_normalized", ascending=False, na_position="last"
    )

    # Save exchange summary
    path = DATA_RAW / "coingecko_exchange_volumes.csv"
    df_exchanges.to_csv(path, index=False)
    print(f"\n  Saved: {path}")

    # Save volume charts as monthly aggregates
    if volume_charts:
        monthly_frames = {}
        for entity, chart in volume_charts.items():
            monthly = chart.resample("ME").mean()
            monthly_frames[entity] = monthly["volume_btc"]
        monthly_df = pd.DataFrame(monthly_frames)
        monthly_df.index.name = "date"
        path2 = DATA_RAW / "coingecko_exchange_monthly_volumes.csv"
        monthly_df.to_csv(path2)
        print(f"  Saved: {path2}")

    # Summary
    print("\n" + "=" * 60)
    print("EXCHANGE MARKET SHARES (24h normalized)")
    print("-" * 60)
    for _, row in df_exchanges.iterrows():
        share = row.get("market_share_pct", 0)
        vol = row.get("trade_volume_24h_btc_normalized", 0)
        print(f"  {row['entity']:15s} | {vol:>12,.0f} BTC | {share:>5.1f}%")
    print("=" * 60)

    # Save as JSON for downstream scripts
    shares = {}
    for _, row in df_exchanges.iterrows():
        shares[row["entity"]] = {
            "market_share_pct": round(float(row.get("market_share_pct", 0)), 2),
            "trust_rank": int(row["trust_score_rank"]) if pd.notna(row.get("trust_score_rank")) else None,
            "tier": int(row["tier"]),
        }
    save_json(shares, "coingecko_exchange_shares.json")


if __name__ == "__main__":
    main()
