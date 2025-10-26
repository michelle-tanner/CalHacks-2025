import os
from fastapi import FastAPI, UploadFile, File, WebSocket, Request # Combined imports
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel # New Pydantic model for text chat
from dotenv import load_dotenv
from server.stt import transcribe_audio
from server.tts import synthesize_speech
# Combined and updated agent imports
from server.agent import get_agent_response, client, generate_parent_summary_response
from server.json_memory import memory

# --- New Imports for Agentverse Chat Protocol (from File 1) ---
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    TextContent,
    ChatAcknowledgement
)
from datetime import datetime
from uuid import uuid4

# Pydantic model for incoming JSON text messages (from File 2)
class MessageRequest(BaseModel):
    message: str

# Load environment variables from the .env file
load_dotenv()

# Fetch API keys from environment variables (Redundant, but kept for clarity)
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY")
DEEPGRAM_KEY = os.getenv("DEEPGRAM_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Check if API keys are loaded successfully (Redundant, but kept for clarity)
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


# ------------------------------------------------
## 1. WebSocket Endpoint (Original Voice Chat - Combined Logic)
# ------------------------------------------------

from starlette.websockets import WebSocketDisconnect #add if not present
@app.websocket("/voice")
async def voice_chat(ws: WebSocket):
    await ws.accept()
    print("🎙️ WebSocket connected")

    try:
        while True:
            #ws.receive() to handle text, bytes, or json
            data = await ws.receive()
            user_text = ""

            # Handle text or audio bytes from WebSocket
            if "text" in data:
                user_text = data["text"]
            elif "bytes" in data:
                audio_bytes = data["bytes"]
                print(f"🎙️ Received {len(audio_bytes)} bytes of audio.")
                
                #skip empty messages
                if not audio_bytes:
                    continue 

                #call STT module with raw bytes 
                user_text = await transcribe_audio(audio_bytes)
                print(f"👂 Transcription Result: {user_text}")
            
            # Client sent a text message inside a JSON object (for flexibility)
            elif "json" in data and "text" in data["json"]:
                user_text = data["json"]["text"]
            if not user_text or user_text in ["[Deepgram API key missing]", "[transcription error]"]:
                if "[transcription error]" in user_text:
                    await ws.send_text("I'm sorry, I had trouble hearing you. Can you try again?")
                continue
            # else:
                # continue

            print(f"👦 User: {user_text}")

            # Use the updated get_agent_response that returns reply, analysis, and facts (from File 2)
            response_dict = await get_agent_response(user_text)
            reply_text = response_dict['reply']
            
            # Save conversation to memory (from File 1, but applied after extracting reply_text)
            memory.remember(user_text, reply_text)
            
            print(f"🤖 Agent: {reply_text}")
            print(f"🚨 Analysis: {response_dict.get('analysis', 'N/A')}") # Include analysis if present

            # Synthesize speech and send bytes (standard logic)
            audio_reply = await synthesize_speech(reply_text)
            
            if audio_reply:
                await ws.send_bytes(audio_reply)
            else:
                #agent TTS (ElevenLabs) not working 
                await ws.send_text("I can't talk right now, but here is my text reply: " + reply_text)

            pass 
        
    except WebSocketDisconnect:
        print("🎙️ WebSocket disconnected cleanly.")
    except Exception as e:
        print("⚠️ WebSocket closed due to an error:", e)
        try:
            await ws.close()
        except Exception:
            pass


# ------------------------------------------------
## 3. Standard FastAPI Endpoints
# ------------------------------------------------

# --- ENDPOINT FOR TEXT-TO-TEXT CHAT (from File 2) ---
@app.post("/message", response_model=dict)
async def handle_text_message(request: MessageRequest):
    """
    Handles simple text message input and returns the agent's reply
    along with the internal safety analysis and updated facts.
    """
    user_text = request.message
    print(f"📥 Received text message: {user_text}")

    # Use the updated get_agent_response that returns reply, analysis, and facts
    response_data = await get_agent_response(user_text)

    return response_data

# UPDATED ENDPOINT: Now returns both conversation context and learned facts (from File 2)
@app.get("/summary")
async def get_summary():
    """Returns the full conversation context and the learned child facts."""
    return {"conversations": memory.context, "facts": memory.get_facts()}

# --- NEW ENDPOINT FOR PARENT SUMMARY (from File 2) ---
@app.post("/parent_summary")
async def generate_parent_report():
    """
    Generates a holistic summary and professional recommendation for the parent
    based on the full history and stored facts.
    """
    report = await generate_parent_summary_response()
    
    return report

# API endpoint for agent response (combined, using the logic from File 2)
@app.get("/agent")
async def agent_response(message: str = "Hello, what should I say?"):
    response_data = await get_agent_response(message)
    return response_data

# API endpoint for Speech-to-Text (STT) interaction (Redundant, but kept)
@app.post("/stt")
async def stt_transcription(audio_file: UploadFile = File(...)):
    transcription = await transcribe_audio(audio_file)
    return {"transcription": transcription}

# Run the FastAPI app with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)


