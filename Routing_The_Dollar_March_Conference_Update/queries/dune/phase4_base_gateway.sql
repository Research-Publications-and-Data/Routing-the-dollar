
WITH gw AS (
    SELECT address, name, tier FROM (VALUES
        (0x3154Cf16ccdb4C6d922629664174b904d80F2C35, 'Coinbase (Base Bridge)', 1),
        (0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43, 'Aerodrome', 3)
    ) AS t(address, name, tier)
)
SELECT date_trunc('day', e.evt_block_time) AS day,
    g.name AS entity, g.tier,
    COUNT(*) AS n_transfers,
    SUM(CAST(e.value AS DOUBLE)) / 1e6 AS volume_usd
FROM erc20_base.evt_Transfer e
INNER JOIN gw g ON (e."from" = g.address OR e."to" = g.address)
WHERE e.contract_address IN (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913, 0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA)
AND e.evt_block_time >= TIMESTAMP '2023-02-01'
GROUP BY 1, 2, 3
ORDER BY 1
