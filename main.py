"""Main module for running the FIA F1 Document Monitor and Discord bot."""

import argparse
import os
import re
import time
import asyncio
import threading
from datetime import datetime
import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv
from scraper import Scraper
from upload_documents import (process_new_documents, move_files_to_folder,
                              update_workspace_embeddings, upload_documents)

# Configuration variables
FIA_DOCUMENTS_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2024-2043"
DOWNLOAD_DIRECTORY = "documents"
CHECK_INTERVAL_SECONDS = 300  # 5 minutes

# Load environment variables from .env file
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
ANYTHINGLLM_API_KEY = os.getenv('ANYTHINGLLM_API_KEY')
ANYTHINGLLM_ENDPOINT = os.getenv('ANYTHINGLLM_ENDPOINT')
ANYTHINGLLM_WORKSPACE = os.getenv('ANYTHINGLLM_WORKSPACE')
TARGET_CHANNEL_ID = int(os.getenv('TARGET_CHANNEL_ID'))  # Convert to integer
print(f"TARGET_CHANNEL_ID: {TARGET_CHANNEL_ID}")

bot = commands.Bot(command_prefix='~', intents=discord.Intents.all())

def monitor_documents(url: str, download_dir: str, interval: int = 300):
    """
    Monitor the FIA documents page for new documents and download them.
    
    Args:
        url: The URL to monitor
        download_dir: Directory to save downloaded documents
        interval: Time between checks in seconds (default: 300 seconds / 5 minutes)
    """
    scraper = Scraper(url, download_dir)
    print(f"Monitoring {url} for new documents...")
    print(f"Downloads will be saved to: {download_dir}")
    print(f"Checking every {interval} seconds")

    while True:
        try:
            documents = scraper.fetch_documents()
            new_docs = []
            for doc in documents:
                if not scraper.is_document_downloaded(doc):
                    print(f"\nNew document found: {doc.title}")
                    print(f"Published: {doc.published}")
                    result = scraper.download_document(doc)
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
                current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                print(f"No new documents found at {current_time}")

        except Exception as e:
            print(f"\nError: {e}")

        time.sleep(interval)

class MurrayClient(discord.Client):
    """Discord client for handling F1 document queries and responses."""

    async def on_ready(self):
        """Called when the client is done preparing data received from Discord."""
        print(f'\nLogged in as {self.user}')

    async def on_message(self, message):
        """Handle incoming messages and respond to queries in the target channel."""
        if message.channel.id == TARGET_CHANNEL_ID:
            if message.author == self.user:
                return
            if message.content.startswith('!'):
                return
            if message.content.strip() == "":
                return
            print(f"Received message in channel {message.channel.id}"
                  f"from {message.author}: {message.content}")
            query = message.content
            async with message.channel.typing():
                response = self.query_anythingllm(query)
                await send_sectioned_response(message, response)

    def query_anythingllm(self, query):
        """Query the AnythingLLM API with the given message and return the response."""
        headers = {
            'Authorization': f'Bearer {ANYTHINGLLM_API_KEY}',
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        data = {
            'message': query,
            'mode': 'chat'
        }
        response = requests.post(ANYTHINGLLM_ENDPOINT, headers=headers, json=data, timeout=30)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            return f'HTTP error occurred: {e}'
        print("Raw response content:", response.content)
        try:
            json_response = response.json()
            text_response = json_response.get('textResponse', 'No textResponse field in JSON')
            
            # First, properly handle the escaped newlines
            text_response = text_response.replace('\\n', '\n')
            
            # Remove any triple or more newlines
            text_response = re.sub(r'\n{3,}', '\n\n', text_response)
            
            # Fix formatting for year comparisons
            text_response = re.sub(r'(\*\*\d{4}:\*\*.*?)(?=\s*\*\*\d{4}:|$)', r'\1\n', text_response)
            
            # Ensure proper indentation and spacing for bullet points
            text_response = re.sub(r'(?m)^(\s*)-\s*', r'   - ', text_response)
            
            return text_response.strip()
        except requests.exceptions.JSONDecodeError:
            return 'Failed to parse JSON response from anythingLLM'

async def send_sectioned_response(message, response_content, max_length=2000):
    """Split and send a response in sections if it exceeds Discord's message length limit."""
    # Split on double newlines to preserve formatting
    sections = response_content.split('\n\n')
    current_section = ""
    
    for section in sections:
        # If adding this section would exceed the limit
        if len(current_section) + len(section) + 2 > max_length:
            if current_section:
                await message.reply(current_section.strip())
            current_section = section
        else:
            if current_section:
                current_section += "\n\n" + section
            else:
                current_section = section
    
    if current_section:
        await message.reply(current_section.strip())

def main():
    """Initialize and run the FIA F1 Document Monitor and Discord bot."""
    parser = argparse.ArgumentParser(description="FIA F1 Document Monitor")
    parser.add_argument(
        "--url",
        default=FIA_DOCUMENTS_URL,
        help="URL to monitor for documents"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=CHECK_INTERVAL_SECONDS,
        help=f"Time between checks in seconds (default: {CHECK_INTERVAL_SECONDS})"
    )

    args = parser.parse_args()

    # Process any existing documents that haven't been uploaded yet
    print("Checking for existing documents that need to be uploaded...")
    uploaded_files = upload_documents(DOWNLOAD_DIRECTORY)
    if uploaded_files:
        print(f"Found and processed {len(uploaded_files)} existing documents")
        # Move files to murray folder
        moved_files = move_files_to_folder(uploaded_files, "murray")
        if moved_files:
            # Update workspace embeddings
            update_workspace_embeddings(ANYTHINGLLM_WORKSPACE, moved_files)
    else:
        print("No existing documents need to be uploaded")

    # Set up Discord bot
    intents = discord.Intents.all()
    client = MurrayClient(intents=intents)

    try:
        # Run both the document monitor and Discord bot
        async def start_services():
            print("\nStarting document monitor...")
            # Start document monitoring in a separate thread
            monitor_thread = threading.Thread(
                target=monitor_documents,
                args=(args.url, DOWNLOAD_DIRECTORY, args.interval),
                daemon=True
            )
            monitor_thread.start()

            # Start Discord bot and keep it running
            print("Starting Discord bot...")
            await client.start(DISCORD_TOKEN)

        # Run everything
        asyncio.run(start_services())
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        asyncio.run(client.close())


if __name__ == "__main__":
    main()
