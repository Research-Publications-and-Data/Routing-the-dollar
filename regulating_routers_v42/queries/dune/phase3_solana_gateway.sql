
SELECT
    date_trunc('day', block_time) AS day,
    COALESCE(
        CASE WHEN from_owner = 'DcgJMCdZZQFMZ3moAjyWMGchBMze2JZVBZ7A5bAWRgji' THEN 'Circle'
        WHEN from_owner = 'H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS' THEN 'Coinbase'
        WHEN from_owner = 'Q6XprfkF8RQQKoQVG33xT88H7wi8Uk1B1CC7YAs69Gi' THEN 'Tether'
        WHEN from_owner = '5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9' THEN 'Binance'
        WHEN from_owner = 'FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiWB5o' THEN 'Kraken'
        WHEN from_owner = '5VCwKtCXgCDuQosQDbo8VKUvTen5tYtEqpNqkzfbqME2' THEN 'OKX'
        WHEN from_owner = 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4' THEN 'Jupiter'
        WHEN from_owner = '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8' THEN 'Raydium'
        WHEN from_owner = 'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc' THEN 'Orca' ELSE NULL END,
        CASE WHEN to_owner = 'DcgJMCdZZQFMZ3moAjyWMGchBMze2JZVBZ7A5bAWRgji' THEN 'Circle'
        WHEN to_owner = 'H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS' THEN 'Coinbase'
        WHEN to_owner = 'Q6XprfkF8RQQKoQVG33xT88H7wi8Uk1B1CC7YAs69Gi' THEN 'Tether'
        WHEN to_owner = '5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9' THEN 'Binance'
        WHEN to_owner = 'FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiWB5o' THEN 'Kraken'
        WHEN to_owner = '5VCwKtCXgCDuQosQDbo8VKUvTen5tYtEqpNqkzfbqME2' THEN 'OKX'
        WHEN to_owner = 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4' THEN 'Jupiter'
        WHEN to_owner = '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8' THEN 'Raydium'
        WHEN to_owner = 'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc' THEN 'Orca' ELSE NULL END
    ) AS entity,
    CASE COALESCE(
        CASE WHEN from_owner = 'DcgJMCdZZQFMZ3moAjyWMGchBMze2JZVBZ7A5bAWRgji' THEN 'Circle'
        WHEN from_owner = 'H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS' THEN 'Coinbase'
        WHEN from_owner = 'Q6XprfkF8RQQKoQVG33xT88H7wi8Uk1B1CC7YAs69Gi' THEN 'Tether'
        WHEN from_owner = '5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9' THEN 'Binance'
        WHEN from_owner = 'FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiWB5o' THEN 'Kraken'
        WHEN from_owner = '5VCwKtCXgCDuQosQDbo8VKUvTen5tYtEqpNqkzfbqME2' THEN 'OKX'
        WHEN from_owner = 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4' THEN 'Jupiter'
        WHEN from_owner = '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8' THEN 'Raydium'
        WHEN from_owner = 'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc' THEN 'Orca' ELSE NULL END,
        CASE WHEN to_owner = 'DcgJMCdZZQFMZ3moAjyWMGchBMze2JZVBZ7A5bAWRgji' THEN 'Circle'
        WHEN to_owner = 'H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS' THEN 'Coinbase'
        WHEN to_owner = 'Q6XprfkF8RQQKoQVG33xT88H7wi8Uk1B1CC7YAs69Gi' THEN 'Tether'
        WHEN to_owner = '5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9' THEN 'Binance'
        WHEN to_owner = 'FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiWB5o' THEN 'Kraken'
        WHEN to_owner = '5VCwKtCXgCDuQosQDbo8VKUvTen5tYtEqpNqkzfbqME2' THEN 'OKX'
        WHEN to_owner = 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4' THEN 'Jupiter'
        WHEN to_owner = '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8' THEN 'Raydium'
        WHEN to_owner = 'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc' THEN 'Orca' ELSE NULL END
    )
        WHEN 'Circle' THEN 1
        WHEN 'Coinbase' THEN 1
        WHEN 'Tether' THEN 2
        WHEN 'Binance' THEN 2
        WHEN 'Kraken' THEN 2
        WHEN 'OKX' THEN 2
        WHEN 'Jupiter' THEN 3
        WHEN 'Raydium' THEN 3
        WHEN 'Orca' THEN 3
    END AS tier,
    CASE
        WHEN token_mint_address = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' THEN 'USDC'
        WHEN token_mint_address = 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB' THEN 'USDT'
    END AS token,
    COUNT(*) AS n_transfers,
    SUM(amount) AS volume_usd
FROM tokens_solana.transfers
WHERE token_mint_address IN (
    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
    'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'
)
AND block_time >= TIMESTAMP '2023-02-01'
AND (from_owner IN ('DcgJMCdZZQFMZ3moAjyWMGchBMze2JZVBZ7A5bAWRgji', 'H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS', 'Q6XprfkF8RQQKoQVG33xT88H7wi8Uk1B1CC7YAs69Gi', '5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9', 'FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiWB5o', '5VCwKtCXgCDuQosQDbo8VKUvTen5tYtEqpNqkzfbqME2', 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4', '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8', 'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc') OR to_owner IN ('DcgJMCdZZQFMZ3moAjyWMGchBMze2JZVBZ7A5bAWRgji', 'H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS', 'Q6XprfkF8RQQKoQVG33xT88H7wi8Uk1B1CC7YAs69Gi', '5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9', 'FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiWB5o', '5VCwKtCXgCDuQosQDbo8VKUvTen5tYtEqpNqkzfbqME2', 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4', '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8', 'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc'))
GROUP BY 1, 2, 3, 4
ORDER BY 1
