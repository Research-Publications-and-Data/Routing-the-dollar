-- =============================================================================
-- EXHIBIT C: Gateway Daily Volumes for Concentration Analysis
-- =============================================================================
-- Purpose: Per-gateway daily volumes to compute HHI, tier shares, top-N
-- Output:  Daily volume by gateway for routing concentration analysis
-- Window:  2023-02-01 to 2026-01-31
-- =============================================================================

WITH stablecoin_contracts AS (
    SELECT * FROM (VALUES
        ('USDC', 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48, 6),
        ('USDT', 0xdAC17F958D2ee523a2206206994597C13D831ec7, 6)
    ) AS t(token_symbol, contract_address, decimals)
),

-- Comprehensive gateway list with CLII scores
gateway_master AS (
    -- Bitso (Tier 1, CLII: 7/8)
    SELECT address, 'Bitso' as gateway_name, 'tier1_high_clii' as tier, 7 as clii_score
    FROM (VALUES
        (0x5bdf85216ec1e38d6458c870992a69e38e03f7ef),
        (0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98),
        (0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be)
    ) AS t(address)
    
    UNION ALL
    
    -- Coinbase (Tier 1, CLII: 8/8)
    SELECT address, 'Coinbase', 'tier1_high_clii', 8
    FROM (VALUES
        (0x71660c4005ba85c37ccec55d0c4493e66fe775d3),
        (0x503828976d22510aad0201ac7ec88293211d23da),
        (0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740),
        (0x3cd751e6b0078be393132286c442345e5dc49699),
        (0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511),
        (0xeb2629a2734e272bcc07bda959863f316f4bd4cf),
        (0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43)
    ) AS t(address)
    
    UNION ALL
    
    -- Kraken (Tier 1, CLII: 7/8)
    SELECT address, 'Kraken', 'tier1_high_clii', 7
    FROM (VALUES
        (0x2910543af39aba0cd09dbb2d50200b3e800a63d2),
        (0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13),
        (0xe853c56864a2ebe4576a807d26fdc4a0ada51919),
        (0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0)
    ) AS t(address)
    
    UNION ALL
    
    -- Binance (Tier 2, CLII: 4/8)
    SELECT address, 'Binance', 'tier2_offshore_cefi', 4
    FROM (VALUES
        (0x28c6c06298d514db089934071355e5743bf21d60),
        (0x21a31ee1afc51d94c2efccaa2092ad1028285549),
        (0xdfd5293d8e347dfe59e90efd55b2956a1343963d),
        (0x56eddb7aa87536c09ccc2793473599fd21a8b17f),
        (0x9696f59e4d72e237be84ffd425dcad154bf96976),
        (0x4976a4a02f38326660d17bf34b431dc6e2eb2327),
        (0xf977814e90da44bfa03b6295a0616a897441acec)
    ) AS t(address)
    
    UNION ALL
    
    -- OKX (Tier 2, CLII: 4/8)
    SELECT address, 'OKX', 'tier2_offshore_cefi', 4
    FROM (VALUES
        (0x6cc5f688a315f3dc28a7781717a9a798a59fda7b),
        (0x236f9f97e0e62388479bf9e5ba4889e46b0273c3),
        (0xa7efae728d2936e78bda97dc267687568dd593f3)
    ) AS t(address)
    
    UNION ALL
    
    -- Huobi/HTX (Tier 2, CLII: 3/8)
    SELECT address, 'Huobi', 'tier2_offshore_cefi', 3
    FROM (VALUES
        (0x5401dbf7da53e1c9dbf484e3d69505815f2f5e6e),
        (0x1062a747393198f70f71ec65a582423dba7e5ab3),
        (0xab5c66752a9e8167967685f1450532fb96d5d24f)
    ) AS t(address)
    
    UNION ALL
    
    -- Uniswap (Tier 3, CLII: 1/8)
    SELECT address, 'Uniswap', 'tier3_noncustodial', 1
    FROM (VALUES
        (0x7a250d5630b4cf539739df2c5dacb4c659f2488d),
        (0xe592427a0aece92de3edee1f18e0157c05861564),
        (0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45),
        (0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b)
    ) AS t(address)
    
    UNION ALL
    
    -- 1inch (Tier 3, CLII: 1/8)
    SELECT address, '1inch', 'tier3_noncustodial', 1
    FROM (VALUES
        (0x1111111254fb6c44bac0bed2854e76f90643097d),
        (0x1111111254eeb25477b68fb85ed929f73a960582)
    ) AS t(address)
),

-- Raw transfers
raw_transfers AS (
    SELECT
        DATE_TRUNC('day', evt_block_time) AS date_utc,
        t.token_symbol,
        tr."from" AS sender,
        tr."to" AS recipient,
        tr.evt_tx_hash AS tx_hash,
        CAST(tr.value AS DOUBLE) / POWER(10, t.decimals) AS amount_token
    FROM erc20_ethereum.evt_Transfer tr
    INNER JOIN stablecoin_contracts t 
        ON tr.contract_address = t.contract_address
    WHERE tr.evt_block_time >= TIMESTAMP '2023-02-01'
      AND tr.evt_block_time < TIMESTAMP '2026-02-01'
      AND tr.value > 0
),

-- Gateway transfers (both directions combined for volume)
gateway_volume AS (
    SELECT
        r.date_utc,
        g.gateway_name,
        g.tier,
        g.clii_score,
        r.tx_hash,
        r.amount_token * COALESCE(p.price, 1.0) AS amount_usd
    FROM raw_transfers r
    INNER JOIN gateway_master g 
        ON r.sender = g.address OR r.recipient = g.address
    LEFT JOIN prices.usd_daily p
        ON p.contract_address = (
            CASE r.token_symbol 
                WHEN 'USDC' THEN 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
                WHEN 'USDT' THEN 0xdAC17F958D2ee523a2206206994597C13D831ec7
            END
        )
        AND p.day = r.date_utc
),

-- Daily aggregates per gateway
daily_gateway_volume AS (
    SELECT
        date_utc,
        gateway_name,
        tier,
        clii_score,
        COUNT(DISTINCT tx_hash) AS tx_count,
        SUM(amount_usd) AS volume_usd
    FROM gateway_volume
    GROUP BY 1, 2, 3, 4
),

-- Daily totals for share calculation
daily_totals AS (
    SELECT
        date_utc,
        SUM(volume_usd) AS total_volume_usd
    FROM daily_gateway_volume
    GROUP BY 1
)

-- Final output with shares
SELECT
    g.date_utc,
    g.gateway_name,
    g.tier,
    g.clii_score,
    g.tx_count,
    g.volume_usd,
    g.volume_usd / NULLIF(t.total_volume_usd, 0) AS volume_share,
    t.total_volume_usd AS daily_total_volume_usd
FROM daily_gateway_volume g
LEFT JOIN daily_totals t ON g.date_utc = t.date_utc
ORDER BY g.date_utc, g.volume_usd DESC;
