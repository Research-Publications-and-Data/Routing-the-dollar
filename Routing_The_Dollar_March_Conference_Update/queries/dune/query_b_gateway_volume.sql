-- Query B: Volume through paper's 12 gateway addresses
-- Save output as: data/raw/dune_gateway_volume.csv
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
AND e.evt_block_time >= TIMESTAMP '2023-02-01' AND e.evt_block_time < TIMESTAMP '2026-02-01'
GROUP BY 1, 2, 3, 4 ORDER BY 1
