-- paxos_verification.sql
-- Verify 0x5f65f7b6... attribution (holds GUSD - Gemini Dollar)
-- Check Dune labels for this address

SELECT
    l.name AS label_name,
    l.label_type,
    l.address
FROM labels.addresses l
WHERE l.address = 0x5f65f7b609678448494De4C87521CdF6cEf1e932
AND l.blockchain = 'ethereum'
