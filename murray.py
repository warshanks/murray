"""Simplified Murray using Perplexity API"""
import os
import re
import discord
import aiohttp
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
PERPLEXITY_MODEL = os.getenv('PERPLEXITY_MODEL', 'sonar-reasoning')
PERPLEXITY_API_URL = os.getenv('PERPLEXITY_API_URL', 'https://api.perplexity.ai/chat/completions')
TARGET_CHANNEL_ID = int(os.getenv('TARGET_CHANNEL_ID'))  # Convert to integer
SHOW_THINKING = os.getenv('SHOW_THINKING', 'false').lower() == 'true'  # Default to false

# Validate configuration
print("Environment variable check:")
print(f"DISCORD_TOKEN present: {bool(DISCORD_TOKEN)}")
print(f"PERPLEXITY_API_KEY present: {bool(PERPLEXITY_API_KEY)}")
print(f"PERPLEXITY_MODEL: {PERPLEXITY_MODEL}")
print(f"PERPLEXITY_API_URL: {PERPLEXITY_API_URL}")
print(f"TARGET_CHANNEL_ID: {TARGET_CHANNEL_ID}")
print(f"SHOW_THINKING: {SHOW_THINKING}")

bot = commands.Bot(command_prefix='~', intents=discord.Intents.all())

# Add event handlers to the bot
@bot.event
async def on_ready():
    """Called when the client is done preparing data received from Discord."""
    print(f'Logged in as {bot.user}')

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

        # Get conversation history
        previous_messages = [msg async for msg in message.channel.history(limit=10)]
        previous_messages.reverse()  # Chronological order

        async with message.channel.typing():
            response, thinking = await query_perplexity(query, previous_messages)

            # Send thinking content first if available and enabled
            if thinking and SHOW_THINKING:
                thinking_msg = f"**Thinking process:**\n\n{thinking}"
                await send_sectioned_response(message, thinking_msg)

            # Then send the main response
            await send_sectioned_response(message, response)

async def query_perplexity(query, previous_messages=None):
    """Query the Perplexity API with the given message and return the response."""
    url = PERPLEXITY_API_URL

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    # Initialize messages with system message
    messages = [
        {
            "role": "system",
            "content": "You are Murray, a helpful expert knowledgeable in F1. Provide informative, accurate, and concise responses about F1."
        }
    ]

    # Process conversation history if provided
    if previous_messages:
        # Create properly alternating user/assistant messages
        current_role = None
        temp_messages = []

        for prev_msg in previous_messages:
            # Skip commands and empty messages
            if (prev_msg.content.startswith('!') or
                prev_msg.content.startswith('~') or
                prev_msg.content.strip() == ""):
                continue

            role = 'assistant' if prev_msg.author.bot else 'user'

            # If we have two consecutive messages with the same role, we need to skip one
            # to maintain the alternating pattern
            if role == current_role:
                continue

            current_role = role
            temp_messages.append({
                "role": role,
                "content": prev_msg.content
            })

        # Ensure we end with a user message (the current query)
        if temp_messages and temp_messages[-1]["role"] == "user":
            # If the last message is already from a user, replace it with the current query
            temp_messages[-1]["content"] = query
        else:
            # Otherwise add the current query as a user message
            temp_messages.append({
                "role": "user",
                "content": query
            })

        # The message array must start with system, then user
        # If first non-system message is assistant, we need to remove it
        if temp_messages and temp_messages[0]["role"] == "assistant":
            temp_messages = temp_messages[1:]

        # Make sure we have proper alternating user/assistant messages
        filtered_messages = []
        for i, msg in enumerate(temp_messages):
            if i == 0 and msg["role"] != "user":
                continue  # First message must be from user
            if i > 0 and msg["role"] == filtered_messages[-1]["role"]:
                continue  # Skip consecutive messages with same role
            filtered_messages.append(msg)

        # Add filtered messages to our message array
        messages.extend(filtered_messages)
    else:
        # If no conversation history, just add the current query
        messages.append({
            "role": "user",
            "content": query
        })

    payload = {
        "model": PERPLEXITY_MODEL,
        "messages": messages,
        "return_images": False,
        "return_related_questions": False,
        "stream": False,
        "presence_penalty": 0,
        "frequency_penalty": 1,
        "web_search_options": {"search_context_size": "medium"}
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=300) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return f'API error: Status {response.status}, Details: {error_text}', None

                json_response = await response.json()

                # Extract the response content from Perplexity API response
                text_response = json_response.get('choices', [{}])[0].get('message', {}).get('content', 'No response content')

                # Extract thinking content if present
                thinking_content = None
                thinking_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
                thinking_match = thinking_pattern.search(text_response)

                # Check if there's a complete <think>...</think> pair
                if thinking_match:
                    thinking_content = thinking_match.group(1).strip()
                    # Remove the thinking content from the main response
                    text_response = thinking_pattern.sub('', text_response)
                else:
                    # Check for orphaned <think> tag without closing tag
                    orphaned_tag = re.search(r'<think>', text_response)
                    if orphaned_tag:
                        # Remove the orphaned tag from the text
                        text_response = text_response.replace('<think>', '')

                # Remove any triple or more newlines
                text_response = re.sub(r'\n{3,}', '\n\n', text_response)

                # Fix formatting for year comparisons
                text_response = re.sub(r'(\*\*\d{4}:\*\*.*?)(?=\s*\*\*\d{4}:|$)', r'\1\n', text_response)

                # Ensure proper indentation and spacing for bullet points
                text_response = re.sub(r'(?m)^(\s*)-\s*', r'   - ', text_response)
                return text_response.strip(), thinking_content

    except aiohttp.ClientResponseError as e:
        return f'HTTP error occurred: {e}', None
    except aiohttp.ClientError as e:
        return f'Connection error: {e}', None
    except Exception as e:
        return f'Error: {e}', None

async def send_sectioned_response(message, response_content, max_length=2000):
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
    print("Starting Murray Discord bot...")
    print(f"Show thinking content: {SHOW_THINKING}")

    try:
        # Run the Discord bot
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("Stopping bot due to keyboard interrupt...")
    except Exception as e:
        print(f"Error running bot: {e}")

if __name__ == "__main__":
    main()
