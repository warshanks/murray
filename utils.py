"""Utility functions for Discord bots using Google Gemini API.

This module provides common functionality for Discord bots interacting with Google Gemini API,
including image generation and message formatting capabilities.
"""
import asyncio
import datetime
import os
import uuid
import re
from io import BytesIO

import discord
from discord import app_commands
from PIL import Image
from google import genai
from google.genai.types import Part, FileData

# Create images directory if it doesn't exist
IMAGES_DIR = "./images"
os.makedirs(IMAGES_DIR, exist_ok=True)

async def keep_typing(channel):
    """Continuously show the typing indicator until the task is cancelled.

    Args:
        channel (discord.TextChannel): The Discord channel to show typing in

    Returns:
        None
    """
    print(f"Starting typing indicator in channel {channel.id}")
    try:
        while True:
            async with channel.typing():  # Use async with context manager
                await asyncio.sleep(5)  # Sleep less than 10 seconds to ensure continuous typing
    except asyncio.CancelledError:
        # Task was cancelled, which is expected
        print(f"Typing indicator cancelled for channel {channel.id}")
        pass
    except Exception as e:
        print(f"Error in keep_typing: {type(e).__name__}: {str(e)}")

async def generate_and_save_image(prompt, google_client, image_model_id):
    """Generate an image using Gemini API and save it to the images directory.

    Args:
        prompt (str): The text description of the image to generate
        google_client (genai.Client): The Google Gemini API client
        image_model_id (str): The model ID to use for image generation

    Returns:
        str: The file path of the saved image

    Raises:
        Exception: If no image was generated or an error occurred
    """
    try:
        response = google_client.models.generate_images(
            model=image_model_id,
            prompt=prompt,
            config=genai.types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9"
            )
        )

        # Create a unique filename with timestamp and UUID
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}.png"
        image_path = os.path.join(IMAGES_DIR, filename)

        # Save the image
        for generated_image in response.generated_images:
            image = Image.open(BytesIO(generated_image.image.image_bytes))
            image.save(image_path)
            return image_path

        # If we get here, no images were generated
        print("ERROR: No images were generated in the response")
        print(f"Full API response: {response}")
        print(f"Response object details: {dir(response)}")
        raise Exception("No image was generated in the response")
    except Exception as e:
        print(f"Exception in image generation: {type(e).__name__}: {str(e)}")
        if "'NoneType' object is not iterable" in str(e):
            print(f"Full API response that caused NoneType error: {response}")
            print(f"Response object details: {dir(response)}")
        if hasattr(e, 'response'):
            print(f"Response in exception: {e.response}")
        raise

async def send_sectioned_response(message, response_content, max_length=1000):
    """Split and send a response in sections if it exceeds Discord's message length limit.

    Args:
        message (discord.Message): The original message to reply to
        response_content (str): The content to send
        max_length (int, optional): Maximum length per message. Defaults to 1000.
    """
    # Split on double newlines to preserve formatting
    sections = response_content.split('\n\n')
    current_section = ""
    messages_to_send = []

    # Prepare all message sections first
    for section in sections:
        # If adding this section would exceed the limit
        if len(current_section) + len(section) + 2 > max_length:
            if current_section:
                messages_to_send.append(current_section.strip())
            current_section = section
        else:
            if current_section:
                current_section += "\n\n" + section
            else:
                current_section = section

    if current_section:
        messages_to_send.append(current_section.strip())

    # Additional safety check - ensure no message exceeds Discord's limit (2000 chars)
    final_messages = []
    for content in messages_to_send:
        # If a single section is still too long, split it further
        if len(content) > 1950:  # Using 1950 for safety margin
            # Split by sentences instead
            sentences = content.replace('. ', '.\n').split('\n')
            temp_section = ""

            for sentence in sentences:
                if len(temp_section) + len(sentence) + 1 > 1950:
                    final_messages.append(temp_section.strip())
                    temp_section = sentence
                else:
                    if temp_section:
                        temp_section += " " + sentence
                    else:
                        temp_section = sentence

            if temp_section:
                final_messages.append(temp_section.strip())
        else:
            final_messages.append(content)

    # Send messages with a delay between each to avoid blocking the event loop
    for i, msg_content in enumerate(final_messages):
        try:
            # Final safety check before sending
            if len(msg_content) > 2000:
                print(f"Warning: Message section {i+1}/{len(final_messages)} is still too long ({len(msg_content)} chars). Trimming...")
                msg_content = msg_content[:1997] + "..."

            # Send first response as a reply, rest as regular messages
            if i == 0:
                await message.reply(msg_content)
            else:
                await message.channel.send(msg_content)

            # Add a small delay between messages to avoid blocking the event loop
            if i < len(final_messages) - 1:
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error sending message section {i+1}/{len(final_messages)}: {e}")
            # If sending fails, try to continue with remaining sections
            continue

def parse_youtube_links(message_text):
    """Parse a message to extract YouTube links and prepare parts for Gemini API.

    This function detects YouTube links in a message and prepares the message
    content as separate parts for the Gemini API (text content and YouTube video).

    Args:
        message_text (str): The message text to parse

    Returns:
        list or str: If YouTube links are found, returns a list of Part objects.
                     If no links are found, returns the original message text.
    """
    # Pattern to match YouTube links
    youtube_pattern = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)(\S*)'
    youtube_match = re.search(youtube_pattern, message_text)

    if youtube_match:
        # If YouTube link is found, extract it
        youtube_url = youtube_match.group(0)
        # Extract text without the URL
        text_content = re.sub(youtube_pattern, '', message_text).strip()

        print(f"YouTube link detected: {youtube_url}")

        # Create parts with both text and YouTube link
        parts = []
        if text_content:
            parts.append(Part(text=text_content))
        parts.append(Part(file_data=FileData(file_uri=youtube_url)))

        return parts
    else:
        # No YouTube links found, return original message
        return message_text

def register_model_command(bot, module_globals):
    """Register the model change command with a Discord bot.

    Args:
        bot (commands.Bot): The Discord bot instance
        module_globals (dict): The globals dictionary from the calling module
    """
    @bot.tree.command(name="model")
    @app_commands.describe(new_model_id="New model ID to use for Gemini API or shorthand ('flash', 'pro')")
    async def change_model(interaction: discord.Interaction, new_model_id: str):
        """Changes the Gemini chat model being used."""
        # Check if the user has the required permissions (admin only)
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can change the model.", ephemeral=True)
            return

        # Handle shorthand model names
        model_mapping = {
            "flash": "gemini-2.0-flash",
            "pro": "gemini-2.5-pro-exp-03-25"
        }

        # Map the shorthand to the full model name if applicable
        actual_model_id = model_mapping.get(new_model_id.lower(), new_model_id)

        old_model = module_globals["chat_model_id"]
        module_globals["chat_model_id"] = actual_model_id

        await interaction.response.send_message(f"Chat model changed from `{old_model}` to `{actual_model_id}`", ephemeral=True)

def register_clear_command(bot, target_channel_id):
    """Register the clear command with a Discord bot.

    Args:
        bot (commands.Bot): The Discord bot instance
        target_channel_id (int): The ID of the channel where message deletion is allowed
    """
    @bot.tree.command(name="clear")
    @app_commands.describe(limit="Number of messages to delete (default: 100)")
    async def clear(interaction: discord.Interaction, limit: int = 100):
        """Clears messages from the bot's designated channel."""
        # Check if this is the target channel
        if interaction.channel.id != target_channel_id:
            await interaction.response.send_message("This command can only be used in the bot's designated channel.", ephemeral=True)
            return

        # Check if the user has the required permissions
        if not interaction.channel.permissions_for(interaction.user).manage_messages:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        # Defer the response to allow for longer processing time
        await interaction.response.defer(ephemeral=True)

        try:
            # Delete messages from the channel
            deleted = await interaction.channel.purge(limit=limit)
            await interaction.followup.send(f"Successfully deleted {len(deleted)} messages.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to delete messages in this channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to delete messages: {str(e)}", ephemeral=True)