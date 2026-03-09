-- =============================================================================
-- EXHIBIT A: US→Mexico Corridor Stablecoin Gateway Transfers
-- =============================================================================
-- Purpose: Extract USDC/USDT transfers touching Mexico-anchored gateway clusters
-- Output:  Daily aggregates for corridor proxy analysis
-- Chains:  Ethereum (primary), Tron (secondary - separate query)
-- Window:  2023-02-01 to 2026-01-31
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PART 1: ETHEREUM TRANSFERS
-- -----------------------------------------------------------------------------

WITH stablecoin_contracts AS (
    SELECT * FROM (VALUES
        ('USDC', 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48, 6),
        ('USDT', 0xdAC17F958D2ee523a2206206994597C13D831ec7, 6)
    ) AS t(token_symbol, contract_address, decimals)
),

-- Gateway address clusters
-- Tier 1: Regulated / High-CLII (Mexico off-ramps)
-- Tier 2: Offshore CeFi (global venues serving MX users)
-- Tier 3: Non-custodial (DEX routers, bridges)

gateway_addresses AS (
    -- ===========================================
    -- BITSO (Tier 1, A_strict + B_broader)
    -- Primary Mexico crypto exchange / off-ramp
    -- Source: Dune labels + manual verification
    -- ===========================================
    SELECT address, 'Bitso' as gateway_name, 'tier1_high_clii' as tier, 'A_strict' as proxy_variant
    FROM (VALUES
        -- Known Bitso hot wallets (verify via etherscan labels / Dune labels.addresses)
        (0x5bdf85216ec1e38d6458c870992a69e38e03f7ef),  -- Bitso Hot Wallet 1
        (0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98),  -- Bitso Hot Wallet 2
        (0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be)   -- Bitso (unverified - check labels)
    ) AS t(address)
    
    UNION ALL
    
    -- Also include Bitso in B_broader
    SELECT address, 'Bitso', 'tier1_high_clii', 'B_broader'
    FROM (VALUES
        (0x5bdf85216ec1e38d6458c870992a69e38e03f7ef),
        (0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98),
        (0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be)
    ) AS t(address)
    
    UNION ALL
    
    -- ===========================================
    -- COINBASE (Tier 1, B_broader only)
    -- Used for churn filtering and Tier 1 robustness
    -- NOT a Mexico-specific off-ramp
    -- ===========================================
    SELECT address, 'Coinbase', 'tier1_high_clii', 'B_broader'
    FROM (VALUES
        (0x71660c4005ba85c37ccec55d0c4493e66fe775d3),  -- Coinbase 1
        (0x503828976d22510aad0201ac7ec88293211d23da),  -- Coinbase 2
        (0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740),  -- Coinbase 3
        (0x3cd751e6b0078be393132286c442345e5dc49699),  -- Coinbase 4
        (0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511),  -- Coinbase 5
        (0xeb2629a2734e272bcc07bda959863f316f4bd4cf),  -- Coinbase Commerce
        (0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43)   -- Coinbase 10
    ) AS t(address)
    
    UNION ALL
    
    -- ===========================================
    -- KRAKEN (Tier 1, B_broader only)
    -- ===========================================
    SELECT address, 'Kraken', 'tier1_high_clii', 'B_broader'
    FROM (VALUES
        (0x2910543af39aba0cd09dbb2d50200b3e800a63d2),  -- Kraken 1
        (0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13),  -- Kraken 2
        (0xe853c56864a2ebe4576a807d26fdc4a0ada51919),  -- Kraken 3
        (0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0)   -- Kraken 4
    ) AS t(address)
    
    UNION ALL
    
    -- ===========================================
    -- BINANCE (Tier 2, B_broader only)
    -- Offshore CeFi - may serve MX users
    -- ===========================================
    SELECT address, 'Binance', 'tier2_offshore_cefi', 'B_broader'
    FROM (VALUES
        (0x28c6c06298d514db089934071355e5743bf21d60),  -- Binance 14
        (0x21a31ee1afc51d94c2efccaa2092ad1028285549),  -- Binance 15
        (0xdfd5293d8e347dfe59e90efd55b2956a1343963d),  -- Binance 16
        (0x56eddb7aa87536c09ccc2793473599fd21a8b17f),  -- Binance 17
        (0x9696f59e4d72e237be84ffd425dcad154bf96976),  -- Binance 18
        (0x4976a4a02f38326660d17bf34b431dc6e2eb2327),  -- Binance US 1
        (0xf977814e90da44bfa03b6295a0616a897441acec)   -- Binance 8
    ) AS t(address)
    
    UNION ALL
    
    -- ===========================================
    -- OKX (Tier 2, B_broader only)
    -- ===========================================
    SELECT address, 'OKX', 'tier2_offshore_cefi', 'B_broader'
    FROM (VALUES
        (0x6cc5f688a315f3dc28a7781717a9a798a59fda7b),  -- OKX 1
        (0x236f9f97e0e62388479bf9e5ba4889e46b0273c3),  -- OKX 2
        (0xa7efae728d2936e78bda97dc267687568dd593f3)   -- OKX 3
    ) AS t(address)
    
    UNION ALL
    
    -- ===========================================
    -- UNISWAP ROUTER (Tier 3, B_broader only)
    -- Non-custodial DEX
    -- ===========================================
    SELECT address, 'Uniswap', 'tier3_noncustodial', 'B_broader'
    FROM (VALUES
        (0x7a250d5630b4cf539739df2c5dacb4c659f2488d),  -- Uniswap V2 Router
        (0xe592427a0aece92de3edee1f18e0157c05861564),  -- Uniswap V3 Router
        (0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45),  -- Uniswap V3 Router 2
        (0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b)   -- Uniswap Universal Router
    ) AS t(address)
),

-- Raw ERC-20 transfers for USDC/USDT
raw_transfers AS (
    SELECT
        DATE_TRUNC('day', evt_block_time) AS date_utc,
        t.token_symbol,
        'ethereum' AS chain,
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

-- Join transfers with gateway addresses
gateway_transfers AS (
    SELECT
        r.date_utc,
        r.token_symbol,
        r.chain,
        g.gateway_name,
        g.tier,
        g.proxy_variant,
        r.tx_hash,
        CASE 
            WHEN r.recipient = g.address THEN 'inflow'
            WHEN r.sender = g.address THEN 'outflow'
        END AS direction,
        r.amount_token,
        -- Price lookup: use daily average from prices.usd
        r.amount_token * COALESCE(p.price, 1.0) AS amount_usd
    FROM raw_transfers r
    INNER JOIN gateway_addresses g 
        ON r.sender = g.address OR r.recipient = g.address
    LEFT JOIN prices.usd_daily p
        ON p.contract_address = (
            CASE r.token_symbol 
                WHEN 'USDC' THEN 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
                WHEN 'USDT' THEN 0xdAC17F958D2ee523a2206206994597C13D831ec7
            END
        )
        AND p.day = r.date_utc
    WHERE (r.recipient = g.address OR r.sender = g.address)
),

-- Apply churn filter: exclude CEX-to-CEX transfers
-- (same tx touching two different labeled gateways)
cex_addresses AS (
    SELECT DISTINCT address 
    FROM gateway_addresses 
    WHERE tier IN ('tier1_high_clii', 'tier2_offshore_cefi')
),

churn_txs AS (
    SELECT DISTINCT tx_hash
    FROM raw_transfers r
    WHERE r.sender IN (SELECT address FROM cex_addresses)
      AND r.recipient IN (SELECT address FROM cex_addresses)
),

filtered_transfers AS (
    SELECT gt.*
    FROM gateway_transfers gt
    WHERE gt.tx_hash NOT IN (SELECT tx_hash FROM churn_txs)
),

-- Aggregate daily by token, gateway, direction, proxy variant
daily_gateway_aggregates AS (
    SELECT
        date_utc,
        token_symbol AS token,
        chain,
        gateway_name,
        tier,
        proxy_variant,
        direction,
        COUNT(*) AS tx_count,
        SUM(amount_usd) AS volume_usd,
        APPROX_PERCENTILE(amount_usd, 0.5) AS median_transfer_usd
    FROM filtered_transfers
    GROUP BY 1, 2, 3, 4, 5, 6, 7
)

-- Final output: one row per date/token/chain/gateway/proxy/direction
SELECT
    date_utc,
    token,
    chain,
    gateway_name,
    tier,
    proxy_variant,
    direction,
    tx_count,
    volume_usd,
    median_transfer_usd
FROM daily_gateway_aggregates
ORDER BY date_utc, proxy_variant, gateway_name, direction;
