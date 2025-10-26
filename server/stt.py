# child_agent/server/stt.py
import aiohttp, os

async def transcribe_audio(audio_bytes: bytes) -> str:
    """Send raw audio bytes to Deepgram API for speech-to-text."""
    dg_key = os.getenv("DEEPGRAM_API_KEY")
    if not dg_key:
        return "[Deepgram API key missing]"
    
    timeout_config = aiohttp.ClientTimeout(total=30)  # 30 seconds timeout
    # header = {
    #     "Authorization": f"Token {dg_key}",
    #     "Content-Type": "audio/webm",
    # }
    async with aiohttp.ClientSession(timeout=timeout_config) as session:
        async with session.post(
            "https://api.deepgram.com/v1/listen",
            headers={"Authorization": f"Token {dg_key}"},
            data=audio_bytes
            # "https://api.deepgram.com/v1/listen?model=general&language=en",
            # headers=headers,
            # data=audio_bytes
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"❌ Deepgram API Error! Status: {resp.status}. Detail: {text[:150]}...")
                return "[transcription error]"
            result = await resp.json()
            return result["results"]["channels"][0]["alternatives"][0].get("transcript", "")
