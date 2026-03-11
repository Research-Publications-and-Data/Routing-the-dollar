
SELECT
    date_trunc('day', evt_block_time) AS day,
    CASE WHEN contract_address = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 THEN 'USDC'
         WHEN contract_address = 0xdAC17F958D2ee523a2206206994597C13D831ec7 THEN 'USDT' END AS token,
    COUNT(*) AS n_transfers,
    SUM(CAST(value AS DOUBLE)) / 1e6 AS volume_usd
FROM erc20_ethereum.evt_Transfer
WHERE contract_address IN (
    0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
    0xdAC17F958D2ee523a2206206994597C13D831ec7
)
AND evt_block_time >= TIMESTAMP '2023-02-01'
AND evt_block_time < TIMESTAMP '2026-02-01'
GROUP BY 1, 2
ORDER BY 1
