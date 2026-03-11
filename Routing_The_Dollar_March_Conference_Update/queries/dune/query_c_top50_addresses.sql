-- Query C: Top 50 addresses by USDC+USDT volume on Ethereum
-- Save output as: data/raw/dune_top50_addresses.csv
WITH p AS (
    SELECT "from" AS addr, CAST(value AS DOUBLE)/1e6 AS vol FROM erc20_ethereum.evt_Transfer
    WHERE contract_address IN (0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48, 0xdAC17F958D2ee523a2206206994597C13D831ec7)
    AND evt_block_time >= TIMESTAMP '2023-02-01' AND evt_block_time < TIMESTAMP '2026-02-01'
    UNION ALL
    SELECT "to", CAST(value AS DOUBLE)/1e6 FROM erc20_ethereum.evt_Transfer
    WHERE contract_address IN (0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48, 0xdAC17F958D2ee523a2206206994597C13D831ec7)
    AND evt_block_time >= TIMESTAMP '2023-02-01' AND evt_block_time < TIMESTAMP '2026-02-01'
)
SELECT addr AS address, SUM(vol) AS total_volume_usd, COUNT(*) AS n_transfers
FROM p WHERE addr != 0x0000000000000000000000000000000000000000
GROUP BY 1 ORDER BY 2 DESC LIMIT 50
