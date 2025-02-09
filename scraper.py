import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
from pathlib import Path


@dataclass
class Document:
    title: str
    url: str
    published: datetime

    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'url': self.url,
            'published': self.published.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Document':
        return cls(
            title=data['title'],
            url=data['url'],
            published=datetime.fromisoformat(data['published'])
        )


class Scraper:
    def __init__(self, base_url: str, download_dir: str):
        self.base_url = base_url
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.history_file = self.download_dir / 'download_history.json'
        self.downloaded_docs = self._load_history()

    def _load_history(self) -> Dict[str, Dict]:
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_history(self) -> None:
        with open(self.history_file, 'w') as f:
            json.dump(self.downloaded_docs, f, indent=2)

    def fetch_documents(self) -> List[Document]:
        """Fetch all documents from the current Grand Prix."""
        response = self.session.get(self.base_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        documents = []
        
        # Find the event wrapper containing all Grand Prix events
        event_wrapper = soup.find('ul', class_='event-wrapper')
        if not event_wrapper:
            return []

        # Find the active (current) Grand Prix
        for event in event_wrapper.find_all('li'):
            active_title = event.find(class_='event-title active')
            if active_title:
                # Process documents under the active Grand Prix
                for doc_row in event.find_all('li', class_='document-row'):
                    title = doc_row.find(class_='title').get_text(strip=True)
                    relative_url = doc_row.find('a')['href']
                    published_str = doc_row.find(class_='published').find(class_='date-display-single').get_text(strip=True)

                    full_url = f"https://www.fia.com{relative_url}"

                    try:
                        published = datetime.strptime(published_str, '%d.%m.%y %H:%M')
                    except ValueError as e:
                        print(f"Error parsing date {published_str}: {e}")
                        continue

                    doc = Document(
                        title=title,
                        url=full_url,
                        published=published
                    )
                    documents.append(doc)

                # Stop after processing the active Grand Prix
                break

        if not documents:
            raise ValueError("No documents found for the current Grand Prix")

        # Sort documents by publication date, newest first
        return sorted(documents, key=lambda x: x.published, reverse=True)

    def is_document_downloaded(self, doc: Document) -> bool:
        return doc.url in self.downloaded_docs

    def download_document(self, doc: Document) -> None:
        if self.is_document_downloaded(doc):
            print(f"Document already downloaded: {doc.title}")
            return

        response = self.session.get(doc.url)
        response.raise_for_status()

        # Create a safe filename
        safe_title = "".join(c for c in doc.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = self.download_dir / f"{safe_title}.pdf"

        # Create a file to save the PDF
        with open(filename, 'wb') as f:
            f.write(response.content)

        # Update history
        self.downloaded_docs[doc.url] = doc.to_dict()
        self._save_history()
        print(f"Downloaded: {filename}") 