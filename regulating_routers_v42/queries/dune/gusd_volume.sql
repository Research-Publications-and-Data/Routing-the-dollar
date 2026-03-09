-- Gemini Gateway Profile: GUSD transfer volume through Gemini addresses
-- GUSD contract: 0x056Fd409E1d7A124BD7017459dFEa2F387b6d5Cd

SELECT
    date_trunc('month', evt_block_time) AS month,
    CASE
        WHEN "from" IN (0xd24400ae8BfEBb18cA49Be86258a3C749cf46853,
                        0x07Ee55aA48Bb72DcC6E9D78256648910De513eca) THEN 'from_gemini'
        WHEN "to" IN (0xd24400ae8BfEBb18cA49Be86258a3C749cf46853,
                      0x07Ee55aA48Bb72DcC6E9D78256648910De513eca) THEN 'to_gemini'
        ELSE 'other'
    END AS direction,
    COUNT(*) AS n_transfers,
    SUM(CAST(value AS DOUBLE)) / 1e2 AS volume_usd  -- GUSD has 2 decimals
FROM erc20_ethereum.evt_Transfer
WHERE contract_address = 0x056Fd409E1d7A124BD7017459dFEa2F387b6d5Cd
AND evt_block_time >= TIMESTAMP '2023-02-01'
AND evt_block_time < TIMESTAMP '2026-02-01'
GROUP BY 1, 2
ORDER BY 1
