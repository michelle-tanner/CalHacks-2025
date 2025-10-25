# user_agent.py
import asyncio
from uagents import Agent, Context, Model

# Replace this with the address printed by chat_agent.py
CHAT_AGENT_ADDRESS = "agent1qv5gwujwhmdrjlh5nfh430s4mx4zn4mk3fdgv0cpxfa9zjsy3dm2yd2sw3p"

class Message(Model):
    message: str

# Initialize UserAgent
user_agent = Agent(
    name="UserAgent",
    seed="user seed phrase",
    port=8001,  # different from chat_agent
    endpoint=["http://127.0.0.1:8001/submit"]
)

# Callback to receive messages
@user_agent.on_message(model=Message)
async def receive_message(ctx: Context, sender: str, msg: Message):
    print(f"ChatAgent: {msg.message}")

# Chat loop outside handler
async def chat_loop():
    print("Start chatting! Type your messages below (type 'exit' to quit).")
    while True:
        user_text = input("You: ")
        if user_text.lower() in ["exit", "quit"]:
            print("Exiting chat...")
            break
        # Use submit() here, NOT send()
        await user_agent.send(CHAT_AGENT_ADDRESS, Message(message=user_text))

if __name__ == "__main__":
    print(f"User Agent address: {user_agent.address}")
    loop = asyncio.get_event_loop()
    # Schedule chat loop as a background task
    loop.create_task(chat_loop())
    # Start the agent server
    user_agent.run()
