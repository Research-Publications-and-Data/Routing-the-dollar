-- gemini_cold_wallet.sql
-- Check USDC/USDT activity for Gemini Cold Wallet (0x61edcdf5...)
-- Etherscan shows $1.1B ETH but need to check stablecoin activity

SELECT
    COUNT(*) AS n_transfers,
    SUM(CAST(value AS DOUBLE)) / 1e6 AS total_volume_usd,
    CASE WHEN contract_address = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 THEN 'USDC'
         WHEN contract_address = 0xdAC17F958D2ee523a2206206994597C13D831ec7 THEN 'USDT' END AS token
FROM erc20_ethereum.evt_Transfer
WHERE ("from" = 0x61edcdf5bb737adffe5043706e7c5bb1f1a56eea
    OR "to" = 0x61edcdf5bb737adffe5043706e7c5bb1f1a56eea)
AND contract_address IN (
    0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
    0xdAC17F958D2ee523a2206206994597C13D831ec7
)
AND evt_block_time >= TIMESTAMP '2023-02-01'
GROUP BY 3
