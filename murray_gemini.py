from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch, Content, Part
from dotenv import load_dotenv
import os
import discord
from discord.ext import commands
from discord import app_commands

load_dotenv()

GOOGLE_KEY = os.getenv("GOOGLE_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))

model_id = "gemini-2.5-pro-exp-03-25"
google_search_tool = Tool(
    google_search = GoogleSearch()
)

# Validate configuration
print("Environment variable check:")
print(f"DISCORD_TOKEN present: {bool(DISCORD_TOKEN)}")
print(f"GOOGLE_KEY present: {bool(GOOGLE_KEY)}")
print(f"TARGET_CHANNEL_ID: {TARGET_CHANNEL_ID}")

bot = commands.Bot(command_prefix="~", intents=discord.Intents.all())
google_client = genai.Client(api_key=GOOGLE_KEY)

# Add app commands to the bot
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
    """Changes the Gemini model being used."""
    global model_id

    # Check if the user has the required permissions (admin only)
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only administrators can change the model.", ephemeral=True)
        return

    old_model = model_id
    model_id = new_model_id

    await interaction.response.send_message(f"Model changed from `{old_model}` to `{new_model_id}`", ephemeral=True)

@bot.event
async def on_ready():
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
        print(f"{message.author}: {message.content}")

        previous_messages = [msg async for msg in message.channel.history(limit=15)]
        previous_messages.reverse()

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

        chat = google_client.chats.create(
            model=model_id,
            history=formatted_history,
            config=GenerateContentConfig(
                tools=[google_search_tool],
                response_modalities=["TEXT"]
            )
        )

        async with message.channel.typing():
            try:
                response = chat.send_message(query)
                response_content = response.text
                await send_sectioned_response(message, response_content)
            except Exception as e:
                print(f"Error generating response: {e}")
                await message.reply("I'm sorry, I encountered an error while generating a response.")


async def send_sectioned_response(message, response_content, max_length=1999):
    """Split and send a response in sections if it exceeds Discord's message length limit."""
    # Split on double newlines to preserve formatting
    sections = response_content.split('\n\n')
    current_section = ""

    for i, section in enumerate(sections):
        # If adding this section would exceed the limit
        if len(current_section) + len(section) + 2 > max_length:
            if current_section:
                try:
                    await message.reply(current_section.strip())
                except Exception as e:
                    print(f"Error sending section: {e}")
            current_section = section
        else:
            if current_section:
                current_section += "\n\n" + section
            else:
                current_section = section

    if current_section:
        try:
            await message.reply(current_section.strip())
        except Exception as e:
            print(f"Error sending final section: {e}")

def main():
    """Initialize and run the Discord bot for Murray."""
    print("Starting Murray...")

    try:
        # Run the Discord bot
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("Stopping bot due to keyboard interrupt...")
    except Exception as e:
        print(f"Error running bot: {e}")

if __name__ == "__main__":
    main()
