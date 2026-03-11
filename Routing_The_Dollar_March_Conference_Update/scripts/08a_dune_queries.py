"""Task 8a: Execute Dune Analytics queries via API and save results.

Uses the Dune API v1 create-then-execute pattern:
1. POST /api/v1/query to create a saved query
2. POST /api/v1/query/{query_id}/execute to run it
3. GET /api/v1/execution/{execution_id}/status to poll
4. GET /api/v1/execution/{execution_id}/results to fetch rows
"""
import requests, pandas as pd, time, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import DUNE_API_KEY
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW

DUNE_API = "https://api.dune.com/api/v1"
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}

QUERIES = {
    "query_a_total_volume": {
        "description": "Total Ethereum USDC+USDT daily volume",
        "output": "dune_total_volume.csv",
        "sql": """
SELECT
    date_trunc('day', evt_block_time) AS day,
    CASE WHEN contract_address = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 THEN 'USDC'
         WHEN contract_address = 0xdAC17F958D2ee523a2206206994597C13D831ec7 THEN 'USDT' END AS token,
    COUNT(*) AS n_transfers,
    SUM(CAST(value AS DOUBLE)) / 1e6 AS volume_usd
FROM erc20_ethereum.evt_Transfer
WHERE contract_address IN (0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48, 0xdAC17F958D2ee523a2206206994597C13D831ec7)
AND evt_block_time >= TIMESTAMP '2023-02-01' AND evt_block_time < TIMESTAMP '2026-03-01'
GROUP BY 1, 2 ORDER BY 1
"""
    },
    "query_b_gateway_volume": {
        "description": "Volume through paper's 12 gateway addresses",
        "output": "dune_gateway_volume.csv",
        "sql": """
WITH gw AS (
    SELECT address, name, tier FROM (VALUES
        (0x55FE002aefF02F77364de339a1292923A15844B8, 'Circle Treasury', 1),
        (0xE25a329d385f77df5D4eD56265babe2b99A5436e, 'Paxos', 1),
        (0x503828976D22510aad0201ac7EC88293211D23Da, 'Coinbase', 1),
        (0xd24400ae8BfEBb18cA49Be86258a3C749cf46853, 'Gemini', 1),
        (0x5754284f345afc66a98fbB0a0Afe71e0F007B949, 'Tether Treasury', 2),
        (0x28C6c06298d514Db089934071355E5743bf21d60, 'Binance', 2),
        (0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2, 'Kraken', 2),
        (0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b, 'OKX', 2),
        (0xE592427A0AEce92De3Edee1F18E0157C05861564, 'Uniswap V3', 3),
        (0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7, 'Curve 3pool', 3),
        (0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2, 'Aave V3', 3),
        (0xd90e2f925DA726b50C4Ed8D0Fb90Ad053324F31b, 'Tornado Cash', 3)
    ) AS t(address, name, tier)
)
SELECT date_trunc('day', e.evt_block_time) AS day, g.name, g.tier,
    CASE WHEN e.contract_address = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 THEN 'USDC'
         WHEN e.contract_address = 0xdAC17F958D2ee523a2206206994597C13D831ec7 THEN 'USDT' END AS token,
    COUNT(*) AS n_transfers, SUM(CAST(e.value AS DOUBLE)) / 1e6 AS volume_usd
FROM erc20_ethereum.evt_Transfer e
INNER JOIN gw g ON (e."from" = g.address OR e."to" = g.address)
WHERE e.contract_address IN (0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48, 0xdAC17F958D2ee523a2206206994597C13D831ec7)
AND e.evt_block_time >= TIMESTAMP '2023-02-01' AND e.evt_block_time < TIMESTAMP '2026-03-01'
GROUP BY 1, 2, 3, 4 ORDER BY 1
"""
    },
    "query_c_top50_addresses": {
        "description": "Top 50 addresses by USDC+USDT volume",
        "output": "dune_top50_addresses.csv",
        "sql": """
WITH p AS (
    SELECT "from" AS addr, CAST(value AS DOUBLE)/1e6 AS vol FROM erc20_ethereum.evt_Transfer
    WHERE contract_address IN (0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48, 0xdAC17F958D2ee523a2206206994597C13D831ec7)
    AND evt_block_time >= TIMESTAMP '2023-02-01' AND evt_block_time < TIMESTAMP '2026-03-01'
    UNION ALL
    SELECT "to", CAST(value AS DOUBLE)/1e6 FROM erc20_ethereum.evt_Transfer
    WHERE contract_address IN (0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48, 0xdAC17F958D2ee523a2206206994597C13D831ec7)
    AND evt_block_time >= TIMESTAMP '2023-02-01' AND evt_block_time < TIMESTAMP '2026-03-01'
)
SELECT addr AS address, SUM(vol) AS total_volume_usd, COUNT(*) AS n_transfers
FROM p WHERE addr != 0x0000000000000000000000000000000000000000
GROUP BY 1 ORDER BY 2 DESC LIMIT 50
"""
    },
    "query_d_tron_volume": {
        "description": "Tron USDT daily volume",
        "output": "dune_tron_volume.csv",
        "sql": """
SELECT date_trunc('day', block_time) AS day, COUNT(*) AS n_transfers,
    SUM(amount) AS volume_usd
FROM tokens_tron.transfers
WHERE contract_address_varchar = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
AND block_time >= TIMESTAMP '2023-02-01'
GROUP BY 1 ORDER BY 1
"""
    },
    "query_e_solana_volume": {
        "description": "Solana USDC+USDT daily volume",
        "output": "dune_solana_volume.csv",
        "sql": """
SELECT date_trunc('day', block_time) AS day,
    CASE WHEN token_mint_address = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' THEN 'USDC'
         WHEN token_mint_address = 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB' THEN 'USDT' END AS token,
    COUNT(*) AS n_transfers, SUM(amount_display) AS volume_usd
FROM tokens_solana.transfers
WHERE token_mint_address IN ('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB')
AND block_time >= TIMESTAMP '2023-02-01'
GROUP BY 1, 2 ORDER BY 1
"""
    },
}


def create_query(name, sql):
    """Create a Dune query and return its query_id."""
    resp = requests.post(
        f"{DUNE_API}/query",
        headers=HEADERS,
        json={"name": f"fed_paper_{name}", "query_sql": sql.strip(), "is_private": True},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"    Create failed: {resp.status_code} {resp.text[:300]}")
        return None
    query_id = resp.json().get("query_id")
    print(f"    Created query ID: {query_id}")
    return query_id


def execute_query(query_id):
    """Execute a Dune query by ID and return execution_id."""
    resp = requests.post(
        f"{DUNE_API}/query/{query_id}/execute",
        headers=HEADERS,
        json={"performance": "medium"},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"    Execute failed: {resp.status_code} {resp.text[:300]}")
        return None
    execution_id = resp.json().get("execution_id")
    print(f"    Execution ID: {execution_id}")
    return execution_id


def poll_and_fetch(execution_id, output_file):
    """Poll for completion and fetch results."""
    for attempt in range(90):  # Max 15 minutes
        time.sleep(10)
        try:
            status_resp = requests.get(
                f"{DUNE_API}/execution/{execution_id}/status",
                headers=HEADERS,
                timeout=30,
            )
            if status_resp.status_code != 200:
                continue
            state = status_resp.json().get("state", "")
            if attempt % 3 == 0:  # Print every 30s
                print(f"    Poll {attempt + 1}: {state}")

            if state == "QUERY_STATE_COMPLETED":
                break
            elif state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"):
                error = status_resp.json().get("error", "unknown")
                print(f"    Query failed: {error}")
                return False
        except Exception as e:
            print(f"    Poll error: {e}")
    else:
        print("    Timed out")
        return False

    # Fetch results
    results_resp = requests.get(
        f"{DUNE_API}/execution/{execution_id}/results",
        headers=HEADERS,
        params={"limit": 500000},
        timeout=120,
    )
    if results_resp.status_code != 200:
        print(f"    Results failed: {results_resp.status_code}")
        return False

    result_data = results_resp.json().get("result", {})
    rows = result_data.get("rows", [])
    if not rows:
        print("    No rows returned")
        return False

    df = pd.DataFrame(rows)
    path = DATA_RAW / output_file
    df.to_csv(path, index=False)
    print(f"    Saved {len(df)} rows to {path}")
    return True


def run_query(name, sql, output_file):
    """Full pipeline: create -> execute -> poll -> fetch."""
    print(f"\n  [{name}]")
    query_id = create_query(name, sql)
    if not query_id:
        return False
    execution_id = execute_query(query_id)
    if not execution_id:
        return False
    return poll_and_fetch(execution_id, output_file)


def main():
    if not DUNE_API_KEY:
        print("ERROR: Set DUNE_API_KEY in config/settings.py")
        sys.exit(1)

    print("Dune Analytics Query Execution")
    print("=" * 50)

    results = {}
    for name, config in QUERIES.items():
        print(f"\n{'=' * 50}")
        print(f"  {config['description']}")
        try:
            ok = run_query(name, config["sql"], config["output"])
            results[name] = "OK" if ok else "FAILED"
        except Exception as e:
            print(f"    ERROR: {e}")
            results[name] = f"ERROR: {e}"

    print(f"\n{'=' * 50}")
    print("RESULTS:")
    for name, status in results.items():
        print(f"  {name}: {status}")

    # Run coverage ratio if queries A and B succeeded
    if results.get("query_a_total_volume") == "OK" and results.get("query_b_gateway_volume") == "OK":
        print("\nComputing gateway coverage ratio...")
        try:
            total = pd.read_csv(DATA_RAW / "dune_total_volume.csv")
            gateway = pd.read_csv(DATA_RAW / "dune_gateway_volume.csv")
            coverage = gateway["volume_usd"].sum() / total["volume_usd"].sum()
            print(f"  Gateway coverage ratio: {coverage:.1%}")
            print(f"  (12 addresses capture {coverage:.1%} of total Ethereum USDC+USDT volume)")
            from utils import save_json
            save_json({"coverage_ratio": round(coverage, 4),
                       "gateway_volume": float(gateway["volume_usd"].sum()),
                       "total_volume": float(total["volume_usd"].sum())}, "gateway_coverage.json")
        except Exception as e:
            print(f"  Coverage ratio error: {e}")


if __name__ == "__main__":
    main()
