# child_agent/server/tts.py
import aiohttp, os

async def synthesize_speech(text: str) -> bytes:
    """Turn text into speech using ElevenLabs API."""
    xi_key = os.getenv("ELEVENLABS_API_KEY")
    
    if not xi_key:
        print("⚠️ Missing ElevenLabs API key, returning dummy bytes")
        return b""
    
    voice = "Rachel"  # friendly child voice

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                headers={"xi-api-key": xi_key, "accept": "audio/mpeg"},
                json={
                    "text": text,
                    "voice_settings": {"stability": 0.4, "similarity_boost": 0.8},
                },
            ) as resp:
                if resp.status != 200:
                    error_detail = await resp.text()
                    print("❌ ElevenLabs API Error! Status: ", resp.status, ". Detail: ", error_detail)
                    return b""
                return await resp.read()
        except Exception as e:
            print(f"🚨 TTS Connection Error: {e}")
            return b""