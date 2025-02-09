# Murray

Murray is an AI-powered Discord bot that monitors and analyzes official FIA Formula 1 documents in real-time. Named in honor of Murray Walker, this bot answers questions by providing intelligent answers to questions about F1 regulations, decisions, and technical documents.

## Features 🌟

- **Real-time Document Monitoring**: Automatically fetches and processes new FIA documents as they're published
- **Intelligent Q&A**: Uses AnythingLLM to provide context-aware answers about F1 regulations and decisions
- **Discord Integration**: Seamlessly integrates with Discord for easy access to F1 document insights
- **Document Management**: Automatically organizes, vectorizes and embeds new documents for quick retrieval
- **Smart Response Formatting**: Handles long responses by breaking them into sections


## Prerequisites 📋

- Python 3.8 or higher
- Discord Bot Token (from [Discord Developer Portal](https://discord.com/developers/applications))
- AnythingLLM API access
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

```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token
TARGET_CHANNEL_ID=your_channel_id

# AnythingLLM Configuration
ANYTHINGLLM_API_KEY=your_api_key
ANYTHINGLLM_BASE_URL=your_base_url
ANYTHINGLLM_ENDPOINT=${ANYTHINGLLM_BASE_URL}/workspace/murray/chat
ANYTHINGLLM_WORKSPACE=murray
```

## Usage 🚀

1. Make sure your virtual environment is activated:
```bash
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

2. Start the bot:
```bash
python main.py
```

3. The bot will automatically:
   - Monitor the FIA website for new F1 documents
   - Download and process new documents
   - Update the AnythingLLM workspace with new information

4. Interact with the bot in your Discord channel:
   - Simply ask questions about F1 regulations or recent decisions
   - The bot will respond with relevant information from the FIA documents

## Project Structure 📁

- `main.py`: Core bot functionality and document monitoring
- `scraper.py`: FIA website document scraping functionality
- `upload_documents.py`: Document processing and AnythingLLM integration
- `documents/`: Directory for storing downloaded FIA documents
- `requirements.txt`: Python dependencies

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

