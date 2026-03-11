-- Kraken/OKX discovered addresses: monthly USDC+USDT volume (3yr)
WITH new_addrs AS (
    SELECT address, entity FROM (VALUES
        (0x89e51fa8ca5d66cd220baed62ed01e8951aa7c40, 'Kraken'),
        (0xae2d4617c862309a3d75a0ffb358c7a5009c673f, 'Kraken'),
        (0xc06f25517e906b7f9b4dec3c7889503bb00b3370, 'Kraken'),
        (0x5041ed759dd4afc3a72b8192c143f72f4724081a, 'OKX'),
        (0x7eb6c83ab7d8d9b8618c0ed973cbef71d1921ef2, 'OKX'),
        (0x03ae1a796dfe0400439211133d065bda774b9d3e, 'OKX'),
        (0x2ce910fbba65b454bbaf6a18c952a70f3bcd8299, 'OKX'),
        (0x68841a1806ff291314946eebd0cda8b348e73d6d, 'OKX'),
        (0x3d55ccb2a943d88d39dd2e62daf767c69fd0179f, 'OKX'),
        (0x9e4e147d103def9e98462884e7ce06385f8ac540, 'OKX'),
        (0x5f8215ee653cb7225c741c7aa8591468d1f158b8, 'OKX'),
        (0xee1c6537e589a15a15f80961f5594c57bed936fb, 'OKX'),
        (0xc68c17e6eec0fde3605c595c9b98de5c1a4cc3e4, 'OKX'),
        (0xfc99f58a8974a4bc36e60e2d490bb8d72899ee9f, 'OKX'),
        (0x83bdf89ce9b2b587785a89603d2d451f05cf719b, 'OKX'),
        (0xb99cc7e10fe0acc68c50c7829f473d81e23249cc, 'OKX')
    ) AS t(address, entity)
)
SELECT
    n.entity,
    date_trunc('month', e.evt_block_time) AS month,
    COUNT(*) AS n_transfers,
    CASE WHEN e.contract_address = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 THEN 'USDC'
         WHEN e.contract_address = 0xdAC17F958D2ee523a2206206994597C13D831ec7 THEN 'USDT'
    END AS token,
    SUM(CAST(e.value AS DOUBLE)) / 1e6 AS volume_usd
FROM erc20_ethereum.evt_Transfer e
INNER JOIN new_addrs n ON (e."from" = n.address OR e."to" = n.address)
WHERE e.contract_address IN (
    0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
    0xdAC17F958D2ee523a2206206994597C13D831ec7
)
AND e.evt_block_time >= TIMESTAMP '2023-02-01'
AND e.evt_block_time < TIMESTAMP '2026-02-01'
GROUP BY 1, 2, 4
ORDER BY 1, 2, 4