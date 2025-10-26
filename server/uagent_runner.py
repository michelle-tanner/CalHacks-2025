import os
from uagents import Agent, Protocol, Context, Model
# from uagents.setup import fund_agent_if_low
from dotenv import load_dotenv
# Import the Chat Protocol tools you already use in main.py
from uagents_core.contrib.protocols.chat import ChatMessage, TextContent, ChatAcknowledgement
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    StartSessionContent,
    EndSessionContent,
    AgentContent,
    TextContent,
    chat_protocol_spec,
)
from datetime import datetime
from uuid import uuid4

load_dotenv()

#import your core logic
from server.agent import get_agent_response
from uagents_core.contrib.protocols.chat import ChatMessage, TextContent, ChatAcknowledgement

# --- Configuration ---
AGENT_SEED_PHRASE = os.getenv("child_imitation_agent") #unique seed for this agent
AGENTVERSE_ENDPOINT = os.getenv("AGENTVERSE_ENDPOINT", "https://agentverse.ai")

#initialize agent
agent = Agent(
    name="child-imitation-agent",
    port=8001,
    endpoint=("http://127.0.0.1:8001/submit"),
    mailbox=True,
)

#define chat protocol
chat_protocol = Protocol(name="Chat", version="1.0")

#handler
@chat_protocol.on_message(ChatMessage, replies={ChatMessage, ChatAcknowledgement})
async def handle_agentverse_chat(ctx: Context, sender: str, msg: ChatMessage):
    # Extract text from the incoming structured message
    user_text = ""
    for content in msg.content:
        if isinstance(content, TextContent):
            user_text = content.text
            break
            
    if not user_text:
        # Acknowledge if no text is present
        await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))
        return

    # Call your existing core agent logic
    response_dict = await get_agent_response(user_text)
    reply_text = response_dict['reply']

    ctx.logger.info(f"Received from {sender}: {user_text}")
    ctx.logger.info(f"Responding with: {reply_text}")

    # Send the response back wrapped in a ChatMessage
    outgoing_message = ChatMessage(
        content=[TextContent(type="text", text=reply_text)],
        msg_id=uuid4(),
        timestamp=datetime.utcnow()
    )
    await ctx.send(sender, outgoing_message)

# 4. Include the Protocol and Run
agent.include(chat_protocol)

if __name__ == "__main__":
    agent.run()