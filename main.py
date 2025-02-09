import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import json
import hashlib
from datetime import datetime
from pathlib import Path

# Configuration variables
TARGET_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2024-2043"
CHECK_INTERVAL = 10  # Time between checks in seconds
DEFAULT_DOWNLOAD_FOLDER = 'documents'  # Default folder to store downloaded files

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

class F1DocumentScraper:
    def __init__(self, url, download_folder=DEFAULT_DOWNLOAD_FOLDER):
        self.url = url
        self.download_folder = download_folder
        self.history_file = os.path.join(download_folder, '.download_history.json')
        self.downloaded_files = self._load_download_history()
        self._setup_download_folder()

    def _setup_download_folder(self):
        """Create download folder if it doesn't exist"""
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
            logging.info(f"Created download folder: {self.download_folder}")

    def _load_download_history(self):
        """Load the history of downloaded files"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return set(json.load(f))
            except json.JSONDecodeError:
                logging.error("Error reading download history, starting fresh")
                return set()
        return set()

    def _save_download_history(self):
        """Save the current download history"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(list(self.downloaded_files), f)
        except Exception as e:
            logging.error(f"Error saving download history: {e}")

    def _get_page_content(self):
        """Fetch the webpage content"""
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logging.error(f"Error fetching page: {e}")
            return None

    def _extract_pdf_links(self, html_content):
        """Extract PDF links from the page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        pdf_links = []
        
        # Find all links that end with .pdf
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.lower().endswith('.pdf'):
                full_url = urljoin(self.url, href)
                pdf_links.append(full_url)
        
        return pdf_links

    def _get_file_info(self, pdf_url):
        """Get file information including name, size, and hash if needed"""
        try:
            response = requests.head(pdf_url)
            filename = pdf_url.split('/')[-1]
            size = response.headers.get('content-length')
            
            # Basic identifier using filename and size
            file_id = f"{filename}:{size}"
            
            # If we have an existing file with this name, compute its hash
            existing_file = os.path.join(self.download_folder, filename)
            if os.path.exists(existing_file):
                with open(existing_file, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                file_id = f"{filename}:{size}:{file_hash}"
            
            return {
                'filename': filename,
                'size': size,
                'file_id': file_id
            }
        except requests.RequestException:
            # Fallback to just filename if we can't get size
            return {
                'filename': pdf_url.split('/')[-1],
                'size': None,
                'file_id': pdf_url.split('/')[-1]
            }

    def _download_pdf(self, pdf_url):
        """Download a PDF file"""
        try:
            file_info = self._get_file_info(pdf_url)
            filename = os.path.join(self.download_folder, file_info['filename'])
            
            # Skip if already downloaded and unchanged
            if file_info['file_id'] in self.downloaded_files:
                logging.info(f"File already exists and unchanged: {filename}")
                return False

            # Download the file
            response = requests.get(pdf_url, stream=True)
            response.raise_for_status()

            # Save the file
            with open(filename, 'wb') as f:
                content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        content += chunk
                        f.write(chunk)
                
                # Calculate hash of the downloaded content
                content_hash = hashlib.md5(content).hexdigest()
                final_file_id = f"{file_info['filename']}:{len(content)}:{content_hash}"
            
            self.downloaded_files.add(final_file_id)
            self._save_download_history()
            logging.info(f"Successfully downloaded: {filename}")
            return True

        except requests.RequestException as e:
            logging.error(f"Error downloading {pdf_url}: {e}")
            return False

    def run(self):
        """Main scraping process"""
        logging.info(f"Starting scrape of {self.url}")
        
        html_content = self._get_page_content()
        if not html_content:
            return

        pdf_links = self._extract_pdf_links(html_content)
        logging.info(f"Found {len(pdf_links)} PDF links")

        new_downloads = 0
        for pdf_url in pdf_links:
            if self._download_pdf(pdf_url):
                new_downloads += 1

        logging.info(f"Scraping complete. Downloaded {new_downloads} new files")

def main():
    scraper = F1DocumentScraper(TARGET_URL)
    
    try:
        while True:
            scraper.run()
            logging.info(f"Waiting {CHECK_INTERVAL} seconds before next check...")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logging.info("Scraper stopped by user")

if __name__ == "__main__":
    main()
