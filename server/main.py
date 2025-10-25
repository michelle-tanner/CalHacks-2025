# child_agent/server/main.py
import os
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from server.stt import transcribe_audio
from server.tts import synthesize_speech
from server.agent import get_agent_response
from server.json_memory import memory

from dotenv import load_dotenv
import os

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


# Correctly fetch the API key using the environment variable name
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY")

if not ASI_ONE_API_KEY:
    print("⚠️ API Key not found! Please set the ASI_ONE_API_KEY environment variable.")
else:
    print("✅ API Key successfully loaded!")

# Fetch other API keys
DEEPGRAM_KEY = os.getenv("DEEPGRAM_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")


app = FastAPI(title="Child Agent Voice Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.websocket("/voice")
async def voice_chat(ws: WebSocket):
    await ws.accept()
    print("🎙️ WebSocket connected")

    try:
        while True:
            data = await ws.receive()

            # handle text for debugging or audio bytes for real voice
            if "text" in data:
                user_text = data["text"]
            elif "bytes" in data:
                audio_bytes = data["bytes"]
                user_text = await transcribe_audio(audio_bytes)
            else:
                continue

            print(f"👦 User: {user_text}")
            reply_text = await get_agent_response(user_text)
            print(f"🤖 Agent: {reply_text}")

            memory.remember(user_text, reply_text)

            # optional TTS
            audio_reply = await synthesize_speech(reply_text)
            await ws.send_bytes(audio_reply)
    except Exception as e:
        print("WebSocket closed:", e)
        await ws.close()

@app.get("/summary")
async def get_summary():
    return {"conversations": memory.context}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)

@app.get("/agent")
async def get_agent_response():
    response = get_agent_response_function()  # Your function calling the agent
    return {"response": response}
