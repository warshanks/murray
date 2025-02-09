# Murray

Murray is an AI-powered Discord bot that uses documents from the FIA to answer questions about the Formula 1.
It's named in honor of Murray Walker, the legendary commentator.

Murray uses the AnythingLLM API to upload documents to a workspace, and then uses the workspace to answer questions.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Create a `.env` file and set the following environment variables:


    - `DISCORD_TOKEN`: The token for the Discord bot
    - `TARGET_CHANNEL_ID`: The ID of the channel to send messages to
    - `ANYTHINGLLM_API_KEY`: The API key for the AnythingLLM API
    - `ANYTHINGLLM_ENDPOINT`: The endpoint for the AnythingLLM API

## Usage

To run the bot, use the following command:

```bash
python main.py
```

