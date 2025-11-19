import os
import pandas as pd
import yaml
import regex as re
from tqdm import tqdm
import sqlite3
from utils_text import extract_text_from_html, parse_sections

# --- 1. CONFIGURATION & CONSTANTS ---
import os
import sys

# --- THIS IS THE CORRECTED PART ---
# Get the absolute path of the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Get the absolute path of the project's root directory
# e.g., /Users/sakshigupta/Desktop/adtm
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Build robust paths to all necessary files and folders
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'config.yaml')
RAW_DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'raw', 'sec-edgar-filings')
DATABASE_PATH = os.path.join(PROJECT_ROOT, 'sql', 'adtm.db')
SCHEMA_PATH = os.path.join(PROJECT_ROOT, 'sql', 'schema.sql')
PROCESSED_DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed')

# Add the project's python directory to the system path to find utils_text
# This makes imports more reliable
sys.path.append(SCRIPT_DIR)

# --- Load Config File ---
try:
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    print(f"ERROR: Configuration file not found at {CONFIG_PATH}")
    exit()

# --- 2. DATABASE SETUP ---
def setup_database():
    """Reads the schema.sql file and executes it to create the DB structure."""
    print(f"Setting up database at: {DATABASE_PATH}")
    # Ensure the directory for the DB exists
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()
    try:
        with open(SCHEMA_PATH, 'r') as f:
            schema_sql = f.read()
        cur.executescript(schema_sql)
        print("Database tables created successfully from schema.")
    except FileNotFoundError:
        print(f"ERROR: SQL schema file not found at {SCHEMA_PATH}")
        conn.close()
        exit()
    except Exception as e:
        print(f"ERROR setting up database: {e}")
        conn.close()
        exit()

    # Populate the 'terms' dimension table from config.yaml
    terms_to_insert = []
    for category, terms_list in config['terms'].items():
        for term in terms_list:
            terms_to_insert.append((term, category))
    
    cur.executemany("INSERT OR IGNORE INTO terms (term, category) VALUES (?, ?)", terms_to_insert)
    print(f"{cur.rowcount} new terms inserted into 'terms' table.")
    
    conn.commit()
    conn.close()


def gather_filings(base_path):
    """Scans the directory for downloaded filings and collects their metadata."""
    filings_metadata = []
    print("Scanning for downloaded filings...")
    if not os.path.exists(base_path):
        print(f"WARNING: Raw data directory not found at {base_path}. Did you run 00_fetch_edgar.py?")
        return pd.DataFrame()

    for ticker in tqdm(os.listdir(base_path), desc="Scanning Tickers"):
        ticker_path = os.path.join(base_path, ticker)
        if not os.path.isdir(ticker_path): continue
        
        for form_type in os.listdir(ticker_path):
            form_path = os.path.join(ticker_path, form_type)
            if not os.path.isdir(form_path): continue

            for filing_dir in os.listdir(form_path):
                filing_path = os.path.join(form_path, filing_dir, 'full-submission.txt')
                if os.path.exists(filing_path):
                    try:
                        # --- THIS IS THE CORRECTED LOGIC ---
                        # The directory name format is CIK-YY-SERIAL
                        # Unpack into three variables instead of two.
                        cik, date_year_part, serial = filing_dir.split('-')
                        
                        # The date_year_part is just the two-digit year, which is not enough
                        # for a full date. We will extract the full date from the filing text later.
                        # For now, let's just create a year for filtering.
                        filing_year = f"20{date_year_part}"

                        # A better approach is to parse the filing's header, but that's more complex.
                        # For this project, we will extract the date from the filename or a known line.
                        # Let's assume for now we only need the CIK and can get the date later.
                        # The downloader library unfortunately doesn't save the full date in the folder name.
                        # Let's grab the date from the header of the submission file.
                        
                        full_date = None
                        with open(filing_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                if line.startswith("FILED AS OF DATE:"):
                                    date_str = line.strip().split(":")[-1].strip()
                                    # Format is YYYYMMDD
                                    full_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                                    break # Stop after finding the date
                        
                        if full_date:
                             filings_metadata.append({
                                'cik': cik,
                                'ticker': ticker,
                                'form_type': form_type,
                                'filing_date': full_date,
                                'file_path': filing_path
                            })
                        else:
                            print(f"Could not find filing date for {filing_dir}, skipping.")

                    except (ValueError, IndexError):
                        print(f"Skipping directory with unexpected name format: {filing_dir}")
                        continue
                        
    return pd.DataFrame(filings_metadata)

def process_single_filing(metadata_row):
    """
    Reads, parses, analyzes a single filing and returns its scores, counts, and snippets.
    """
    try:
        with open(metadata_row['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
            raw_content = f.read()
    except Exception as e:
        # print(f"Could not read {metadata_row['file_path']}: {e}") # Uncomment for debugging
        return None, None, None

    # Step A: Extract Text & Basic Validation
    text = extract_text_from_html(raw_content)
    if not text:
        return None, None, None
    word_count = len(re.findall(r'\w+', text))
    if word_count < 1000:  # Skip very short or empty filings
        return None, None, None

    # Step B: Parse into Sections
    sections = parse_sections(text, config['sections'])
    
    # Step C: Count Terms and Collect Snippets
    counts_list = []
    snippets_list = []
    
    for category, terms in config['terms'].items():
        for term in terms:
            for section_name, section_text in sections.items():
                matches = list(re.finditer(r'\b' + re.escape(term) + r'\b', section_text, flags=re.IGNORECASE))
                
                if matches:
                    counts_list.append({
                        'term': term,
                        'section': section_name,
                        'frequency': len(matches)
                    })
                    for match in matches:
                        start = max(0, match.start() - 250) # Approx 50 words before
                        end = min(len(section_text), match.end() + 250) # Approx 50 words after
                        snippet_text = f"...{section_text[start:end]}..."
                        snippets_list.append({'term': term, 'context': snippet_text})

    if not counts_list:
        scores_data = {'word_count': word_count, 'T_score': 0, 'R_score': 0, 'A_score': 0, 'RAI_score': 0}
        return scores_data, pd.DataFrame(), pd.DataFrame()

    # Step D: Calculate Scores
    df_counts = pd.DataFrame(counts_list)
    
    # Transparency Score (T)
    usage_mentions = df_counts[df_counts['term'].isin(config['terms']['usage'])]['frequency'].sum()
    t_score = (usage_mentions / word_count) * 1000
    
    # Risk Acknowledgment Score (R)
    risk_section_key = "item 1a. risk factors"
    risk_mentions = df_counts[
        (df_counts['section'] == risk_section_key) & 
        (df_counts['term'].isin(config['terms']['usage'] + config['terms']['governance']))
    ]['frequency'].sum()
    r_score = (risk_mentions / word_count) * 1000
    
    # Actionability Score (A)
    action_mentions = df_counts[df_counts['term'].isin(config['terms']['action'])]['frequency'].sum()
    a_score = (action_mentions / word_count) * 1000

    # Composite RAI Score
    w = config['weights']
    rai_score = (w['transparency'] * t_score) + (w['risk'] * r_score) + (w['action'] * a_score)
    
    scores_data = {'word_count': word_count, 'T_score': t_score, 'R_score': r_score, 'A_score': a_score, 'RAI_score': rai_score}
    
    return scores_data, df_counts, pd.DataFrame(snippets_list)


# --- 4. MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    # Part 1: Setup
    setup_database()
    
    # Part 2: Load terms from DB to create a term -> term_id mapping for efficiency
    conn = sqlite3.connect(DATABASE_PATH)
    df_terms = pd.read_sql_query("SELECT term_id, term FROM terms", conn)
    term_to_id_map = pd.Series(df_terms.term_id.values, index=df_terms.term).to_dict()
    conn.close()

    # Part 3: Gather and process all filings
    df_filings_meta = gather_filings(RAW_DATA_PATH)
    if df_filings_meta.empty:
        print("No filings found to process. Exiting.")
    else:
        print(f"Found {len(df_filings_meta)} filings to process. Starting pipeline...")
        
        conn = sqlite3.connect(DATABASE_PATH)
        for _, row in tqdm(df_filings_meta.iterrows(), total=len(df_filings_meta), desc="Processing Filings"):
            
            # --- CHANGES ARE IN THIS SECTION ---

            # Process the content of the filing first to get the word_count
            scores_data, df_counts, df_snippets = process_single_filing(row)
            
            if scores_data:
                # Add word_count to the filing's metadata before saving it
                row['word_count'] = scores_data['word_count']
                
                # Save the filing metadata (now including word_count) and get its unique ID
                filing_df_to_insert = pd.DataFrame([row])
                filing_df_to_insert.to_sql('filings', conn, if_exists='append', index=False)
                filing_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                # Now, prepare the scores data *without* the word_count
                scores_to_insert = {
                    'filing_id': filing_id,
                    'T_score': scores_data['T_score'],
                    'R_score': scores_data['R_score'],
                    'A_score': scores_data['A_score'],
                    'RAI_score': scores_data['RAI_score']
                }
                df_scores = pd.DataFrame([scores_to_insert])
                df_scores.to_sql('scores', conn, if_exists='append', index=False) # This will no longer error

                # The rest of the loop for counts and snippets is fine...
                if not df_counts.empty:
                    df_counts['term_id'] = df_counts['term'].map(term_to_id_map)
                    df_counts['filing_id'] = filing_id
                    df_counts.dropna(subset=['term_id'], inplace=True)
                    df_counts['term_id'] = df_counts['term_id'].astype(int)
                    df_counts[['filing_id', 'term_id', 'section', 'frequency']].to_sql('counts', conn, if_exists='append', index=False)

                if not df_snippets.empty:
                    df_snippets['term_id'] = df_snippets['term'].map(term_to_id_map)
                    df_snippets['filing_id'] = filing_id
                    df_snippets.dropna(subset=['term_id'], inplace=True)
                    df_snippets['term_id'] = df_snippets['term_id'].astype(int)
                    df_snippets[['filing_id', 'term_id', 'context']].to_sql('snippets', conn, if_exists='append', index=False)
        
        conn.commit()
        conn.close()
        
        # Part 4: Export denormalized data from SQL to CSV for Power BI
        print("\nExporting final datasets from SQL to CSV for Power BI...")
        os.makedirs(PROCESSED_DATA_PATH, exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        
        # Main dashboard data (one row per filing)
        main_query = """
        SELECT
            f.filing_id,
            f.ticker,
            f.form_type,
            f.filing_date,
            f.word_count,
            s.T_score,
            s.R_score,
            s.A_score,
            s.RAI_score
        FROM filings f
        JOIN scores s ON f.filing_id = s.filing_id;
        """
        df_dashboard_main = pd.read_sql_query(main_query, conn)
        df_dashboard_main.to_csv(os.path.join(PROCESSED_DATA_PATH, 'dashboard_main.csv'), index=False)
        
        # Detailed term counts data
        counts_query = """
        SELECT 
            f.filing_id,
            f.ticker,
            f.filing_date,
            t.term, 
            t.category, 
            c.section, 
            c.frequency
        FROM counts c
        JOIN filings f ON c.filing_id = f.filing_id
        JOIN terms t ON c.term_id = t.term_id;
        """
        df_all_counts = pd.read_sql_query(counts_query, conn)
        df_all_counts.to_csv(os.path.join(PROCESSED_DATA_PATH, 'all_counts.csv'), index=False)
        
        # Snippets data for drill-through
        snippets_query = """
        SELECT
            f.filing_id,
            f.ticker,
            t.term,
            s.context
        FROM snippets s
        JOIN filings f ON s.filing_id = f.filing_id
        JOIN terms t ON s.term_id = t.term_id;
        """
        df_all_snippets = pd.read_sql_query(snippets_query, conn)
        df_all_snippets.to_csv(os.path.join(PROCESSED_DATA_PATH, 'all_snippets.csv'), index=False)

        conn.close()
        
        print("\n--- PIPELINE FINISHED SUCCESSFULLY ---")
        print(f"Database '{DATABASE_PATH}' is fully populated.")
        print(f"CSVs for Power BI are ready in: {os.path.abspath(PROCESSED_DATA_PATH)}")