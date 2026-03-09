-- Double-Counting Check: Gateway-to-gateway bilateral flow matrix
-- Quantifies transfers between any two monitored entities

WITH gw AS (
    SELECT address, entity, tier FROM (VALUES
        (0x55FE002aefF02F77364de339a1292923A15844B8, 'Circle', 1),
        (0x5B6122C109B78C6755486966148C1D70a50A47D7, 'Circle', 1),
        (0x0A59649758aa4d66E25f08Dd01271e891fe52199, 'Circle', 1),
        (0x503828976D22510aad0201ac7EC88293211D23Da, 'Coinbase', 1),
        (0xA9D1e08C7793af67e9d92fe308d5697FB81d3E43, 'Coinbase', 1),
        (0x71660c4005BA85c37ccec55d0C4493E66Fe775d3, 'Coinbase', 1),
        (0xddfAbCdc4D8FfC6d5beaf154f18B778f892A0740, 'Coinbase', 1),
        (0x3cD751E6b0078Be393132286c442345e68FF0aFf, 'Coinbase', 1),
        (0xb5d85CBf7cB3EE0D56b3bB207D5Fc4B82f43F511, 'Coinbase', 1),
        (0xE25a329d385f77df5D4eD56265babe2b99A5436e, 'Paxos', 1),
        (0x36819a5B9D1DBd8B1e04a19C30A10F8d2b9CEc3f, 'Paxos', 1),
        (0xd24400ae8BfEBb18cA49Be86258a3C749cf46853, 'Gemini', 1),
        (0x07Ee55aA48Bb72DcC6E9D78256648910De513eca, 'Gemini', 1),
        (0x0e7EB45C8F8DA3D62627b1B16e107bBf8BcD24e6, 'PayPal', 1),
        (0x5C985E89DDe482eFE97ea9f1950aD149Eb73829B, 'BitGo', 1),
        (0x5754284f345afc66a98fbB0a0Afe71e0F007B949, 'Tether', 2),
        (0xC6CDE7C39eB2f0F0095F41570af89eFC2C1Ea828, 'Tether', 2),
        (0x28C6c06298d514Db089934071355E5743bf21d60, 'Binance', 2),
        (0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549, 'Binance', 2),
        (0xDFd5293D8e347dFe59E90eFd55b2956a1343963d, 'Binance', 2),
        (0xF977814e90dA44bFA03b6295A0616a897441aceC, 'Binance', 2),
        (0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8, 'Binance', 2),
        (0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2, 'Kraken', 2),
        (0xDA9dfA130Df4dE4673b89022EE50ff26f6EA73Cf, 'Kraken', 2),
        (0x89e51fA8CA5D66cd220bAed62ED01e8951aa7c40, 'Kraken', 2),
        (0xae2D4617c862309A3d75A0fFB358c7a5009c673F, 'Kraken', 2),
        (0xC06f25517E906B7f9b4dec3c7889503bB00b3370, 'Kraken', 2),
        (0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b, 'OKX', 2),
        (0x236F9F97e0E62388479bf9E5BA4889e46B0273C3, 'OKX', 2),
        (0x5041ed759Dd4aFc3a72b8192C143F72f4724081A, 'OKX', 2),
        (0x7eb6c83AB7d8D9B8618c0ED973cbEF71d1921EF2, 'OKX', 2),
        (0x03ae1a796dfe0400439211133d065bda774b9d3e, 'OKX', 2),
        (0x2ce910fBba65B454bBaF6A18c952A70F3bcd8299, 'OKX', 2),
        (0x68841a1806fF291314946EeBd0CDa8B348E73d6d, 'OKX', 2),
        (0x3D55CCb2A943D88d39dd2e62dAf767c69fD0179f, 'OKX', 2),
        (0x9e4E147d103DEf9e98462884e7CE06385f8Ac540, 'OKX', 2),
        (0x5f8215EE653Cb7225c741c7aA8591468D1f158b8, 'OKX', 2),
        (0xEe1c6537e589a15a15f80961f5594c57bed936fB, 'OKX', 2),
        (0xC68C17e6eEc0fDe3605c595C9b98DE5C1a4CC3E4, 'OKX', 2),
        (0xfc99f58A8974a4bc36e60E2d490Bb8D72899ee9f, 'OKX', 2),
        (0x83bDf89CE9b2b587785a89603D2d451f05CF719b, 'OKX', 2),
        (0xb99cC7e10Fe0Acc68C50C7829F473d81e23249cc, 'OKX', 2),
        (0xf89d7b9c864f589bbF53a82105107622B35EaA40, 'Bybit', 2),
        (0x40B38765696e3d5d8d9d834D8AaD4bB6e418E489, 'Robinhood', 2),
        (0xE592427A0AEce92De3Edee1F18E0157C05861564, 'Uniswap V3', 3),
        (0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD, 'Uniswap Universal Router', 3),
        (0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7, 'Curve 3pool', 3),
        (0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2, 'Aave V3', 3),
        (0x1111111254EEB25477B68fb85Ed929f73A960582, '1inch', 3),
        (0xc3d688B66703497DAA19211EEdff47f25384cdc3, 'Compound V3', 3),
        (0xd90e2f925DA726b50C4Ed8D0Fb90Ad053324F31b, 'Tornado Cash', 3)
    ) AS t(address, entity, tier)
)
SELECT
    gf.entity AS from_entity,
    gf.tier AS from_tier,
    gt.entity AS to_entity,
    gt.tier AS to_tier,
    COUNT(*) AS n_transfers,
    SUM(CAST(e.value AS DOUBLE)) / 1e6 AS volume_usd
FROM erc20_ethereum.evt_Transfer e
INNER JOIN gw gf ON e."from" = gf.address
INNER JOIN gw gt ON e."to" = gt.address
WHERE gf.entity != gt.entity  -- DIFFERENT entities only (excludes internal)
AND e.contract_address IN (
    0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
    0xdAC17F958D2ee523a2206206994597C13D831ec7
)
AND e.evt_block_time >= TIMESTAMP '2023-02-01'
AND e.evt_block_time < TIMESTAMP '2026-02-01'
GROUP BY 1, 2, 3, 4
ORDER BY 6 DESC
