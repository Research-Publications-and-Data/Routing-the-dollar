-- Internal Transfer Audit: Quantify intra-entity transfers for multi-address entities
-- Identifies transfers where BOTH from and to belong to the same entity

WITH gw AS (
    SELECT address, entity FROM (VALUES
        -- Coinbase (6 addresses)
        (0x503828976D22510aad0201ac7EC88293211D23Da, 'Coinbase'),
        (0xA9D1e08C7793af67e9d92fe308d5697FB81d3E43, 'Coinbase'),
        (0x71660c4005BA85c37ccec55d0C4493E66Fe775d3, 'Coinbase'),
        (0xddfAbCdc4D8FfC6d5beaf154f18B778f892A0740, 'Coinbase'),
        (0x3cD751E6b0078Be393132286c442345e68FF0aFf, 'Coinbase'),
        (0xb5d85CBf7cB3EE0D56b3bB207D5Fc4B82f43F511, 'Coinbase'),
        -- Binance (5 addresses)
        (0x28C6c06298d514Db089934071355E5743bf21d60, 'Binance'),
        (0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549, 'Binance'),
        (0xDFd5293D8e347dFe59E90eFd55b2956a1343963d, 'Binance'),
        (0xF977814e90dA44bFA03b6295A0616a897441aceC, 'Binance'),
        (0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8, 'Binance'),
        -- Kraken (5 addresses)
        (0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2, 'Kraken'),
        (0xDA9dfA130Df4dE4673b89022EE50ff26f6EA73Cf, 'Kraken'),
        (0x89e51fA8CA5D66cd220bAed62ED01e8951aa7c40, 'Kraken'),
        (0xae2D4617c862309A3d75A0fFB358c7a5009c673F, 'Kraken'),
        (0xC06f25517E906B7f9b4dec3c7889503bB00b3370, 'Kraken'),
        -- OKX (15 addresses)
        (0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b, 'OKX'),
        (0x236F9F97e0E62388479bf9E5BA4889e46B0273C3, 'OKX'),
        (0x5041ed759Dd4aFc3a72b8192C143F72f4724081A, 'OKX'),
        (0x7eb6c83AB7d8D9B8618c0ED973cbEF71d1921EF2, 'OKX'),
        (0x03ae1a796dfe0400439211133d065bda774b9d3e, 'OKX'),
        (0x2ce910fBba65B454bBaF6A18c952A70F3bcd8299, 'OKX'),
        (0x68841a1806fF291314946EeBd0CDa8B348E73d6d, 'OKX'),
        (0x3D55CCb2A943D88d39dd2e62dAf767c69fD0179f, 'OKX'),
        (0x9e4E147d103DEf9e98462884e7CE06385f8Ac540, 'OKX'),
        (0x5f8215EE653Cb7225c741c7aA8591468D1f158b8, 'OKX'),
        (0xEe1c6537e589a15a15f80961f5594c57bed936fB, 'OKX'),
        (0xC68C17e6eEc0fDe3605c595C9b98DE5C1a4CC3E4, 'OKX'),
        (0xfc99f58A8974a4bc36e60E2d490Bb8D72899ee9f, 'OKX'),
        (0x83bDf89CE9b2b587785a89603D2d451f05CF719b, 'OKX'),
        (0xb99cC7e10Fe0Acc68C50C7829F473d81e23249cc, 'OKX')
    ) AS t(address, entity)
)
SELECT
    gf.entity,
    CASE WHEN e.contract_address = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 THEN 'USDC'
         WHEN e.contract_address = 0xdAC17F958D2ee523a2206206994597C13D831ec7 THEN 'USDT' END AS token,
    COUNT(*) AS internal_transfers,
    SUM(CAST(e.value AS DOUBLE)) / 1e6 AS internal_volume_usd
FROM erc20_ethereum.evt_Transfer e
INNER JOIN gw gf ON e."from" = gf.address
INNER JOIN gw gt ON e."to" = gt.address
WHERE gf.entity = gt.entity  -- SAME entity on both sides
AND e.contract_address IN (
    0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
    0xdAC17F958D2ee523a2206206994597C13D831ec7
)
AND e.evt_block_time >= TIMESTAMP '2023-02-01'
AND e.evt_block_time < TIMESTAMP '2026-02-01'
GROUP BY 1, 2
ORDER BY 4 DESC
