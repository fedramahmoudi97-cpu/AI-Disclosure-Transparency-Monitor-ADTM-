-- This script defines the database structure for the ADTM project.

-- Drop tables if they already exist to ensure a clean setup.
DROP TABLE IF EXISTS filings;
DROP TABLE IF EXISTS scores;
DROP TABLE IF EXISTS counts;
DROP TABLE IF EXISTS snippets;
DROP TABLE IF EXISTS terms;

-- Table to store metadata about each downloaded filing.
CREATE TABLE filings (
    filing_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Added AUTOINCREMENT for clarity
    cik TEXT NOT NULL,
    ticker TEXT NOT NULL,
    form_type TEXT NOT NULL,
    filing_date DATE NOT NULL,
    file_path TEXT UNIQUE NOT NULL,
    word_count INTEGER -- <<<<<< ADD THIS LINE
);

-- Table to store the calculated scores for each filing.
CREATE TABLE scores (
    filing_id INTEGER PRIMARY KEY,
    T_score REAL,
    R_score REAL,
    A_score REAL,
    RAI_score REAL,
    FOREIGN KEY (filing_id) REFERENCES filings (filing_id)
);

-- Table to define all the terms we are searching for and their categories.
-- This is a "dimension table".
CREATE TABLE terms (
    term_id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL -- 'usage', 'governance', or 'action'
);

-- Table to store the frequency of each term found in each section of a filing.
-- This is a "fact table" that links filings and terms.
CREATE TABLE counts (
    count_id INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id INTEGER NOT NULL,
    term_id INTEGER NOT NULL,
    section TEXT,
    frequency INTEGER NOT NULL,
    FOREIGN KEY (filing_id) REFERENCES filings (filing_id),
    FOREIGN KEY (term_id) REFERENCES terms (term_id)
);

-- Table to store contextual snippets for each mention.
-- This provides the "evidence" for our scores.
CREATE TABLE snippets (
    snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id INTEGER NOT NULL,
    term_id INTEGER NOT NULL,
    context TEXT NOT NULL,
    FOREIGN KEY (filing_id) REFERENCES filings (filing_id),
    FOREIGN KEY (term_id) REFERENCES terms (term_id)
);

-- Create indexes to speed up common queries.
CREATE INDEX idx_filings_ticker_date ON filings (ticker, filing_date);
CREATE INDEX idx_counts_filing_id ON counts (filing_id);
CREATE INDEX idx_snippets_filing_id ON snippets (filing_id);