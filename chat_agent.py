# Integrate chat LLM and build chat agent 
# Allow agents to exchange text 

import json
import random
from uagents import Agent, Context, Model

#message schema
class Message(Model):
    message: str

#load JSON responses 
with open("responses.json", "r", encoding="utf-8") as f:
    RESPONSE_DB = json.load(f)

#create chat agent
chat_agent = Agent(
    name="chat_agent",
    seed="child-friendly seed phrase",
    port=8000,
    endpoint=["http://localhost:8000/submit"]

)

def find_reply(user_text: str) -> str:
    """Find a suitable reply from the RESPONSE_DB based on keywords in user_text."""
    user_text_lower = user_text.lower()
    
    for entry in RESPONSE_DB:
        for keyword in entry["keywords"]:
            if keyword in user_text_lower:
                return random.choice(entry["responses"])
    return "Hmm, can you tell me a bit more about that? 😊"

@chat_agent.on_message(model=Message)
async def respond_to_user(ctx: Context, sender: str, msg: Message):
    user_text = msg.message
    ctx.logger.info(f"Received message from {sender}: {user_text}")

    reply = find_reply(user_text)
    ctx.logger.info(f"Replying to {sender}: {reply}")
    await ctx.send(sender, Message(message=reply))
    
#run chat agent
if __name__ == "__main__":
    print("Chat Agent address:", chat_agent.address)

    chat_agent.run()