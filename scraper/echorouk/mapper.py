import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
from pathlib import Path
import re
import time
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('echorouk_scraper')

class EchoroukScraper:
    """
    Scraper for Echorouk newspaper.
    """
    def __init__(self, output_dir=None):
        """
        Initialize the Echorouk newspaper scraper.
        
        Args:
            output_dir: Directory to save downloaded PDFs
        """
        if output_dir is None:
            output_dir = Path("d:/My Projects/DZAdsSearchEngine/scraper/echorouk/data")
        else:
            output_dir = Path(output_dir)
            
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Base URL for Echorouk newspaper listings
        self.base_url = "https://www.echoroukonline.com/echorouk-yawmi"
        self.listing_url = f"{self.base_url}/page/{{page}}"
        
        # Use simpler headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    
    def get_pagination_range(self):
        """
        Get the pagination range (first page and last page) from the website.
        
        Returns:
            Tuple of (first_page, last_page, latest_date) or (1, None, None) if pagination not found
        """
        try:
            logger.info(f"Fetching pagination range from {self.base_url}")
            
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch pagination: Status code {response.status_code}")
                return (1, None, None)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the latest newspaper date
            latest_date_element = soup.select_one('div.ech-palp__title._nodb a')
            latest_date_text = None
            
            if latest_date_element:
                latest_date_text = latest_date_element.text.strip()
                logger.info(f"Found latest newspaper date: {latest_date_text}")
            else:
                logger.warning("Latest newspaper date not found")
            
            # Find the pagination list
            pagination_ul = soup.select_one('ul.d-f.fxw-w')
            
            if not pagination_ul:
                logger.warning("Pagination list not found")
                return (1, None, latest_date_text)
            
            # Get all list items
            pagination_items = pagination_ul.find_all('li')
            
            if not pagination_items:
                logger.warning("No pagination items found")
                return (1, None, latest_date_text)
            
            # First page is usually 1
            first_page = 1
            
            # Get the last page from the last li element
            last_item = pagination_items[-1]
            last_page_link = last_item.find('a')
            
            if last_page_link and 'href' in last_page_link.attrs:
                # Extract page number from URL
                page_url = last_page_link['href']
                page_match = re.search(r'/page/(\d+)', page_url)
                
                if page_match:
                    last_page = int(page_match.group(1))
                    logger.info(f"Found pagination range: {first_page} to {last_page}")
                    return (first_page, last_page, latest_date_text)
                else:
                    # Try to get the text content
                    last_page_text = last_page_link.text.strip()
                    if last_page_text.isdigit():
                        last_page = int(last_page_text)
                        logger.info(f"Found pagination range: {first_page} to {last_page}")
                        return (first_page, last_page, latest_date_text)
            
            logger.warning("Could not determine last page number")
            return (1, None, latest_date_text)
            
        except Exception as e:
            logger.error(f"Error fetching pagination range: {str(e)}")
            return (1, None, None)

    def fetch_publication_dates(self, start_page=1, max_pages=20):
        """
        Fetch publication dates from the newspaper listing pages.
        
        Args:
            start_page: Page to start fetching from
            max_pages: Maximum number of pages to fetch
            
        Returns:
            List of dictionaries containing date information
        """
        publication_dates = []
        arabic_month_map = {
            'جانفي': 1, 'فيفري': 2, 'مارس': 3, 'أفريل': 4, 'ماي': 5, 'جوان': 6,
            'جويلية': 7, 'أوت': 8, 'سبتمبر': 9, 'أكتوبر': 10, 'نوفمبر': 11, 'ديسمبر': 12
        }
        
        arabic_day_map = {
            'الأحد': 'Sunday', 'الإثنين': 'Monday', 'الثلاثاء': 'Tuesday', 
            'الأربعاء': 'Wednesday', 'الخميس': 'Thursday', 'الجمعة': 'Friday', 'السبت': 'Saturday'
        }
        
        logger.info(f"Starting to fetch publication dates from page {start_page}")
        
        for page in range(start_page, start_page + max_pages):
            try:
                url = self.listing_url.format(page=page)
                logger.info(f"Fetching {url}")
                
                # Reduce delay to avoid timeouts
                delay = random.uniform(1, 2)
                logger.info(f"Waiting {delay:.2f} seconds before next request")
                time.sleep(delay)
                
                # Try with and without headers
                response = requests.get(url, timeout=30)
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch page {page}: Status code {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Let's try different selectors to find the date elements
                date_elements = soup.select('div.ech-pdbl__pdat a')
                
                # If the first selector doesn't work, try alternatives
                if not date_elements:
                    logger.info("Trying alternative selector...")
                    date_elements = soup.select('a[href*="echorouk-yawmi"]')
                
                if not date_elements:
                    logger.warning(f"No date elements found on page {page}")
                    
                    # Debug: Print some of the HTML to see what we're getting
                    logger.info(f"Page content sample: {soup.text[:500]}")
                    break
                
                if not date_elements:
                    logger.warning(f"No date elements found on page {page}")
                    break
                
                for date_element in date_elements:
                    date_text = date_element.text.strip()
                    date_url = date_element['href']
                    
                    # Parse Arabic date format (e.g., "الأحد 16 مارس 2025")
                    try:
                        # Extract components using regex
                        match = re.match(r'(\S+)\s+(\d+)\s+(\S+)\s+(\d+)', date_text)
                        if match:
                            day_name, day, month_name, year = match.groups()
                            
                            # Convert Arabic month name to number
                            if month_name in arabic_month_map:
                                month = arabic_month_map[month_name]
                                
                                # Create date object
                                date_obj = datetime(int(year), month, int(day))
                                
                                publication_dates.append({
                                    'date': date_obj,
                                    'date_text': date_text,
                                    'url': date_url,
                                    'day_name': day_name,
                                    'day_name_en': arabic_day_map.get(day_name, day_name),
                                    'scrape_order': len(publication_dates) + 1  # Add scrape order index
                                })
                            else:
                                logger.warning(f"Unknown month name: {month_name}")
                        else:
                            logger.warning(f"Failed to parse date text: {date_text}")
                    except Exception as e:
                        logger.error(f"Error parsing date '{date_text}': {str(e)}")
                
                logger.info(f"Extracted {len(date_elements)} dates from page {page}")
                
            except Exception as e:
                logger.error(f"Error fetching page {page}: {str(e)}")
                break
        
        # Remove this line completely - we don't want any sorting
        # publication_dates.sort(key=lambda x: x['date'])
        
        logger.info(f"Fetched a total of {len(publication_dates)} publication dates")
        return publication_dates
    
    def save_publication_dates(self, dates, filepath=None):
        """
        Save the list of publication dates to a CSV file.
        
        Args:
            dates: List of publication date dictionaries
            filepath: Path to save the file (default: publication_dates.csv in output_dir)
            
        Returns:
            Path to the saved file
        """
        if filepath is None:
            filepath = self.output_dir / "publication_dates.csv"
        else:
            filepath = Path(filepath)
        
        # Sort dates by issue number in ascending order (oldest first, newest last)
        if any('issue_number' in date_info for date_info in dates):
            sorted_dates = sorted(dates, key=lambda x: x['issue_number'])
            logger.info(f"Sorted dates by issue number (ascending order - oldest first)")
        else:
            # Fallback to sorting by index if issue numbers aren't available
            sorted_dates = sorted(dates, key=lambda x: x['scrape_order'], reverse=True)
            logger.info(f"Issue numbers not available, sorted by scrape order (reversed)")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write CSV header
            header = "index,date,date_text,standard_date"
            if any('issue_number' in date_info for date_info in sorted_dates):
                header += ",issue_number"
            f.write(header + "\n")
            
            # Write data rows with new index based on sorted order
            for i, date_info in enumerate(sorted_dates):
                date = date_info['date']
                # Update index to reflect new sorted order (starting from 1)
                new_index = i + 1
                row = f"{new_index},{date.strftime('%Y-%m-%d')},{date_info['date_text']},{date.strftime('%Y-%m-%d')}"
                if 'issue_number' in date_info:
                    row += f",{date_info['issue_number']}"
                f.write(row + "\n")
        
        logger.info(f"Saved {len(sorted_dates)} publication dates to {filepath} (oldest first by issue number)")
        return filepath

    def get_latest_issue_number(self):
        """
        Get the latest issue number by following a chain of links:
        1. Get the latest newspaper URL
        2. Find the download link on that page
        3. Follow the download link to get to the PDF download page
        4. Extract the issue number from the final PDF URL
        
        Returns:
            int: The latest issue number or None if not found
        """
        try:
            # Step 1: Get the latest newspaper URL
            logger.info("Fetching the main page to find latest issue")
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to fetch main page: Status code {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the latest newspaper link
            latest_issue_link = soup.select_one('div.ech-palp__title._nodb a')
            if not latest_issue_link:
                logger.error("Could not find latest issue link")
                return None
                
            latest_issue_url = latest_issue_link['href']
            latest_issue_date = latest_issue_link.text.strip()
            
            # Make sure the URL is absolute
            if not latest_issue_url.startswith('http'):
                latest_issue_url = f"https://www.echoroukonline.com{latest_issue_url}"
                
            logger.info(f"Latest issue date: {latest_issue_date}")
            logger.info(f"Latest issue URL: {latest_issue_url}")
            
            # Step 2: Access the latest issue page to find the download link
            logger.info(f"Accessing latest issue page")
            response = requests.get(latest_issue_url, headers=self.headers, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to access latest issue page: Status code {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the download link (first link)
            download_link = soup.select_one('a.ech-dwmt__dwlk')
            if not download_link:
                logger.error("Could not find download link on the latest issue page")
                return None
                
            download_url = download_link['href']
            
            # Make sure the URL is absolute
            if not download_url.startswith('http'):
                download_url = f"https://www.echoroukonline.com{download_url}"
                
            logger.info(f"Download URL: {download_url}")
            
            # Step 3: Access the download page to find the PDF download link
            logger.info(f"Accessing download page")
            response = requests.get(download_url, headers=self.headers, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to access download page: Status code {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the PDF download link (second link)
            pdf_download_link = soup.select_one('a.ech-dwmt__dwlk')
            if not pdf_download_link:
                logger.error("Could not find PDF download link")
                return None
                
            pdf_download_url = pdf_download_link['href']
            
            # Make sure the URL is absolute
            if not pdf_download_url.startswith('http'):
                pdf_download_url = f"https://www.echoroukonline.com{pdf_download_url}"
                
            logger.info(f"PDF download URL: {pdf_download_url}")
            
            # Step 4: Follow the PDF download link to get the final PDF URL
            logger.info(f"Following PDF download link to get final URL")
            response = requests.get(pdf_download_url, headers=self.headers, allow_redirects=True, timeout=30)
            
            # The final URL after redirects should contain the issue number
            final_pdf_url = response.url
            logger.info(f"Final PDF URL: {final_pdf_url}")
            
            # Extract the issue number from the URL using regex
            issue_match = re.search(r'/(\d+)\.pdf$', final_pdf_url)
            if issue_match:
                issue_number = int(issue_match.group(1))
                logger.info(f"Extracted issue number: {issue_number}")
                return issue_number
            else:
                logger.error(f"Could not extract issue number from PDF URL: {final_pdf_url}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting latest issue number: {str(e)}")
            return None

def main():
    """
    Main function to handle user input and fetch newspaper dates.
    """
    # Initialize the scraper
    scraper = EchoroukScraper()
    
    print("\nEchorouk Newspaper Date Fetcher")
    print("==============================")
    
    try:
        # Get the latest issue number
        print("\nFetching latest issue number...")
        latest_issue_number = scraper.get_latest_issue_number()
        
        if latest_issue_number:
            print(f"\nLatest issue number: {latest_issue_number}")
        else:
            print("\nCould not determine latest issue number automatically.")
            latest_issue_number = input("Please enter the issue number manually (or press Enter to continue without it): ")
            if latest_issue_number:
                latest_issue_number = int(latest_issue_number)
            else:
                latest_issue_number = None
        
        # Get pagination range and latest date
        first_page, last_page, latest_date = scraper.get_pagination_range()
        
        if latest_date:
            print(f"\nLatest newspaper release: {latest_date}")
        
        if last_page:
            print(f"Available pagination range: Page {first_page} to Page {last_page}")
        else:
            print("Could not determine pagination range. Using default values.")
            last_page = 100  # Default fallback
        
        # Ask for start page with the context of available range
        start_page = int(input(f"\nEnter start page number (1-{last_page}, default: 1): ") or "1")
        
        # Validate start page
        if start_page < 1:
            start_page = 1
            print("Invalid start page. Using page 1.")
        elif start_page > last_page:
            start_page = last_page
            print(f"Start page exceeds maximum. Using page {last_page}.")
        
        # Calculate remaining pages
        remaining_pages = last_page - start_page + 1
        
        # Ask for max pages with context
        max_pages_prompt = f"Enter maximum number of pages to fetch (max {remaining_pages}, default: 20): "
        max_pages = int(input(max_pages_prompt) or min(20, remaining_pages))
        
        # Validate max pages
        if max_pages < 1:
            max_pages = 1
            print("Invalid number of pages. Fetching 1 page.")
        elif max_pages > remaining_pages:
            max_pages = remaining_pages
            print(f"Adjusted to maximum available: {max_pages} pages")
        
        print(f"\nFetching publication dates from page {start_page} to {start_page + max_pages - 1}...")
        dates = scraper.fetch_publication_dates(start_page, max_pages)
        
        if dates:
            print(f"\nFound {len(dates)} publication dates.")
            
            # If we have the latest issue number, we can calculate issue numbers for all dates
            if latest_issue_number:
                print("\nCalculating issue numbers for all dates...")
                # The first date in the list (index 0) corresponds to the latest issue
                for i, date_info in enumerate(dates):
                    # Calculate issue number by subtracting the index from the latest issue number
                    date_info['issue_number'] = latest_issue_number - date_info['scrape_order'] + 1
            
            # Display some sample dates
            print("\nSample dates:")
            for i, date_info in enumerate(dates[:5]):
                issue_str = f" - Issue: {date_info.get('issue_number', 'N/A')}" if 'issue_number' in date_info else ""
                print(f"Index: {date_info['scrape_order']} - {date_info['date'].strftime('%Y-%m-%d')} - {date_info['date_text']}{issue_str}")
            
            # Automatically save to default location without asking
            saved_path = scraper.save_publication_dates(dates)
            print(f"\nSaved publication dates to {saved_path}")
        else:
            print("No publication dates found.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()