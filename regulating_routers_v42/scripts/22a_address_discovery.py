"""22a: Discover top-100 stablecoin addresses on Solana and Tron via Dune.

Creates 2 Dune queries to find the highest-volume USDC/USDT addresses,
then cross-references against known exchange labels. This addresses the
data gap where registry addresses (program IDs, stale wallets) returned
no data from token transfer queries.
"""
import requests, pandas as pd, time, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import DUNE_API_KEY, PRIMARY_START
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json

DUNE_API = "https://api.dune.com/api/v1"
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}
QUERIES_DIR = Path(__file__).resolve().parent.parent / "queries"

# Known Solana exchange addresses from public sources (Solscan, Arkham, etc.)
KNOWN_SOLANA_LABELS = {
    # Binance (confirmed working in our Dune queries)
    "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9": "Binance",
    # Coinbase (confirmed working)
    "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS": "Coinbase",
    "2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm": "Coinbase",
    "GJRs4FwHtemZ5ZE9x3FNvJ8TMwitKTh21yxdRPqn7npE": "Coinbase",
    # Kraken (multiple known wallets from Solscan/Arkham)
    "9Hm7ePxEsWsGa1Z5nfgUYzYNjXmVWvFzSghjNRPLWKGx": "Kraken",
    "CKZ7sAcEnMbHFBGnHVn7XVjrT5wUvGBSaJ5miFNFWcPa": "Kraken",
    "FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiWB5o": "Kraken",
    # OKX
    "5VCwKtCXgCDuQosQDbo8VKUvTen5tYtEqpNqkzfbqME2": "OKX",
    "5EFUmSHjnZ1oaSTBmtyz8PEoVvnoMZP4D8GiA9KmrEze": "OKX",
    "6TfCnFJkDPacNHodGbVm3Yqv1HX3uRFVvdb5x6GNsr4G": "OKX",
    # Bybit
    "AC5RDfQFmDS1deWZos921JfqscXdByf6BKHAbXh2dZnH": "Bybit",
    # Tether
    "Q6XprfkF8RQQKoQVG33xT88H7wi8Uk1B1CC7YAs69Gi": "Tether",
    # Circle (CCTP — these are token accounts, not the mint authority)
    "DcgJMCdZZQFMZ3moAjyWMGchBMze2JZVBZ7A5bAWRgji": "Circle (Mint Authority)",
    # Robinhood
    "5UYsQvBAQHECGriyx4M2G1FdgWsKWFHsPQzw94hfSfhz": "Robinhood",
    # HTX
    "HZyKJpsyTKgKSAFMLfHKkSVnPou1HDu1nMszayP2Gms": "HTX",
    # Jump Trading / Wormhole
    "CKqoNhm66MW8Vmv5auiqBDHGLnSVvs5dJQgd2QKZ7DWP": "Jump Trading",
}

# Known Tron exchange addresses from Tronscan
KNOWN_TRON_LABELS = {
    # Tether Treasury (confirmed working)
    "TYASr5UV6HEcXatwdFQfmLVUqQQQMUxHLS": "Tether",
    "TNXoiAJ3dct8Fjg4M9fkLFh9S2v9TXc32G": "Tether",
    # Binance
    "TJDENsfBJs4RFETt1X1W8wMDc8M5XnKhCF": "Binance",
    "TV6MuMXfmLbBqPZvBHdwFsDnQeVfnmiuEM": "Binance",
    "TYDzsYUEpvnYmQk4zGP9sWWcTEd2MiAtW": "Binance",
    "TNaRAoLUyYEV2uF7GUrzSjRQTU8v5ZJ5VR": "Binance",
    "TWd4WrZ9wn84f5x1hZhL4DHvk738ns5jwb": "Binance",
    # OKX
    "TJN6WeqBjghRHCeiE3jnb7TSAB3Rmcoy7o": "OKX",
    "TAiw9CDyEfKnimQ5bRQxDcJtGksc4KxUqK": "OKX",
    # HTX
    "TRD5yAQVd5DRSBGTsBjqzMtW777ZZsjHJk": "HTX",
    "THbRALfnEKRVvHPCZVVJEp8C7D7AhF3pCJ": "HTX",
    # Bybit (confirmed working)
    "TLPh66vQ2QMb64rG3WEBV5qnAhefh2kcdw": "Bybit",
    # Kraken
    "TBAo7PNyKo94YWUq1Cs2LBFxkhTgUmLzvR": "Kraken",
    # SunSwap
    "TKcEU8ekq2ZoFzLSGFYCUY6aocePBpCsRS": "SunSwap",
    # JustLend
    "TX7kybeP6UwTBRHLNPYmswFESHfyjm9bAS": "JustLend",
    # Crypto.com
    "TFczxzPhnThNSqr5by8tvxsdCFRRz6cPNq": "Crypto.com",
    # KuCoin
    "TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4": "KuCoin",
}


def create_query(name, sql):
    resp = requests.post(
        f"{DUNE_API}/query", headers=HEADERS,
        json={"name": f"disc_{name}", "query_sql": sql.strip(), "is_private": True},
        timeout=30)
    if resp.status_code != 200:
        print(f"    Create failed: {resp.status_code} {resp.text[:300]}")
        return None
    return resp.json().get("query_id")


def execute_query(query_id):
    resp = requests.post(
        f"{DUNE_API}/query/{query_id}/execute", headers=HEADERS,
        json={"performance": "medium"}, timeout=30)
    if resp.status_code != 200:
        print(f"    Execute failed: {resp.status_code} {resp.text[:300]}")
        return None
    return resp.json().get("execution_id")


def poll_and_fetch(execution_id, max_polls=120, interval=10):
    for attempt in range(max_polls):
        time.sleep(interval)
        try:
            resp = requests.get(f"{DUNE_API}/execution/{execution_id}/status",
                                headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                continue
            state = resp.json().get("state", "")
            if attempt % 5 == 0:
                print(f"    Poll {attempt+1}: {state}")
            if state == "QUERY_STATE_COMPLETED":
                break
            elif state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"):
                err = resp.json().get("error", "unknown")
                print(f"    FAILED: {err}")
                return None
        except Exception as e:
            if attempt % 5 == 0:
                print(f"    Poll error: {e}")
    else:
        print("    Timed out")
        return None
    results_resp = requests.get(f"{DUNE_API}/execution/{execution_id}/results",
                                headers=HEADERS, params={"limit": 500000}, timeout=120)
    if results_resp.status_code != 200:
        return None
    rows = results_resp.json().get("result", {}).get("rows", [])
    return pd.DataFrame(rows) if rows else None


def save_sql_fallback(name, sql):
    """Save SQL to queries/ dir for manual execution if API fails."""
    path = QUERIES_DIR / f"disc_{name}.sql"
    with open(path, "w") as f:
        f.write(sql)
    print(f"    SQL saved to {path} for manual Dune UI execution")


# ── SQL Queries ──────────────────────────────────────────────

SOLANA_TOP100_SQL = """
-- Top 100 Solana addresses by USDC+USDT volume (2024 only for memory)
SELECT
    addr,
    SUM(vol) AS total_volume,
    SUM(cnt) AS n_transfers
FROM (
    SELECT from_owner AS addr, SUM(amount) AS vol, COUNT(*) AS cnt
    FROM tokens_solana.transfers
    WHERE token_mint_address IN (
        'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'
    )
    AND block_time >= TIMESTAMP '2024-01-01'
    AND block_time < TIMESTAMP '2025-01-01'
    GROUP BY 1
    UNION ALL
    SELECT to_owner AS addr, SUM(amount) AS vol, COUNT(*) AS cnt
    FROM tokens_solana.transfers
    WHERE token_mint_address IN (
        'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'
    )
    AND block_time >= TIMESTAMP '2024-01-01'
    AND block_time < TIMESTAMP '2025-01-01'
    GROUP BY 1
) sub
WHERE addr != '11111111111111111111111111111111'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 100
"""

TRON_TOP100_SQL = """
-- Top 100 Tron addresses by USDT volume (2024 only for memory)
SELECT
    addr,
    SUM(vol) AS total_volume,
    SUM(cnt) AS n_transfers
FROM (
    SELECT from_varchar AS addr, SUM(amount) AS vol, COUNT(*) AS cnt
    FROM tokens_tron.transfers
    WHERE contract_address_varchar = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
    AND block_time >= TIMESTAMP '2024-01-01'
    AND block_time < TIMESTAMP '2025-01-01'
    GROUP BY 1
    UNION ALL
    SELECT to_varchar AS addr, SUM(amount) AS vol, COUNT(*) AS cnt
    FROM tokens_tron.transfers
    WHERE contract_address_varchar = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
    AND block_time >= TIMESTAMP '2024-01-01'
    AND block_time < TIMESTAMP '2025-01-01'
    GROUP BY 1
) sub
GROUP BY 1
ORDER BY 2 DESC
LIMIT 100
"""


def run_discovery(name, sql, known_labels):
    """Run a discovery query and label results."""
    print(f"\n--- {name} Top-100 Discovery ---")

    # Check for cached results
    cache_path = DATA_RAW / f"dune_{name.lower()}_top100.csv"
    if cache_path.exists():
        print(f"  Cache exists: {cache_path}")
        df = pd.read_csv(cache_path)
        print(f"  {len(df)} rows loaded from cache")
        return df

    qid = create_query(f"{name.lower()}_top100", sql)
    if not qid:
        save_sql_fallback(f"{name.lower()}_top100", sql)
        return None
    print(f"    Query ID: {qid}")

    eid = execute_query(qid)
    if not eid:
        save_sql_fallback(f"{name.lower()}_top100", sql)
        return None
    print(f"    Execution ID: {eid}")

    df = poll_and_fetch(eid)
    if df is None or len(df) == 0:
        print("    No data returned")
        save_sql_fallback(f"{name.lower()}_top100", sql)
        return None

    # Label known addresses
    df["label"] = df["addr"].map(known_labels).fillna("Unknown")
    df["total_volume"] = pd.to_numeric(df["total_volume"], errors="coerce")
    df["n_transfers"] = pd.to_numeric(df["n_transfers"], errors="coerce")

    # Sort by volume
    df = df.sort_values("total_volume", ascending=False).reset_index(drop=True)
    df.index.name = "rank"

    # Save
    df.to_csv(cache_path, index=False)
    print(f"    OK: {len(df)} addresses")

    # Summary
    labeled = df[df["label"] != "Unknown"]
    print(f"    Labeled: {len(labeled)}/{len(df)}")
    total_vol = df["total_volume"].sum()
    for _, row in labeled.iterrows():
        pct = row["total_volume"] / total_vol * 100 if total_vol > 0 else 0
        print(f"      {row['label']}: {row['addr'][:16]}... "
              f"vol=${row['total_volume']/1e6:,.0f}M ({pct:.1f}%)")

    # Show top unknowns for manual research
    unknowns = df[df["label"] == "Unknown"].head(10)
    if len(unknowns) > 0:
        print(f"\n    Top unlabeled addresses (research candidates):")
        for _, row in unknowns.iterrows():
            pct = row["total_volume"] / total_vol * 100 if total_vol > 0 else 0
            print(f"      {row['addr'][:24]}... "
                  f"vol=${row['total_volume']/1e6:,.0f}M ({pct:.1f}%)")

    return df


def main():
    if not DUNE_API_KEY:
        print("ERROR: Set DUNE_API_KEY in config/settings.py")
        sys.exit(1)

    print("=" * 60)
    print("ADDRESS DISCOVERY: Top-100 Stablecoin Addresses")
    print("=" * 60)

    results = {}

    # Solana discovery
    sol_df = run_discovery("Solana", SOLANA_TOP100_SQL, KNOWN_SOLANA_LABELS)
    if sol_df is not None:
        results["solana"] = {
            "total_addresses": len(sol_df),
            "labeled": int((sol_df["label"] != "Unknown").sum()),
            "top_labels": sol_df[sol_df["label"] != "Unknown"][["addr", "label", "total_volume"]].to_dict("records"),
        }

    # Tron discovery
    tron_df = run_discovery("Tron", TRON_TOP100_SQL, KNOWN_TRON_LABELS)
    if tron_df is not None:
        results["tron"] = {
            "total_addresses": len(tron_df),
            "labeled": int((tron_df["label"] != "Unknown").sum()),
            "top_labels": tron_df[tron_df["label"] != "Unknown"][["addr", "label", "total_volume"]].to_dict("records"),
        }

    save_json(results, "address_discovery_results.json")

    print("\n" + "=" * 60)
    print("DISCOVERY COMPLETE")
    for chain, data in results.items():
        print(f"  {chain}: {data['labeled']}/{data['total_addresses']} labeled")
    print("=" * 60)


if __name__ == "__main__":
    main()
