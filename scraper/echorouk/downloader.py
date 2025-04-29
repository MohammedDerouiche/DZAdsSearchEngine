import os
import pandas as pd
import requests
from pathlib import Path
import time
import random
import logging
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# Updated base directory structure
BASE_DIR = Path("d:/My Projects/DZAdsSearchEngine")
SCRAPER_DIR = BASE_DIR / "scraper"
NEWSPAPER_DIR = SCRAPER_DIR / "echorouk"  # Specific newspaper directory
DATA_DIR = NEWSPAPER_DIR / "data"  # Data directory for this newspaper

# Create directories if they don't exist
NEWSPAPER_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging with updated paths
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DATA_DIR / "download_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('echorouk_downloader')

class EchoroukPDFDownloader:
    """
    Downloads PDF files for Echorouk newspaper based on issue mapping.
    """
    def __init__(self, mapping_file=None, output_dir=None):
        """
        Initialize the PDF downloader.
        
        Args:
            mapping_file: Path to the issue mapping CSV file
            output_dir: Directory to save downloaded PDFs
        """
        if mapping_file is None:
            mapping_file = DATA_DIR / "publication_dates.csv"
        
        if output_dir is None:
            output_dir = DATA_DIR
        
        self.mapping_file = Path(mapping_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Updated URL template based on the example provided
        self.pdf_url_template = "https://www.echoroukonline.com/wp-content/uploads/{year}/{month}/{issue_number}.pdf"
        
        # Set browser-like headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/pdf,application/x-pdf',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Referer': 'https://www.echoroukonline.com/',
        }
        
        # Load the mapping file
        self.mapping_df = None
        self.load_mapping()
    
    def load_mapping(self):
        """Load issue mapping from CSV file."""
        if not os.path.exists(self.mapping_file):
            raise FileNotFoundError(f"Mapping file not found: {self.mapping_file}")
        
        self.mapping_df = pd.read_csv(self.mapping_file)
        
        # Sort by issue number if available, otherwise by index
        if 'issue_number' in self.mapping_df.columns:
            self.mapping_df = self.mapping_df.sort_values(by='issue_number', ascending=True)
            logger.info(f"Sorted mapping by issue number (ascending)")
        else:
            self.mapping_df = self.mapping_df.sort_values(by='index', ascending=True)
            logger.info(f"Sorted mapping by index (ascending)")
        
        logger.info(f"Loaded {len(self.mapping_df)} issue mappings from {self.mapping_file}")
    
    def generate_pdf_url(self, issue_number, date_str):
        """Generate PDF URL for a given issue number and date."""
        try:
            # Parse the date to extract year and month
            date_parts = date_str.split('-')
            year = date_parts[0]
            month = date_parts[1].zfill(2)  # Ensure month is two digits
            
            # Format the URL with the correct year, month, and issue number
            return self.pdf_url_template.format(year=year, month=month, issue_number=issue_number)
        except Exception as e:
            logger.error(f"Error generating URL for issue {issue_number}: {str(e)}")
            # Fallback to a simpler URL if date parsing fails
            return f"https://www.echoroukonline.com/wp-content/uploads/{issue_number}.pdf"
    
    def download_pdf(self, row):
        """
        Download a single PDF file.
        
        Args:
            row: DataFrame row containing issue information
            
        Returns:
            Tuple of (success, issue_number, filepath or error message)
        """
        issue_number = row['issue_number']
        date_str = row['date']
        
        # Create filename with date and issue number
        filename = f"echorouk_{date_str}_{issue_number}.pdf"
        filepath = self.output_dir / filename
        
        # Skip if file already exists
        if filepath.exists():
            return (True, issue_number, f"Already exists: {filepath}")
        
        # Generate URL with the correct format
        url = self.generate_pdf_url(issue_number, date_str)
        
        # Log the URL being attempted
        logger.info(f"Attempting to download from: {url}")
        
        try:
            # Add a random delay to avoid overwhelming the server
            delay = random.uniform(1, 3)
            time.sleep(delay)
            
            # Download the PDF
            response = requests.get(url, headers=self.headers, timeout=30, stream=True)
            
            if response.status_code == 200:
                # Check if it's actually a PDF
                content_type = response.headers.get('Content-Type', '')
                if 'application/pdf' in content_type or len(response.content) > 10000:
                    # Save the PDF
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    return (True, issue_number, str(filepath))
                else:
                    return (False, issue_number, f"Not a PDF: {url} (Content-Type: {content_type})")
            else:
                return (False, issue_number, f"Failed with status code {response.status_code}: {url}")
        
        except Exception as e:
            return (False, issue_number, f"Error downloading {url}: {str(e)}")
    
    def download_all_pdfs(self, start_index=0, end_index=None, max_workers=3):
        """
        Download all PDF files based on the issue mapping.
        
        Args:
            start_index: Index to start from in the mapping DataFrame
            end_index: Index to end at in the mapping DataFrame (None for all)
            max_workers: Maximum number of concurrent downloads
            
        Returns:
            List of successful downloads
        """
        if self.mapping_df is None:
            raise ValueError("No mapping loaded. Call load_mapping() first.")
        
        # Determine range to process
        if end_index is None:
            end_index = len(self.mapping_df)
        
        # Get subset of rows to process
        rows_to_process = self.mapping_df.iloc[start_index:end_index]
        total_rows = len(rows_to_process)
        
        logger.info(f"Starting download of {total_rows} PDFs from index {start_index} to {end_index-1}")
        
        successful_downloads = []
        failed_downloads = []
        
        # Use ThreadPoolExecutor for concurrent downloads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_row = {executor.submit(self.download_pdf, row): row for _, row in rows_to_process.iterrows()}
            
            # Process results as they complete
            with tqdm(total=total_rows, desc="Downloading PDFs") as pbar:
                for future in as_completed(future_to_row):
                    success, issue_number, message = future.result()
                    
                    if success:
                        successful_downloads.append((issue_number, message))
                        logger.info(f"Successfully downloaded issue {issue_number}: {message}")
                    else:
                        failed_downloads.append((issue_number, message))
                        logger.warning(f"Failed to download issue {issue_number}: {message}")
                    
                    pbar.update(1)
        
        # Log summary
        logger.info(f"Download complete. {len(successful_downloads)} successful, {len(failed_downloads)} failed.")
        
        # Save failed downloads to a file for later retry
        if failed_downloads:
            failed_file = self.output_dir / "failed_downloads.txt"
            with open(failed_file, 'w', encoding='utf-8') as f:
                for issue_number, message in failed_downloads:
                    f.write(f"{issue_number}: {message}\n")
            logger.info(f"Saved failed downloads to {failed_file}")
        
        return successful_downloads

def main():
    """
    Main function to handle user input and download PDFs.
    """
    print("\nEchorouk PDF Downloader")
    print("======================")
    
    # Initialize the downloader with default options
    downloader = EchoroukPDFDownloader()
    
    # Get download range
    try:
        start_index = int(input("\nEnter start index (0 for beginning): ") or "0")
        end_input = input("Enter end index (leave empty for all): ")
        end_index = int(end_input) if end_input else None
        
        max_workers = int(input("\nEnter maximum concurrent downloads (default: 3): ") or "3")
        
        print(f"\nStarting download from index {start_index}" + 
              (f" to {end_index-1}" if end_index else " to end"))
        
        # Start the download
        successful_downloads = downloader.download_all_pdfs(start_index, end_index, max_workers)
        
        print(f"\nDownload complete. {len(successful_downloads)} PDFs downloaded successfully.")
        
    except ValueError as e:
        print(f"Invalid input: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()