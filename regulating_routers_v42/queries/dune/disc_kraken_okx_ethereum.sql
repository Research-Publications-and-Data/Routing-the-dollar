
-- Discover labeled Kraken/OKX addresses with USDC+USDT volume
WITH exchange_labels AS (
    SELECT DISTINCT address, name, label_type
    FROM labels.addresses
    WHERE blockchain = 'ethereum'
    AND (name ILIKE '%kraken%' OR name ILIKE '%okx%' OR name ILIKE '%okex%')
),
addr_volume AS (
    SELECT
        addr,
        SUM(vol) AS total_volume_usd,
        SUM(cnt) AS n_transfers
    FROM (
        SELECT "from" AS addr, SUM(CAST(value AS DOUBLE) / 1e6) AS vol, COUNT(*) AS cnt
        FROM erc20_ethereum.evt_Transfer
        WHERE contract_address IN (
            0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48,
            0xdac17f958d2ee523a2206206994597c13d831ec7
        )
        AND evt_block_time >= TIMESTAMP '2023-02-01'
        AND evt_block_time < TIMESTAMP '2026-02-01'
        GROUP BY 1
        UNION ALL
        SELECT "to", SUM(CAST(value AS DOUBLE) / 1e6), COUNT(*)
        FROM erc20_ethereum.evt_Transfer
        WHERE contract_address IN (
            0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48,
            0xdac17f958d2ee523a2206206994597c13d831ec7
        )
        AND evt_block_time >= TIMESTAMP '2023-02-01'
        AND evt_block_time < TIMESTAMP '2026-02-01'
        GROUP BY 1
    ) sub
    GROUP BY 1
    HAVING SUM(vol) > 1e8  -- >$100M
)
SELECT
    e.name AS label,
    CAST(a.addr AS VARCHAR) AS address,
    a.total_volume_usd,
    a.n_transfers,
    e.label_type
FROM addr_volume a
JOIN exchange_labels e ON a.addr = e.address
ORDER BY a.total_volume_usd DESC
