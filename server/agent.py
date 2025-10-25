# child_agent/server/agent.py
import os
from openai import OpenAI
from server.json_memory import memory

from dotenv import load_dotenv


# Load environment variables from the .env file
load_dotenv()

# Now access the keys from environment variables
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY")
DEEPGRAM_KEY = os.getenv("DEEPGRAM_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")

if not ASI_ONE_API_KEY:
    print("⚠️ API Key not found! Please set the ASI_ONE_API_KEY environment variable.")
else:
    print("✅ API Key successfully loaded!")


client = OpenAI(
    api_key=os.getenv("ASI_ONE_API_KEY"),
    base_url="https://api.asi1.ai/v1"
)

async def get_agent_response(user_input: str) -> str:
    """Use JSON fallback or ASI:One model for a reply."""
    
    #1. Simple rule-based branch for emotion words (Fallback/Memory)
    lowered = user_input.lower()
    if any(k in lowered for k in ["sad", "lonely", "upset", "worried"]):
        reply = memory.load_category("sadness")
        if not reply: #fallback if memory fails to load
            reply = "It's okay to feel that way. I'm here for you. (failed call to sadness)"
    #2. LLM Call (Main Logic)
    else:
        try:
            system_prompt = open("server/prompts/base_prompt.txt").read()
            res = client.chat.completions.create(
                model="asi1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
            )
            reply = res.choices[0].message.content.strip()
        except Exception as e:
            print("⚠️ ASI:One error:", e)
            reply = "Sorry, I couldnt' process that right now."
    
    return reply