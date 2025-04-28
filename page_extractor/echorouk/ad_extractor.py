import os
import sys
from pathlib import Path
import pandas as pd
import logging
import google.generativeai as genai
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import time
import json
import argparse
from tqdm import tqdm
import pytesseract
from PIL import Image
import re

# Configure base directories
BASE_DIR = Path("d:/My Projects/DZAdsSearchEngine")
PAGE_EXTRACTOR_DIR = BASE_DIR / "page_extractor"
NEWSPAPER_DIR = PAGE_EXTRACTOR_DIR / "echorouk"
DATA_DIR = NEWSPAPER_DIR / "data"
PDF_DIR = BASE_DIR / "scraper" / "echorouk" / "data"

# Create directories if they don't exist
NEWSPAPER_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(NEWSPAPER_DIR / "ad_extractor_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('echorouk_ad_extractor')

class EchoroukAdExtractor:
    """
    Extracts ad pages from Echorouk newspaper PDFs using both Gemini API and text detection.
    """
    def __init__(self, api_key=None, config_path=None, poppler_path=None, tesseract_path=None):
        """
        Initialize the ad extractor.
        
        Args:
            api_key: Gemini API key
            config_path: Path to configuration file
            poppler_path: Path to poppler binaries
            tesseract_path: Path to Tesseract OCR executable
        """
        self.api_key = api_key
        self.poppler_path = poppler_path
        self.tesseract_path = tesseract_path
        
        # Load config if provided
        if config_path:
            self.load_config(config_path)
        
        # Initialize Gemini API if key is provided
        self.use_gemini = False
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro-vision')
                self.use_gemini = True
                logger.info("Gemini API initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini API: {str(e)}")
                logger.info("Falling back to text-based detection only")
        else:
            logger.info("No Gemini API key provided. Using text-based detection only.")
        
        # Set up pytesseract for OCR (for Arabic text detection)
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            logger.info(f"Tesseract OCR path set to: {self.tesseract_path}")
        
        # Create output directories
        self.ads_csv_path = NEWSPAPER_DIR / "ads_pages.csv"
        self.ads_images_dir = DATA_DIR
        self.ads_images_dir.mkdir(parents=True, exist_ok=True)
        
        # Arabic ad indicators
        self.ad_indicators = [
            "إشهار",  # Main ad indicator
            "إعلان",  # Another word for advertisement
            "الإعلانات",  # Advertisements
            "إعلانات",  # Advertisements
            "اتصل بمصلحة الإشهار",  # Contact advertising department
            "للإعلان",  # For advertising
            "السوق",  # Market (often in ad sections)
            "عروض",  # Offers
            "مناقصة",  # Tender
            "مزايدة",  # Auction
            "بيع",  # Sale
            "شراء"  # Purchase
        ]
    
    def load_config(self, config_path):
        """Load configuration from a JSON file."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.api_key = config.get('gemini_api_key', self.api_key)
                self.poppler_path = config.get('poppler_path', self.poppler_path)
                self.tesseract_path = config.get('tesseract_path', self.tesseract_path)
                logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
    
    def detect_ads_with_ocr(self, image):
        """
        Detect advertisements using OCR to find Arabic ad indicators.
        
        Args:
            image: PIL Image object
            
        Returns:
            Tuple of (contains_ads, confidence, detected_indicators)
        """
        try:
            # Check if Tesseract is available
            if not self.is_tesseract_available():
                logger.warning("Tesseract OCR is not available. Skipping OCR detection.")
                return False, 0, []
                
            # Use pytesseract with Arabic language support
            text = pytesseract.image_to_string(image, lang='ara+eng')
            
            # Check for ad indicators
            detected_indicators = []
            for indicator in self.ad_indicators:
                if indicator in text:
                    detected_indicators.append(indicator)
            
            # Calculate confidence based on number of indicators found
            confidence = min(100, len(detected_indicators) * 25)
            contains_ads = len(detected_indicators) > 0
            
            return contains_ads, confidence, detected_indicators
            
        except Exception as e:
            logger.error(f"Error in OCR detection: {str(e)}")
            # If OCR fails, fall back to Gemini if available
            if self.use_gemini:
                logger.info("Falling back to Gemini for this page due to OCR error")
                return False, 0, []
            else:
                # If Gemini is not available, assume no ads to continue processing
                return False, 0, []
    
    def is_tesseract_available(self):
        """Check if Tesseract OCR is available."""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    def analyze_with_gemini(self, image):
        """
        Analyze an image with Gemini to identify if it contains ads.
        
        Args:
            image: PIL Image object
            
        Returns:
            Tuple of (contains_ads, confidence, ad_types)
        """
        if not self.use_gemini:
            return False, 0, []
        
        try:
            # Prepare prompt for Gemini
            prompt = """
            Analyze this newspaper page in Arabic and determine if it contains advertisements.
            Focus on identifying commercial ads, classified ads, or announcement sections.
            Look for the word "إشهار" (advertisement) which often appears at the top of ad pages.
            
            Return ONLY a JSON object with the following structure:
            {
                "contains_ads": true/false,
                "confidence": 0-100,
                "ad_types": ["commercial", "classified", "announcement", etc.],
                "description": "Brief description of the ads found"
            }
            """
            
            # Call Gemini API
            response = self.model.generate_content([prompt, image])
            
            # Parse the response
            try:
                # Extract JSON from the response
                response_text = response.text
                # Find JSON content between triple backticks if present
                if "```json" in response_text:
                    json_content = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_content = response_text.split("```")[1].strip()
                else:
                    json_content = response_text.strip()
                
                result = json.loads(json_content)
                
                contains_ads = result.get("contains_ads", False)
                confidence = result.get("confidence", 0)
                ad_types = result.get("ad_types", [])
                
                return contains_ads, confidence, ad_types
                
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON response: {response.text}")
                return False, 0, []
            
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return False, 0, []
    
    def analyze_page(self, image, page_num):
        """
        Analyze a page using both OCR and Gemini (if available).
        
        Args:
            image: PIL Image object
            page_num: Page number
            
        Returns:
            Boolean indicating if the page contains ads
        """
        # First try OCR detection (faster and doesn't use API quota)
        ocr_contains_ads, ocr_confidence, detected_indicators = self.detect_ads_with_ocr(image)
        
        if ocr_contains_ads and ocr_confidence >= 50:
            logger.info(f"Page {page_num}: OCR detected ads with {ocr_confidence}% confidence")
            logger.info(f"Detected indicators: {detected_indicators}")
            return True
        
        # If OCR is not confident enough or failed, and Gemini is available, try Gemini
        if self.use_gemini:
            gemini_contains_ads, gemini_confidence, ad_types = self.analyze_with_gemini(image)
            
            if gemini_contains_ads and gemini_confidence >= 50:
                logger.info(f"Page {page_num}: Gemini detected ads with {gemini_confidence}% confidence")
                logger.info(f"Ad types: {ad_types}")
                return True
            
            # If both methods found something but with low confidence, combine their results
            if ocr_contains_ads or gemini_contains_ads:
                combined_confidence = max(ocr_confidence, gemini_confidence)
                if combined_confidence >= 30:  # Lower threshold for combined methods
                    logger.info(f"Page {page_num}: Combined detection with {combined_confidence}% confidence")
                    return True
        
        return False  # Changed from ocr_contains_ads to False since OCR might not be available
    
    def analyze_pdf(self, pdf_path):
        """
        Analyze a PDF file to identify ad pages.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of page numbers containing ads
        """
        try:
            # Extract PDF info
            pdf = PdfReader(pdf_path)
            total_pages = len(pdf.pages)
            
            logger.info(f"Analyzing PDF: {pdf_path.name} ({total_pages} pages)")
            
            # Analyze all pages (or up to a reasonable limit)
            max_pages_to_analyze = min(total_pages, 20)  # Analyze up to 20 pages
            
            ad_pages = []
            
            # Convert pages to images and analyze them
            images = convert_from_path(
                pdf_path, 
                first_page=1, 
                last_page=max_pages_to_analyze,
                dpi=150,  # Medium DPI for balance of speed and accuracy
                poppler_path=self.poppler_path  # Add poppler path here
            )
            
            for i, image in enumerate(images, 1):
                logger.info(f"Analyzing page {i} of {pdf_path.name}")
                
                if self.analyze_page(image, i):
                    ad_pages.append(i)
                
                # Add a small delay to avoid overwhelming resources
                time.sleep(0.5)
            
            return ad_pages
            
        except Exception as e:
            logger.error(f"Error analyzing PDF {pdf_path}: {str(e)}")
            return []
    
    def extract_ad_pages(self, pdf_path, ad_pages):
        """
        Extract ad pages from a PDF and save them as images.
        
        Args:
            pdf_path: Path to the PDF file
            ad_pages: List of page numbers to extract
            
        Returns:
            List of paths to the extracted images
        """
        if not ad_pages:
            logger.info(f"No ad pages to extract from {pdf_path.name}")
            return []
        
        # Create output directory based on PDF name
        pdf_name = pdf_path.stem
        output_dir = self.ads_images_dir / pdf_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Extracting {len(ad_pages)} ad pages from {pdf_path.name}")
        
        extracted_images = []
        
        try:
            # Convert specific pages to images
            for page_num in ad_pages:
                images = convert_from_path(
                    pdf_path,
                    first_page=page_num,
                    last_page=page_num,
                    dpi=300,  # Higher DPI for better quality
                    poppler_path=self.poppler_path  # Add poppler path here
                )
                
                if images:
                    image_path = output_dir / f"page_{page_num}.jpg"
                    images[0].save(image_path, "JPEG")
                    extracted_images.append(str(image_path))
                    logger.info(f"Saved ad page {page_num} to {image_path}")
            
            return extracted_images
            
        except Exception as e:
            logger.error(f"Error extracting pages from {pdf_path}: {str(e)}")
            return []
    
    def process_pdfs(self, pdf_dir=None, limit=None, start_date=None, end_date=None, start_issue=None, end_issue=None):
        """
        Process PDFs in a directory to extract ad pages, with filtering options.
        
        Args:
            pdf_dir: Directory containing PDF files
            limit: Maximum number of PDFs to process
            start_date: Start date for filtering PDFs (format: YYYY-MM-DD)
            end_date: End date for filtering PDFs (format: YYYY-MM-DD)
            start_issue: Start issue number for filtering PDFs
            end_issue: End issue number for filtering PDFs
            
        Returns:
            DataFrame with ad page information
        """
        if pdf_dir is None:
            pdf_dir = PDF_DIR
        else:
            pdf_dir = Path(pdf_dir)
        
        # Find all PDF files
        pdf_files = list(pdf_dir.glob("*.pdf"))
        
        # Filter by date if specified
        if start_date or end_date:
            filtered_files = []
            for pdf_file in pdf_files:
                # Try to extract date from filename
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', pdf_file.stem)
                if date_match:
                    file_date = date_match.group(1)
                    if start_date and file_date < start_date:
                        continue
                    if end_date and file_date > end_date:
                        continue
                    filtered_files.append(pdf_file)
                else:
                    logger.warning(f"Could not extract date from filename: {pdf_file.name}")
            
            pdf_files = filtered_files
            logger.info(f"Filtered to {len(pdf_files)} PDFs by date range")
        
        # Filter by issue number if specified
        if start_issue or end_issue:
            filtered_files = []
            for pdf_file in pdf_files:
                # Try to extract issue number from filename
                issue_match = re.search(r'issue[_-]?(\d+)', pdf_file.stem, re.IGNORECASE)
                if issue_match:
                    issue_num = int(issue_match.group(1))
                    if start_issue and issue_num < start_issue:
                        continue
                    if end_issue and issue_num > end_issue:
                        continue
                    filtered_files.append(pdf_file)
                else:
                    # Alternative: try to extract issue number from the end of the filename
                    issue_match = re.search(r'_(\d+)\.pdf$', str(pdf_file), re.IGNORECASE)
                    if issue_match:
                        issue_num = int(issue_match.group(1))
                        if start_issue and issue_num < start_issue:
                            continue
                        if end_issue and issue_num > end_issue:
                            continue
                        filtered_files.append(pdf_file)
                    else:
                        logger.warning(f"Could not extract issue number from filename: {pdf_file.name}")
            
            pdf_files = filtered_files
            logger.info(f"Filtered to {len(pdf_files)} PDFs by issue number range")
        
        # Apply limit if specified
        if limit:
            pdf_files = pdf_files[:limit]
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Sort files by name for consistent processing
        pdf_files.sort()
        
        results = []
        
        for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
            try:
                # Analyze PDF to find ad pages
                ad_pages = self.analyze_pdf(pdf_file)
                
                if ad_pages:
                    # Extract ad pages as images
                    extracted_images = self.extract_ad_pages(pdf_file, ad_pages)
                    
                    # Add to results
                    results.append({
                        "pdf_file": str(pdf_file),
                        "pdf_name": pdf_file.stem,
                        "ad_pages": ad_pages,
                        "extracted_images": extracted_images,
                        "num_ad_pages": len(ad_pages)
                    })
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {str(e)}")
        
        # Create DataFrame from results
        results_df = pd.DataFrame(results) if results else pd.DataFrame()
        
        # Save to CSV
        if not results_df.empty:
            results_df.to_csv(self.ads_csv_path, index=False)
            logger.info(f"Saved ad page information to {self.ads_csv_path}")
        
        return results_df

    def get_available_ranges(self, pdf_dir=None):
        """
        Get the available date and issue number ranges from the PDF files.
        
        Args:
            pdf_dir: Directory containing PDF files
            
        Returns:
            Tuple of (date_range, issue_range) where each is a tuple of (min, max)
        """
        if pdf_dir is None:
            pdf_dir = PDF_DIR
        else:
            pdf_dir = Path(pdf_dir)
        
        # Find all PDF files
        pdf_files = list(pdf_dir.glob("*.pdf"))
        
        dates = []
        issue_numbers = []
        
        for pdf_file in pdf_files:
            # Try to extract date from filename
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', pdf_file.stem)
            if date_match:
                dates.append(date_match.group(1))
            
            # Try to extract issue number from filename
            issue_match = re.search(r'issue[_-]?(\d+)', pdf_file.stem, re.IGNORECASE)
            if issue_match:
                issue_numbers.append(int(issue_match.group(1)))
            else:
                # Alternative: try to extract issue number from the end of the filename
                issue_match = re.search(r'_(\d+)\.pdf$', str(pdf_file), re.IGNORECASE)
                if issue_match:
                    issue_numbers.append(int(issue_match.group(1)))
        
        # Get min and max dates
        date_range = (min(dates) if dates else None, max(dates) if dates else None)
        
        # Get min and max issue numbers
        issue_range = (min(issue_numbers) if issue_numbers else None, max(issue_numbers) if issue_numbers else None)
        
        return date_range, issue_range

def main():
    """
    Main function to handle command-line arguments and run the ad extractor.
    """
    print("\nEchorouk Ad Page Extractor")
    print("=========================")
    
    parser = argparse.ArgumentParser(description='Extract ad pages from Echorouk newspaper PDFs')
    parser.add_argument('--api-key', help='Gemini API key')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--pdf-dir', help='Directory containing PDF files')
    parser.add_argument('--poppler-path', help='Path to poppler binaries')
    parser.add_argument('--tesseract-path', help='Path to Tesseract OCR executable')
    parser.add_argument('--limit', type=int, help='Maximum number of PDFs to process')
    parser.add_argument('--start-date', help='Start date for filtering PDFs (format: YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for filtering PDFs (format: YYYY-MM-DD)')
    parser.add_argument('--start-issue', type=int, help='Start issue number for filtering PDFs')
    parser.add_argument('--end-issue', type=int, help='End issue number for filtering PDFs')
    
    args = parser.parse_args()
    
    # Get configuration
    config_path = args.config
    if not config_path:
        config_path = Path(__file__).parent / "config.json"
    
    # Check if config exists, if not, create it
    if not Path(config_path).exists() and not (args.api_key and args.poppler_path and args.tesseract_path):
        print(f"\nConfiguration file not found at {config_path}")
        api_key = input("Please enter your Gemini API key (leave empty to use text-based detection only): ")
        poppler_path = input("Please enter the path to poppler binaries (e.g., C:\\Program Files\\poppler-23.11.0\\Library\\bin): ")
        tesseract_path = input("Please enter the path to Tesseract OCR executable (e.g., C:\\Program Files\\Tesseract-OCR\\tesseract.exe): ")
        
        # Save the config file if provided
        if api_key.strip() or poppler_path.strip() or tesseract_path.strip():
            import json
            with open(config_path, 'w') as f:
                config = {}
                if api_key.strip():
                    config["gemini_api_key"] = api_key
                if poppler_path.strip():
                    config["poppler_path"] = poppler_path
                if tesseract_path.strip():
                    config["tesseract_path"] = tesseract_path
                json.dump(config, f, indent=4)
            print(f"Configuration saved to {config_path}")
    
    try:
        # Initialize the ad extractor
        extractor = EchoroukAdExtractor(
            api_key=args.api_key,
            config_path=config_path if Path(config_path).exists() else None,
            poppler_path=args.poppler_path,
            tesseract_path=args.tesseract_path
        )
        
        # Get available ranges
        date_range, issue_range = extractor.get_available_ranges(args.pdf_dir)
        
        # Get filtering parameters from command line or ask user
        start_date = args.start_date
        end_date = args.end_date
        start_issue = args.start_issue
        end_issue = args.end_issue
        limit = args.limit
        
        # If running interactively and no filtering parameters provided, ask user
        if not any([args.pdf_dir, args.start_date, args.end_date, args.start_issue, args.end_issue, args.limit]):
            # Add a loop to handle invalid input
            filter_option = None
            while filter_option not in ["1", "2", "3"]:
                print("\nPDF filtering options:")
                print("1. Filter by date range")
                print("2. Filter by issue number range")
                print("3. Process all PDFs (or limit by count)")
                
                filter_option = input("\nSelect filtering option (1-3): ").strip()
                
                if filter_option not in ["1", "2", "3"]:
                    print("\nInvalid option. Please enter 1, 2, or 3.")
            
            if filter_option == "1":
                if date_range[0] and date_range[1]:
                    print(f"\nAvailable date range: {date_range[0]} to {date_range[1]}")
                
                start_date = input("Enter start date (YYYY-MM-DD, leave empty for no lower bound): ").strip()
                end_date = input("Enter end date (YYYY-MM-DD, leave empty for no upper bound): ").strip()
                
            elif filter_option == "2":
                if issue_range[0] and issue_range[1]:
                    print(f"\nAvailable issue range: {issue_range[0]} to {issue_range[1]}")
                
                start_issue_input = input("Enter start issue number (leave empty for no lower bound): ").strip()
                start_issue = int(start_issue_input) if start_issue_input else None
                
                end_issue_input = input("Enter end issue number (leave empty for no upper bound): ").strip()
                end_issue = int(end_issue_input) if end_issue_input else None
            
            # Ask for limit regardless of filtering option
            limit_input = input("\nEnter maximum number of PDFs to process (leave empty for all): ").strip()
            limit = int(limit_input) if limit_input else None
        
        # Process PDFs
        print("\nStarting PDF processing...")
        results = extractor.process_pdfs(
            pdf_dir=args.pdf_dir,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            start_issue=start_issue,
            end_issue=end_issue
        )
        
        if not results.empty:
            print(f"\nProcessed {len(results)} PDFs")
            print(f"Found ads in {results['num_ad_pages'].sum()} pages")
            print(f"Results saved to {extractor.ads_csv_path}")
            
            # Show sample of results
            print("\nSample of processed PDFs:")
            print(results[['pdf_name', 'ad_pages', 'num_ad_pages']].head())
        else:
            print("\nNo PDFs were processed or no ads were found.")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()