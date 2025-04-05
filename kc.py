"""KC - Chatbot using Google Gemini API

This implementation of KC uses the Google Gemini API to provide chat capabilities
through a Discord bot interface.
"""
from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch, Content, Part
from dotenv import load_dotenv
import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio

# Import utility functions from our library
from utils import generate_and_save_image, send_sectioned_response, keep_typing

load_dotenv()

GOOGLE_KEY = os.getenv("GOOGLE_KEY")
DISCORD_TOKEN = os.getenv("KC_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("KC_CHANNEL_ID"))

# Create images directory if it doesn't exist
IMAGES_DIR = "./images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# Use separate models for text chat and image generation
chat_model_id = "gemini-2.5-pro-exp-03-25"
image_model_id = "imagen-3.0-generate-002"

# Initialize Google Search tool
google_search_tool = Tool(
    google_search = GoogleSearch()
)

# Validate configuration
print("Environment variable check:")
print(f"DISCORD_TOKEN present: {bool(DISCORD_TOKEN)}")
print(f"GOOGLE_KEY present: {bool(GOOGLE_KEY)}")
print(f"TARGET_CHANNEL_ID: {TARGET_CHANNEL_ID}")

# Initialize Discord bot and Google client
bot = commands.Bot(command_prefix="~", intents=discord.Intents.all())
google_client = genai.Client(api_key=GOOGLE_KEY)


@bot.tree.command(name="clear")
@app_commands.describe(limit="Number of messages to delete (default: 100)")
async def clear(interaction: discord.Interaction, limit: int = 100):
    """Clears messages from the current channel."""
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

@bot.tree.command(name="model")
@app_commands.describe(new_model_id="New model ID to use for Gemini API")
async def change_model(interaction: discord.Interaction, new_model_id: str):
    """Changes the Gemini chat model being used."""
    global chat_model_id

    # Check if the user has the required permissions (admin only)
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only administrators can change the model.", ephemeral=True)
        return

    old_model = chat_model_id
    chat_model_id = new_model_id

    await interaction.response.send_message(f"Chat model changed from `{old_model}` to `{new_model_id}`", ephemeral=True)

@bot.tree.command(name="image")
@app_commands.describe(prompt="Description of the image you want to generate")
async def generate_image(interaction: discord.Interaction, prompt: str):
    """Generates an image using Gemini API based on the provided prompt."""
    await interaction.response.defer(thinking=True)

    try:
        image_path = await generate_and_save_image(prompt, google_client, image_model_id)
        await interaction.followup.send(f"Generated image based on: {prompt}", file=discord.File(image_path))
    except Exception as e:
        print(f"Error generating image: {e}")
        await interaction.followup.send(file=discord.File(os.path.join(IMAGES_DIR, "no.jpg")))

@bot.event
async def on_ready():
    """Called when the client is done preparing data received from Discord."""
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    """Handle incoming messages and respond to queries in the target channel."""
    # Always process commands first
    await bot.process_commands(message)

    if message.channel.id == TARGET_CHANNEL_ID:
        if message.author == bot.user:
            return
        if message.content.startswith('!') or message.content.startswith('~'):
            return
        if message.content.strip() == "":
            return

        query = message.content
        print(f"Processing message: '{query[:30]}...' in channel {message.channel.id}")

        # Check if this is an image generation request
        if query.lower().startswith("generate image:") or query.lower().startswith("create image:"):
            # Start continuous typing in the background
            typing_task = asyncio.create_task(keep_typing(message.channel))

            try:
                prompt = query.split(":", 1)[1].strip()
                try:
                    print(f"Generating image for prompt: {prompt[:30]}...")
                    image_path = await generate_and_save_image(prompt, google_client, image_model_id)
                    # Cancel typing before sending the response
                    typing_task.cancel()
                    await message.reply(f"Here's your image:", file=discord.File(image_path))
                except Exception as e:
                    print(f"Error generating image: {e}")
                    # Cancel typing before sending the response
                    typing_task.cancel()
                    await message.reply(file=discord.File(os.path.join(IMAGES_DIR, "no.jpg")))
            except Exception as e:
                # Make sure to cancel the typing task even if an error occurs
                typing_task.cancel()
                print(f"Exception during image generation: {e}")
                raise e
            return

        previous_messages = [msg async for msg in message.channel.history(limit=15)]
        previous_messages.reverse()  # Chronological order

        # Format history for Gemini API
        formatted_history = []
        for msg in previous_messages:
            if msg.author == bot.user:
                role = "model"
            else:
                role = "user"

            formatted_history.append(
                Content(
                    role=role,
                    parts=[Part(text=msg.content)]
                )
            )

        # Ensure history starts with a user message
        if not formatted_history or formatted_history[0].role != "user":
            # If no history or first message is not from a user,
            # we don't send any history to the API
            formatted_history = []

        # Start continuous typing in the background
        typing_task = asyncio.create_task(keep_typing(message.channel))

        try:
            # Create chat in the main thread
            print("Creating Gemini chat")
            chat = google_client.chats.create(
                model=chat_model_id,
                history=formatted_history,
                config=GenerateContentConfig(
                    system_instruction=(
                        "Your name is KC. You are a helpful assistant."
                    ),
                    tools=[google_search_tool],
                    response_modalities=["TEXT"]
                )
            )

            try:
                # Run the API call in a separate thread to prevent blocking the event loop
                print("Sending message to Gemini (non-blocking)")

                # Define a function to run in a separate thread
                def run_gemini_query(chat, query_text):
                    print("Starting Gemini query in separate thread")
                    response = chat.send_message(query_text)
                    print("Gemini query completed in thread")
                    return response

                # Run the function in a separate thread
                response = await asyncio.to_thread(run_gemini_query, chat, query)

                response_content = response.text
                print(f"Got response from Gemini, length: {len(response_content)}")

                # Cancel typing before sending the response
                typing_task.cancel()
                await send_sectioned_response(message, response_content)
                print("Response sent to Discord")
            except Exception as e:
                print(f"Error generating response: {e}")
                # Cancel typing before sending the error message
                typing_task.cancel()
                await message.reply("I'm sorry, I encountered an error while generating a response.")
        except ValueError as e:
            print(f"Error with chat history: {e}")
            # Try again with no history
            chat = google_client.chats.create(
                model=chat_model_id,
                config=GenerateContentConfig(
                    tools=[google_search_tool],
                    response_modalities=["TEXT"]
                )
            )
            try:
                print("Retrying Gemini with no history")

                # Run the API call in a separate thread
                def run_retry_query(chat, query_text):
                    print("Starting retry Gemini query in separate thread")
                    response = chat.send_message(query_text)
                    print("Retry Gemini query completed in thread")
                    return response

                # Run the function in a separate thread
                response = await asyncio.to_thread(run_retry_query, chat, query)

                response_content = response.text
                # Cancel typing before sending the response
                typing_task.cancel()
                await send_sectioned_response(message, response_content)
            except Exception as e:
                print(f"Error generating response (retry): {e}")
                # Cancel typing before sending the error message
                typing_task.cancel()
                await message.reply("I'm sorry, I encountered an error while generating a response.")
        except Exception as e:
            # Make sure to cancel the typing task even if an error occurs
            typing_task.cancel()
            print(f"Exception during Gemini response: {e}")
            raise e

def main():
    """Initialize and run the Discord bot for KC."""
    print("Starting KC with Gemini...")

    try:
        # Run the Discord bot
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("Stopping bot due to keyboard interrupt...")
    except Exception as e:
        print(f"Error running bot: {e}")

if __name__ == "__main__":
    main()
