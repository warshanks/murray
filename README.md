# Murray

Murray is an AI-powered Discord bot that answers questions about Formula 1. Named in honor of Murray Walker, this bot provides intelligent answers to F1-related questions using either the Perplexity API or Google's Gemini API.

## Features 🌟

- **Intelligent F1 Q&A**: Provides knowledgeable answers about F1 history, regulations, teams, drivers, and more
- **Discord Integration**: Seamlessly integrates with Discord for easy access to F1 information
- **Context-Aware Conversations**: Maintains conversation history for more coherent dialogue
- **Smart Response Formatting**: Handles long responses by breaking them into sections
- **Multiple AI Options**: Choose between Perplexity API or Google's Gemini API implementations
- **Image Generation**: With the Gemini implementation, generate images on request

## Prerequisites 📋

- Python 3.8 or higher
- Discord Bot Token (from [Discord Developer Portal](https://discord.com/developers/applications))
- Either a Perplexity API key or a Google API key for Gemini
- Discord Server with a designated channel for the bot

## Installation 🔧

1. Clone the repository:
```bash
git clone https://github.com/warshanks/murray.git
cd murray
```

2. Set up a virtual environment (recommended):
```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following configuration:

For Perplexity implementation:
```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token
TARGET_CHANNEL_ID=your_channel_id

# Perplexity Configuration
PERPLEXITY_API_KEY=your_perplexity_api_key
PERPLEXITY_MODEL=sonar-reasoning # Models from: https://docs.perplexity.ai/guides/model-cards
SHOW_THINKING=false  # Optional: Set to display thinking process in Discord
```

For Gemini implementation:
```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token
TARGET_CHANNEL_ID=your_channel_id

# Google Configuration
GOOGLE_KEY=your_google_api_key
```

## Usage 🚀

1. Make sure your virtual environment is activated:
```bash
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

2. Start the bot with your preferred implementation:

For Perplexity:
```bash
python murray_perplexity.py
```

For Gemini:
```bash
python murray_gemini.py
```

3. Interact with the bot in your Discord channel:
   - Simply ask questions about F1
   - For Gemini implementation, you can generate images with "generate image: [description]" or "create image: [description]"
   - Use the `/clear` command to delete messages in the channel (requires permissions)
   - With Gemini, use the `/model` command to change the model (admin only)

## Project Structure 📁

- `murray_perplexity.py`: Murray implementation using Perplexity API
- `murray_gemini.py`: Murray implementation using Google's Gemini API
- `images/`: Directory for storing generated images (Gemini implementation)
- `requirements.txt`: Python dependencies

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

