WITH gateway_addresses AS (
    SELECT address, name, tier FROM (VALUES
        (0x55fe002aeff02f77364de339a1292923a15844b8, 'Circle', 1),
        (0x5b6122c109b78c6755486966148c1d70a50a47d7, 'Circle', 1),
        (0x0a59649758aa4d66e25f08dd01271e891fe52199, 'Circle', 1),
        (0x503828976d22510aad0201ac7ec88293211d23da, 'Coinbase', 1),
        (0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43, 'Coinbase', 1),
        (0x71660c4005ba85c37ccec55d0c4493e66fe775d3, 'Coinbase', 1),
        (0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740, 'Coinbase', 1),
        (0x3cd751e6b0078be393132286c442345e68ff0aff, 'Coinbase', 1),
        (0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511, 'Coinbase', 1),
        (0xe25a329d385f77df5d4ed56265babe2b99a5436e, 'Paxos', 1),
        (0x36819a5b9d1dbd8b1e04a19c30a10f8d2b9cec3f, 'Paxos', 1),
        (0xd24400ae8bfebb18ca49be86258a3c749cf46853, 'Gemini', 1),
        (0x07ee55aa48bb72dcc6e9d78256648910de513eca, 'Gemini', 1),
        (0x0e7eb45c8f8da3d62627b1b16e107bbf8bcd24e6, 'PayPal', 1),
        (0x5c985e89dde482efe97ea9f1950ad149eb73829b, 'BitGo', 1),
        (0x5754284f345afc66a98fbb0a0afe71e0f007b949, 'Tether', 2),
        (0xc6cde7c39eb2f0f0095f41570af89efc2c1ea828, 'Tether', 2),
        (0x28c6c06298d514db089934071355e5743bf21d60, 'Binance', 2),
        (0x21a31ee1afc51d94c2efccaa2092ad1028285549, 'Binance', 2),
        (0xdfd5293d8e347dfe59e90efd55b2956a1343963d, 'Binance', 2),
        (0xf977814e90da44bfa03b6295a0616a897441acec, 'Binance', 2),
        (0xbe0eb53f46cd790cd13851d5eff43d12404d33e8, 'Binance', 2),
        (0x2910543af39aba0cd09dbb2d50200b3e800a63d2, 'Kraken', 2),
        (0xda9dfa130df4de4673b89022ee50ff26f6ea73cf, 'Kraken', 2),
        (0x89e51fa8ca5d66cd220baed62ed01e8951aa7c40, 'Kraken', 2),
        (0xae2d4617c862309a3d75a0ffb358c7a5009c673f, 'Kraken', 2),
        (0xc06f25517e906b7f9b4dec3c7889503bb00b3370, 'Kraken', 2),
        (0x6cc5f688a315f3dc28a7781717a9a798a59fda7b, 'OKX', 2),
        (0x236f9f97e0e62388479bf9e5ba4889e46b0273c3, 'OKX', 2),
        (0x5041ed759dd4afc3a72b8192c143f72f4724081a, 'OKX', 2),
        (0x7eb6c83ab7d8d9b8618c0ed973cbef71d1921ef2, 'OKX', 2),
        (0x03ae1a796dfe0400439211133d065bda774b9d3e, 'OKX', 2),
        (0x2ce910fbba65b454bbaf6a18c952a70f3bcd8299, 'OKX', 2),
        (0x68841a1806ff291314946eebd0cda8b348e73d6d, 'OKX', 2),
        (0x3d55ccb2a943d88d39dd2e62daf767c69fd0179f, 'OKX', 2),
        (0x9e4e147d103def9e98462884e7ce06385f8ac540, 'OKX', 2),
        (0x5f8215ee653cb7225c741c7aa8591468d1f158b8, 'OKX', 2),
        (0xee1c6537e589a15a15f80961f5594c57bed936fb, 'OKX', 2),
        (0xc68c17e6eec0fde3605c595c9b98de5c1a4cc3e4, 'OKX', 2),
        (0xfc99f58a8974a4bc36e60e2d490bb8d72899ee9f, 'OKX', 2),
        (0x83bdf89ce9b2b587785a89603d2d451f05cf719b, 'OKX', 2),
        (0xb99cc7e10fe0acc68c50c7829f473d81e23249cc, 'OKX', 2),
        (0xf89d7b9c864f589bbf53a82105107622b35eaa40, 'Bybit', 2),
        (0x40b38765696e3d5d8d9d834d8aad4bb6e418e489, 'Robinhood', 2),
        (0xe592427a0aece92de3edee1f18e0157c05861564, 'Uniswap V3', 3),
        (0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad, 'Uniswap Universal Router', 3),
        (0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7, 'Curve 3pool', 3),
        (0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2, 'Aave V3', 3),
        (0x1111111254eeb25477b68fb85ed929f73a960582, '1inch', 3),
        (0xc3d688b66703497daa19211eedff47f25384cdc3, 'Compound V3', 3),
        (0xd90e2f925da726b50c4ed8d0fb90ad053324f31b, 'Tornado Cash', 3)
    ) AS t(address, name, tier)
)
, daily_vol AS (
    SELECT
        date_trunc('day', e.evt_block_time) AS day,
        g.name AS gateway,
        g.tier,
        SUM(CAST(e.value AS DOUBLE)) / 1e6 AS volume_usd
    FROM erc20_ethereum.evt_Transfer e
    INNER JOIN gateway_addresses g ON (e."from" = g.address OR e."to" = g.address)
    WHERE e.contract_address IN (
        0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
        0xdAC17F958D2ee523a2206206994597C13D831ec7
    )
    AND e.evt_block_time >= TIMESTAMP '2023-02-01'
    AND e.evt_block_time < TIMESTAMP '2026-02-01'
    GROUP BY 1, 2, 3
)
, daily_total AS (
    SELECT day, SUM(volume_usd) AS total_vol FROM daily_vol GROUP BY 1
)
SELECT
    d.day AS date,
    d.gateway,
    d.tier,
    d.volume_usd,
    d.volume_usd / NULLIF(t.total_vol, 0) * 100 AS share_pct,
    POWER(d.volume_usd / NULLIF(t.total_vol, 0) * 100, 2) AS hhi_component
FROM daily_vol d
JOIN daily_total t ON d.day = t.day
ORDER BY d.day, d.tier, d.gateway
