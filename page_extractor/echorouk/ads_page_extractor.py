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
from datetime import datetime
import numpy as np
from PIL import ImageFilter

# Configure base directories
BASE_DIR = Path("d:/My Projects/DZAdsSearchEngine")
PAGE_EXTRACTOR_DIR = BASE_DIR / "page_extractor"
NEWSPAPER_DIR = PAGE_EXTRACTOR_DIR / "echorouk"
PDF_DIR = BASE_DIR / "scraper" / "echorouk" / "data"

# Create directories if they don't exist
NEWSPAPER_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(NEWSPAPER_DIR / "ads_page_extractor_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('echorouk_ads_page_extractor')

class EchoroukAdsPageExtractor:
    """
    Identifies ad pages in Echorouk newspaper PDFs using text detection and/or Gemini API.
    """
    def __init__(self, api_key=None, config_path=None, poppler_path=None, tesseract_path=None):
        """
        Initialize the ads page extractor.
        
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
        
        # Create output file path
        self.ads_csv_path = NEWSPAPER_DIR / "ads_pages.csv"
        
        # Arabic ad indicators - expanded list
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
            "شراء",  # Purchase
            "إعلان قانوني",  # Legal announcement
            "إعلانات مبوبة",  # Classified ads
            "إعلانات قانونية",  # Legal ads
            "إعلانات تجارية",  # Commercial ads
            "إعلان عن",  # Announcement about
            "إشهار تجاري",  # Commercial advertisement
            "إشهارات",  # Advertisements
            "إعلانكم",  # Your advertisements
            "إشهاركم",  # Your advertisements
            "الإشهار",  # Advertisement (with definite article)
            "تعلن",  # Announces
            "يعلن",  # Announces
            "إعلامكم",  # To inform you
            "إعلام",  # Information/announcement
            "فرصة",  # Opportunity
            "عرض خاص"  # Special offer
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
            
            # Log the extracted text for debugging
            logger.debug(f"Extracted text: {text[:200]}...")  # Log first 200 chars
            
            # Check for ad indicators
            detected_indicators = []
            for indicator in self.ad_indicators:
                if indicator in text:
                    detected_indicators.append(indicator)
            
            # Calculate confidence based on number of indicators found
            confidence = min(100, len(detected_indicators) * 20)  # Reduced multiplier for more gradual confidence
            
            # Lower threshold for detection - even one indicator is enough
            contains_ads = len(detected_indicators) > 0
            
            if detected_indicators:
                logger.info(f"OCR detected indicators: {detected_indicators}")
            
            return contains_ads, confidence, detected_indicators
            
        except Exception as e:
            logger.error(f"Error in OCR detection: {str(e)}")
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
                "confidence": 0-100
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
                
                return contains_ads, confidence, []
                
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
        
        # Lower the confidence threshold for OCR detection
        if ocr_contains_ads and ocr_confidence >= 20:  # Reduced from 50 to 20
            logger.info(f"Page {page_num}: OCR detected ads with {ocr_confidence}% confidence")
            return True
        
        # If OCR is not confident enough or failed, and Gemini is available, try Gemini
        if self.use_gemini:
            gemini_contains_ads, gemini_confidence, _ = self.analyze_with_gemini(image)
            
            # Lower the confidence threshold for Gemini detection
            if gemini_contains_ads and gemini_confidence >= 30:  # Reduced from 50 to 30
                logger.info(f"Page {page_num}: Gemini detected ads with {gemini_confidence}% confidence")
                return True
            
            # If both methods found something but with low confidence, combine their results
            if ocr_contains_ads or gemini_contains_ads:
                combined_confidence = max(ocr_confidence, gemini_confidence)
                if combined_confidence >= 15:  # Reduced from 30 to 15
                    logger.info(f"Page {page_num}: Combined detection with {combined_confidence}% confidence")
                    return True
        
        # Visual heuristics - check for common ad page layouts
        # Ads often have multiple columns, boxes, or distinctive layouts
        try:
            # Convert to grayscale for analysis
            gray_image = image.convert('L')
            
            # Simple heuristic: check for many horizontal or vertical lines (common in ad layouts)
            # This is a very basic approach and might need refinement
            edges = gray_image.filter(ImageFilter.FIND_EDGES)
            pixels = np.array(edges)
            
            # Count horizontal and vertical lines
            h_lines = np.sum(pixels > 200, axis=1)
            v_lines = np.sum(pixels > 200, axis=0)
            
            # If there are many lines, it might be an ad page
            if np.sum(h_lines > pixels.shape[1] * 0.5) > 10 or np.sum(v_lines > pixels.shape[0] * 0.5) > 10:
                logger.info(f"Page {page_num}: Visual heuristics suggest this might be an ad page")
                return True
        except Exception as e:
            logger.warning(f"Error in visual heuristics: {str(e)}")
        
        # Check for pages that are typically ads in newspapers (e.g., last few pages)
        if page_num >= 15:  # Assuming ads are often in the last pages
            logger.info(f"Page {page_num}: Might be an ad page based on position in newspaper")
            return True
        
        return False
    
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
            max_pages_to_analyze = min(total_pages, 30)  # Increased from 20 to 30
            
            ad_pages = []
            
            # Convert pages to images and analyze them
            convert_params = {
                'pdf_path': pdf_path,
                'first_page': 1,
                'last_page': max_pages_to_analyze,
                'dpi': 150  # Medium DPI for balance of speed and accuracy
            }
            
            # Add poppler_path if it's specified
            if self.poppler_path:
                convert_params['poppler_path'] = self.poppler_path
                
            images = convert_from_path(**convert_params)
            
            for i, image in enumerate(images, 1):
                logger.info(f"Analyzing page {i} of {pdf_path.name}")
                
                if self.analyze_page(image, i):
                    ad_pages.append(i)
                
                # Add a small delay to avoid overwhelming resources
                time.sleep(0.5)
            
            # If no ads found, try some common ad page numbers as a fallback
            if not ad_pages and total_pages > 10:
                # In many newspapers, ads are often in the last few pages
                potential_ad_pages = [total_pages, total_pages-1, total_pages-2, 
                                     total_pages//2, 3, 4]  # Common ad page positions
                
                logger.info(f"No ads detected, trying common ad page positions: {potential_ad_pages}")
                
                # Filter to pages within the PDF
                potential_ad_pages = [p for p in potential_ad_pages if 1 <= p <= total_pages]
                
                # Add a few potential ad pages as a fallback
                ad_pages = potential_ad_pages[:3]  # Take up to 3 potential ad pages
            
            return ad_pages
            
        except Exception as e:
            logger.error(f"Error analyzing PDF {pdf_path}: {str(e)}")
            return []
    
    def extract_metadata(self, pdf_path):
        """
        Extract metadata (issue number, date) from PDF filename.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (issue_number, date)
        """
        issue_number = None
        date = None
        
        # Try to extract issue number from filename
        issue_match = re.search(r'issue[_-]?(\d+)', pdf_path.stem, re.IGNORECASE)
        if issue_match:
            issue_number = int(issue_match.group(1))
        else:
            # Alternative: try to extract issue number from the end of the filename
            issue_match = re.search(r'_(\d+)\.pdf$', str(pdf_path), re.IGNORECASE)
            if issue_match:
                issue_number = int(issue_match.group(1))
        
        # Try to extract date from filename
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', pdf_path.stem)
        if date_match:
            date = date_match.group(1)
            # Convert to YYYY/MM/DD format
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                date = date_obj.strftime('%Y/%m/%d')
            except ValueError:
                pass
        
        return issue_number, date
    
    def process_pdfs(self, pdf_dir=None, limit=None, start_date=None, end_date=None, start_issue=None, end_issue=None):
        """
        Process PDFs in a directory to identify ad pages, with filtering options.
        
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
                # Extract metadata
                issue_number, date = self.extract_metadata(pdf_file)
                
                # Analyze PDF to find ad pages
                ad_pages = self.analyze_pdf(pdf_file)
                
                # Add to results
                results.append({
                    "name": pdf_file.name,
                    "issue_number": issue_number,
                    "date": date,
                    "ads_pages": ad_pages
                })
                
                logger.info(f"Found {len(ad_pages)} ad pages in {pdf_file.name}")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {str(e)}")
        
        # Create DataFrame from results
        results_df = pd.DataFrame(results) if results else pd.DataFrame()
        
        # Save to CSV
        if not results_df.empty:
            # Convert ads_pages list to string representation
            results_df['ads_pages'] = results_df['ads_pages'].apply(lambda x: str(x).replace('[', '').replace(']', ''))
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
    Main function to handle command-line arguments and run the ads page extractor.
    """
    print("\nEchorouk Ads Page Extractor")
    print("=========================")
    
    parser = argparse.ArgumentParser(description='Identify ad pages in Echorouk newspaper PDFs')
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
        # Initialize the ads page extractor
        extractor = EchoroukAdsPageExtractor(
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
            print(f"Results saved to {extractor.ads_csv_path}")
            
            # Show sample of results
            print("\nSample of processed PDFs:")
            print(results[['name', 'issue_number', 'date', 'ads_pages']].head())
        else:
            print("\nNo PDFs were processed or no ads were found.")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()