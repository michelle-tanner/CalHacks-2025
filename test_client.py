import asyncio
import websockets

async def main():
    uri = "ws://localhost:8000/voice"
    async with websockets.connect(uri) as ws:
        while True:
            msg = input("👦 You: ")
            if not msg.strip():
                break
            await ws.send(msg)
            reply = await ws.recv()
            print("🤖 Agent replied (audio bytes):", len(reply), "bytes")

asyncio.run(main())
