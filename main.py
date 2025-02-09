# Configuration variables
FIA_DOCUMENTS_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2024-2043"
DOWNLOAD_DIRECTORY = "documents"
CHECK_INTERVAL_SECONDS = 300  # 5 minutes

import argparse
import re
import time
import discord
import requests
from discord.ext import commands
from pathlib import Path
from scraper import Scraper
from dotenv import load_dotenv
import os


# Load environment variables from .env file
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
ANYTHINGLLM_API_KEY = os.getenv('ANYTHINGLLM_API_KEY')
ANYTHINGLLM_ENDPOINT = os.getenv('ANYTHINGLLM_ENDPOINT')
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
            new_docs = False
            
            for doc in documents:
                if not scraper.is_document_downloaded(doc):
                    new_docs = True
                    print(f"\nNew document found: {doc.title}")
                    print(f"Published: {doc.published}")
                    scraper.download_document(doc)
            
            if not new_docs:
                print(".", end="", flush=True)
                
        except Exception as e:
            print(f"\nError: {e}")
        
        time.sleep(interval)

class MurrayClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        print(f'\nLogged in as {self.user}')

    async def on_message(self, message):
        print(f"Received message in channel {message.channel.id} from {message.author}: {message.content}")
        if message.channel.id == TARGET_CHANNEL_ID:
            if message.author == self.user:
                return
            if message.content.startswith('!'):
                return
            query = message.content
            async with message.channel.typing():
                response = self.query_anythingllm(query)
                await send_sectioned_response(message, response)

    def query_anythingllm(self, query):
        headers = {
            'Authorization': f'Bearer {ANYTHINGLLM_API_KEY}',
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        data = {
            'message': query,
            'mode': 'chat'
        }
        response = requests.post(ANYTHINGLLM_ENDPOINT, headers=headers, json=data)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            return f'HTTP error occurred: {e}'
        print("Raw response content:", response.content)
        try:
            json_response = response.json()
            return json_response.get('textResponse', 'No textResponse field in JSON')
        except requests.exceptions.JSONDecodeError:
            return 'Failed to parse JSON response from anythingLLM'

async def send_sectioned_response(message, response_content, max_length=2000):
    sentences = re.split(r'(?<=[.!?])\s+', response_content)
    section = ""
    for sentence in sentences:
        if len(section) + len(sentence) + 1 > max_length:
            await message.reply(section.strip())
            section = ""
        section += " " + sentence
    if section:
        await message.reply(section.strip()) 

def main():
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

    # Set up Discord bot
    intents = discord.Intents.all()
    client = MurrayClient(intents=intents)

    try:
        # Run both the document monitor and Discord bot
        import asyncio
        
        async def start_services():
            print("Starting document monitor...")
            # Start document monitoring in a separate thread
            import threading
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