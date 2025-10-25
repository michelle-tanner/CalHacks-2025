import os
from fastapi import FastAPI, UploadFile, File, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from server.stt import transcribe_audio
from server.tts import synthesize_speech
from server.agent import get_agent_response, client # Import client for use below
from server.json_memory import memory

# --- New Imports for Agentverse Chat Protocol ---
from uagents_core.contrib.protocols.chat import (
    ChatMessage, 
    TextContent, 
    ChatAcknowledgement
)
from datetime import datetime
from uuid import uuid4

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


# ------------------------------------------------
## 1. WebSocket Endpoint (Original Voice Chat)
# ------------------------------------------------
@app.websocket("/voice")
async def voice_chat(ws: WebSocket):
    await ws.accept()
    print("🎙️ WebSocket connected")

    try:
        while True:
            data = await ws.receive_json()  # Receive JSON data from WebSocket

            # Handle text or audio bytes from WebSocket
            if "text" in data:
                user_text = data["text"]
            elif "bytes" in data:
                audio_bytes = data["bytes"]
                user_text = await transcribe_audio(audio_bytes)
            else:
                continue

            print(f"Data type received: {type(data)}")
            print(f"👦 User: {user_text}")
            
            reply_text = await get_agent_response(user_text)
            
            print(f"🤖 Agent: {reply_text}")

            if isinstance(reply_text, str):
                #save conversation to memory
                memory.remember(user_text, reply_text)
                #synthesize speech using ElevenLabs TTS 
                audio_reply = await synthesize_speech(reply_text)
                await ws.send_bytes(audio_reply)
            else:
                print("⚠️ Reply is not a string.")
                await ws.send_text("[Error: Invalid reply format]")
            # Optionally, send the reply as audio (Text-to-Speech)
            # audio_reply = await synthesize_speech(reply_text)
            # await ws.send_bytes(audio_reply)
    except Exception as e:
        print("WebSocket closed:", e)
        await ws.close()

# ------------------------------------------------
## 2. HTTP POST Endpoint (Agentverse/ASI:One Protocol)
# ------------------------------------------------
# This is the required endpoint for hackathon qualification.
@app.post("/protocol-chat", response_model=ChatMessage)
async def agentverse_chat(incoming_message: ChatMessage):
    """
    Handles structured ChatProtocol messages from Agentverse/ASI:One.
    This endpoint ensures hackathon track compatibility.
    """
    
    # 1. Extract the user's text from the structured message
    user_text = ""
    for content in incoming_message.content:
        # The actual text is inside the TextContent model
        if isinstance(content, TextContent):
            user_text = content.text
            break

    if not user_text:
        # Acknowledge the message but return an error if no text is present
        return ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=incoming_message.msg_id)

    # 2. Call the unified agent logic
    reply_text = await get_agent_response(user_text)
    print(f"🌐 Agentverse User: {user_text}")
    print(f"🌐 Agentverse Reply: {reply_text}")

    # 3. Wrap the agent's response back into a ChatMessage
    outgoing_message = ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=reply_text)]
    )
    
    # NOTE: In a real uAgents setup, you'd send an ACK first, then the response.
    # For a simple web hook registration, returning the response message is often sufficient.
    
    return outgoing_message

# ------------------------------------------------
## 3. Standard FastAPI Endpoints (Remaining API)
# ------------------------------------------------

# Endpoint for summarizing the conversation
@app.get("/summary")
async def get_summary():
    return {"conversations": memory.context}

# API endpoint for agent response (if needed)
@app.get("/agent")
async def agent_response():
    response = await get_agent_response()  # Your agent logic here
    return {"response": response}

# API endpoint for Speech-to-Text (STT) interaction
@app.post("/stt")
async def stt_transcription(audio_file: UploadFile = File(...)):
    transcription = await transcribe_audio(audio_file)  # Call STT logic from agent.py
    return {"transcription": transcription}

# Run the FastAPI app with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
