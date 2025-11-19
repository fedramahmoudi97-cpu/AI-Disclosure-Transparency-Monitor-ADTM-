from sec_edgar_downloader import Downloader
import os

def fetch_filings():
    # List of 10 companies (Ticker: CIK)
    companies = {
        "MSFT": "0000789019", # Microsoft
        "GOOGL": "0001652044",# Alphabet
        "JPM": "0000019617",  # JPMorgan Chase
        "META": "0001326801", # Meta Platforms
        "NVDA": "0001045810", # Nvidia
        "AMZN": "0001018724", # Amazon
        "AAPL": "0000320193", # Apple
        "IBM": "0000051143",  # IBM
        "ORCL": "0001341439", # Oracle
        "TSLA": "0001318604"  # Tesla
    }

    # SEC EDGAR API requirements
    company_name = "Fedra"
    email_address = "fedramahmoudi97@gmail.com"
    
    # --- THIS IS THE CORRECTED PART ---
    # Build a path relative to this script's location to ensure correctness.
    # __file__ is the path to the current script (00_fetch_edgar.py)
    # os.path.dirname() gets the directory of that file (.../adtm/python)
    # The second os.path.dirname() goes up one level to the project root (.../adtm)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    download_path = os.path.join(project_root, "data", "raw")
    
    # Ensure the download directory exists
    os.makedirs(download_path, exist_ok=True)
    
    # Initialize the Downloader
    dl = Downloader(company_name, email_address, download_path)
    
    print("Starting download of SEC filings...")
    print(f"Files will be saved in: {download_path}") # Added for clarity

    for ticker, cik in companies.items():
        try:
            # Download the 5 most recent 10-K filings
            dl.get("10-K", ticker, limit=5)
            print(f"Successfully downloaded 10-K filings for {ticker}")

            # Download the 5 most recent 10-Q filings
            dl.get("10-Q", ticker, limit=5)
            print(f"Successfully downloaded 10-Q filings for {ticker}")

        except Exception as e:
            print(f"Could not download filings for {ticker}. Error: {e}")
            
    print("\nAll downloads complete.")
    print(f"Raw files are stored in: {os.path.abspath(download_path)}")

if __name__ == "__main__":
    fetch_filings()