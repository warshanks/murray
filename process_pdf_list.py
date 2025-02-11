"""Script for processing a list of PDF URLs in batches."""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import requests
from dotenv import load_dotenv
from upload_documents import (process_new_documents, move_files_to_folder,
                            update_workspace_embeddings)

# Load environment variables from .env file
load_dotenv()

# Configuration
DOWNLOAD_DIRECTORY = "documents"
BATCH_SIZE = 10
ANYTHINGLLM_WORKSPACE = os.getenv('ANYTHINGLLM_WORKSPACE')

class PDFDownloader:
    """Simple PDF downloader that tracks downloaded files."""

    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.download_dir / 'download_history.json'
        self.downloaded_docs = self._load_history()
        self.session = requests.Session()

    def _load_history(self) -> Dict:
        """Load the download history from JSON file."""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_history(self) -> None:
        """Save the current download history to JSON file."""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.downloaded_docs, f, indent=2)

    def _clean_filename(self, filename: str) -> str:
        """Clean filename to remove special characters and shorten if needed."""
        # Replace URL encoding with spaces
        filename = filename.replace('%20', ' ')

        # Remove any remaining special characters
        filename = re.sub(r'[^\w\s-]', '', filename)

        # Replace multiple spaces with single space
        filename = re.sub(r'\s+', ' ', filename)

        # Truncate if too long (leaving room for .pdf extension)
        if len(filename) > 100:
            filename = filename[:96] + '...'

        return filename.strip() + '.pdf'

    def is_downloaded(self, url: str) -> bool:
        """Check if a URL has already been downloaded."""
        return url in self.downloaded_docs

    def download(self, url: str) -> Path | None:
        """Download a PDF and save it to the download directory."""
        if self.is_downloaded(url):
            print(f"Already downloaded: {url.split('/')[-1]}")
            return None

        try:
            response = self.session.get(url)
            response.raise_for_status()

            # Create a safe filename from the URL
            original_filename = url.split('/')[-1].replace('.pdf', '')
            clean_filename = self._clean_filename(original_filename)
            filepath = self.download_dir / clean_filename

            # Save the PDF
            with open(filepath, 'wb') as f:
                f.write(response.content)

            # Update history
            self.downloaded_docs[url] = {
                'filename': clean_filename,
                'original_filename': original_filename + '.pdf',
                'downloaded_at': datetime.now().isoformat()
            }
            self._save_history()

            print(f"Downloaded: {clean_filename}")
            return filepath

        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return None

def process_batch(urls: List[str], downloader: PDFDownloader) -> None:
    """
    Process a batch of PDF URLs.

    Args:
        urls: List of URLs to process
        downloader: PDFDownloader instance to use for downloading
    """
    new_docs = []

    for url in urls:
        result = downloader.download(url)
        if result is not None:
            new_docs.append(result)

    if new_docs:
        print(f"\nUploading {len(new_docs)} new documents to AnythingLLM...")
        # Upload new documents
        uploaded_files = process_new_documents(new_docs)
        if uploaded_files:
            # Move files to murray folder
            moved_files = move_files_to_folder(uploaded_files, "murray")
            if moved_files:
                # Update workspace embeddings
                update_workspace_embeddings(ANYTHINGLLM_WORKSPACE, moved_files)
    else:
        print("No new documents to process in this batch")

def main():
    """Process PDF URLs from the list file in batches."""
    url_list_file = 'reference/pdf_links.txt'

    if not os.path.exists(url_list_file):
        print(f"Error: {url_list_file} not found")
        return

    # Initialize downloader
    downloader = PDFDownloader(DOWNLOAD_DIRECTORY)

    # Read URLs from file
    with open(url_list_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    total_urls = len(urls)
    total_batches = (total_urls + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Found {total_urls} URLs to process in {total_batches} batches")

    # Process in batches
    for i in range(0, total_urls, BATCH_SIZE):
        current_batch = i // BATCH_SIZE + 1
        batch = urls[i:i + BATCH_SIZE]
        print(f"\n[Batch {current_batch}/{total_batches}] Processing URLs {i + 1} to {min(i + BATCH_SIZE, total_urls)}")
        process_batch(batch, downloader)

        # Show progress
        processed = min(i + BATCH_SIZE, total_urls)
        percent_done = (processed / total_urls) * 100
        print(f"Overall progress: {processed}/{total_urls} ({percent_done:.1f}%)")

    print("\nFinished processing all batches!")

if __name__ == "__main__":
    main()