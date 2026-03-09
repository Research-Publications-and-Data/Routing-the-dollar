-- gemini_verification.sql
-- Confirm Gemini address attribution: mislabeled vs real Gemini addresses
-- Expected: 0x21a31... (Binance 15/36) has ~$423B, real Gemini near $0

SELECT
    CASE
        WHEN addr = 0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549 THEN 'MISLABELED (Binance 15)'
        WHEN addr = 0xd24400ae8BfEBb18cA49Be86258a3C749cf46853 THEN 'Gemini Hot Wallet'
        WHEN addr = 0x07Ee55aA48Bb72DcC6E9D78256648910De513eca THEN 'Gemini 2'
    END AS label,
    SUM(CAST(value AS DOUBLE)) / 1e6 AS total_volume_usd,
    COUNT(*) AS n_transfers
FROM erc20_ethereum.evt_Transfer
CROSS JOIN UNNEST(ARRAY[
    0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549,
    0xd24400ae8BfEBb18cA49Be86258a3C749cf46853,
    0x07Ee55aA48Bb72DcC6E9D78256648910De513eca
]) AS t(addr)
WHERE ("from" = addr OR "to" = addr)
AND contract_address IN (
    0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
    0xdAC17F958D2ee523a2206206994597C13D831ec7
)
AND evt_block_time >= TIMESTAMP '2023-02-01'
AND evt_block_time < TIMESTAMP '2026-02-01'
GROUP BY 1
