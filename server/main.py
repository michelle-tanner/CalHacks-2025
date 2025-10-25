import os
from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel # New Import for structured input
from dotenv import load_dotenv
from server.stt import transcribe_audio
from server.tts import synthesize_speech
from server.agent import get_agent_response
from server.json_memory import memory

# Pydantic model for incoming JSON text messages
class MessageRequest(BaseModel):
    message: str

# Load environment variables from the .env file
load_dotenv()

# Fetch API keys from environment variables
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY")
DEEPGRAM_KEY = os.getenv("DEEPGRAM_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")

# Check if API keys are loaded successfully
if not ASI_ONE_API_KEY:
    print("⚠️ API Key not found! Please set the ASI_ONE_API_KEY environment variable.")
else:
    print("✅ API Key successfully loaded!")

# Initialize FastAPI app
app = FastAPI(title="Child Agent Voice Server")

# Allow Cross-Origin Requests (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# WebSocket endpoint for voice chat
@app.websocket("/voice")
async def voice_chat(ws: WebSocket):
    await ws.accept()
    print("🎙️ WebSocket connected")

    try:
        while True:
            data = await ws.receive_json()

            if "text" in data:
                user_text = data["text"]
            elif "bytes" in data:
                audio_bytes = data["bytes"]
                user_text = await transcribe_audio(audio_bytes)
            else:
                continue

            print(f"👦 User: {user_text}")
            
            # Since get_agent_response now returns a dict, we extract the reply
            response_dict = await get_agent_response(user_text)
            reply_text = response_dict['reply']
            
            print(f"🤖 Agent: {reply_text}")
            print(f"🚨 Analysis: {response_dict['analysis']}")

            memory.remember(user_text, reply_text)

            # Optionally, send the reply as audio (Text-to-Speech)
            audio_reply = await synthesize_speech(reply_text)
            await ws.send_bytes(audio_reply)
    except Exception as e:
        print("WebSocket closed:", e)
        await ws.close()

# --- NEW ENDPOINT FOR TEXT-TO-TEXT TESTING ---
@app.post("/message", response_model=dict)
async def handle_text_message(request: MessageRequest):
    """
    Handles simple text message input and returns the agent's reply
    along with the internal safety analysis.
    """
    user_text = request.message
    print(f"📥 Received text message: {user_text}")

    # Use the updated get_agent_response that returns reply and analysis
    response_data = await get_agent_response(user_text)
    
    # Store history for summary endpoint
    memory.remember(user_text, response_data['reply'])

    return response_data
# ---------------------------------------------

# Endpoint for summarizing the conversation
@app.get("/summary")
async def get_summary():
    return {"conversations": memory.context}

# API endpoint for agent response (if needed) - KEEPING BUT FIXING ARGUMENTS
@app.get("/agent")
async def agent_response(message: str = "Hello, what should I say?"):
    response_data = await get_agent_response(message)
    return response_data

# API endpoint for Speech-to-Text (STT) interaction
@app.post("/stt")
async def stt_transcription(audio_file: UploadFile = File(...)):
    transcription = await transcribe_audio(audio_file)
    return {"transcription": transcription}

# Run the FastAPI app with Uvicorn
if __name__ == "__main__":
    import uvicorn
    # Note: Uvicorn auto-reloads, so the server will restart now
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)