select * from filings limit 10;
-- find the filings with the highest RAI SCORS
SELECT
    f.ticker,
    f.filing_date,
    s.RAI_score,
    s.T_score,
    s.R_score,
    s.A_score
FROM scores s
JOIN filings f ON s.filing_id = f.filing_id
ORDER BY s.RAI_score DESC
LIMIT 15;

--Calculate the Average RAI score for each company
SELECT
    f.ticker,
    COUNT(f.filing_id) as number_of_filings,
    AVG(s.RAI_score) as average_rai_score,
    AVG(s.T_score) as average_transparency,
    AVG(s.R_score) as average_risk,
    AVG(s.A_score) as average_actionability
FROM scores s
JOIN filings f ON s.filing_id = f.filing_id
GROUP BY f.ticker
ORDER BY average_rai_score DESC;

-- What are the most frequently mentioned action terms (governance cotrols in all company)
SELECT
    t.term,
    SUM(c.frequency) as total_mentions
FROM counts c
JOIN terms t ON c.term_id = t.term_id
WHERE t.category = 'action'
GROUP BY t.term
ORDER BY total_mentions DESC
LIMIT 10;

-- sow a result for specific high scoring filings
SELECT
    t.term,
    sn.context
FROM snippets sn
JOIN terms t ON sn.term_id = t.term_id
WHERE sn.filing_id = 3; -- Replace number with a real filing_id from your data (any number between 1-10)

