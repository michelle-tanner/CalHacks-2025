# child_agent/server/stt.py
import aiohttp, os

async def transcribe_audio(audio_bytes: bytes) -> str:
    """Send raw audio bytes to Deepgram API for speech-to-text."""
    dg_key = os.getenv("DEEPGRAM_API_KEY")
    if not dg_key:
        return "[Deepgram API key missing]"
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.deepgram.com/v1/listen",
            headers={"Authorization": f"Token {dg_key}"},
            data=audio_bytes
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                print("Deepgram error:", text)
                return "[transcription error]"
            result = await resp.json()
            return result["results"]["channels"][0]["alternatives"][0].get("transcript", "")
