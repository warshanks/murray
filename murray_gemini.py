"""Murray - F1 information bot using Google Gemini API

This implementation of Murray uses the Google Gemini API to provide F1-related information
through a Discord bot interface. Named after legendary F1 commentator Murray Walker.
Also supports image generation capabilities.
"""
from google import genai
from dotenv import load_dotenv
import os

# Import utility functions from our library
from utils import run_bot, initialize_bot, register_model_command, register_clear_command, register_generic_on_message_handler

load_dotenv()

GOOGLE_KEY = os.getenv("GOOGLE_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))

# Create images directory if it doesn't exist
IMAGES_DIR = "./images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# Use separate models for text chat and image generation
chat_model_id = "gemini-2.5-pro-exp-03-25"
image_model_id = "imagen-3.0-generate-002"

# Initialize Google client
google_client = genai.Client(api_key=GOOGLE_KEY)

def main():
    """Initialize and run the Discord bot for Murray."""
    # Initialize bot and tools
    bot, genai_client, google_search_tool = initialize_bot(
        bot_name="Murray",
        discord_token=DISCORD_TOKEN,
        google_key=GOOGLE_KEY,
        target_channel_id=TARGET_CHANNEL_ID,
        google_client=google_client,
        chat_model_id=chat_model_id,
        image_model_id=image_model_id
    )

    # Register model change command
    register_model_command(bot, globals())

    # Register clear command
    register_clear_command(bot, TARGET_CHANNEL_ID)

    # Murray-specific system instruction
    system_instruction = (
        "Your name is Murray, you are named after legendary F1 commentator Murray Walker. "
        "You are knowledgeable about F1 and you can answer questions about it."
    )

    # Register message handler
    register_generic_on_message_handler(
        bot=bot,
        target_channel_id=TARGET_CHANNEL_ID,
        google_client=google_client,
        chat_model_id=chat_model_id,
        image_model_id=image_model_id,
        system_instruction=system_instruction,
        google_search_tool=google_search_tool
    )

    # Run the bot
    run_bot(bot, DISCORD_TOKEN, bot_name="Murray")

if __name__ == "__main__":
    main()
