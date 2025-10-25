from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
    StartSessionContent,
    EndSessionContent,
)

chat_proto = Protocol(spec=chat_protocol_spec)

from typing import Any, Dict
from uagents import Model

class StructuredOutputPrompt(Model):
    prompt: str
    output_schema: Dict[str, Any]

class StructuredOutputResponse(Model):
    output: Dict[str, Any]

struct_output_client_proto = Protocol(
    name="StructuredOutputClientProtocol", version="0.1.0"
)

from datetime import datetime
from uuid import uuid4


def create_text_chat(text: str, end_session: bool = False) -> ChatMessage:
    content = [TextContent(type="text", text=text)]
    if end_session:
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=content,
    )

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    StartSessionContent,
)

from functions import get_weather, WeatherRequest

AI_AGENT_ADDRESS = (
    "agent1qtlpfshtlcxekgrfcpmv7m9zpajuwu7d5jfyachvpa4u3dkt6k0uwwp2lct"  # OpenAI AI agent address
)

agent = Agent()

@chat_proto.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    ctx.logger.info(f"Got a message from {sender}: {msg.content}")

    # Remember who sent this session's message so we can reply later
    ctx.storage.set(str(ctx.session), sender)

    # Acknowledge receipt
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id
        ),
    )

    # Extract user text and forward to AI agent for structured output
    for item in msg.content:
        if isinstance(item, StartSessionContent):
            ctx.logger.info(f"Got a start session message from {sender}")
            continue
        elif isinstance(item, TextContent):
            ctx.logger.info(f"User said: {item.text}")

            # Ask the AI agent to produce JSON matching our schema
            await ctx.send(
                AI_AGENT_ADDRESS,
                StructuredOutputPrompt(
                    prompt=item.text, output_schema=WeatherRequest.schema()
                ),
            )
        else:
            ctx.logger.info("Ignoring non-text content")

@struct_output_client_proto.on_message(StructuredOutputResponse)
async def handle_structured_output_response(
    ctx: Context, sender: str, msg: StructuredOutputResponse
):
    ctx.logger.info(f"Structured output: {msg.output}")

    # Who started this session?
    session_sender = ctx.storage.get(str(ctx.session))
    if session_sender is None:
        ctx.logger.error("No session sender found in storage")
        return

    # Handle unknowns gracefully
    if "<UNKNOWN>" in str(msg.output):
        await ctx.send(
            session_sender,
            create_text_chat(
                "Sorry, I couldn't process your location request. Please try again later."
            ),
        )
        return

    # Extract location from structured output
    try:
        location = msg.output.get("location") if isinstance(msg.output, dict) else None
    except Exception:
        location = None
    ctx.logger.info(f"prompt{location}")

    try:
        if not location:
            raise ValueError("No location provided in structured output")
        weather = get_weather(location)
        ctx.logger.info(str(weather))
    except Exception as err:
        ctx.logger.error(f"Weather error: {err}")
        await ctx.send(
            session_sender,
            create_text_chat(
                "Sorry, I couldn't process your request. Please try again later."
            ),
        )
        return

    if "error" in weather:
        await ctx.send(session_sender, create_text_chat(str(weather["error"])) )
        return

    # Reply uses pre-formatted text from get_weather
    reply = weather.get("weather") or f"Weather for {location}: (no data)"
    await ctx.send(session_sender, create_text_chat(reply))

agent.include(chat_proto, publish_manifest=True)
agent.include(struct_output_client_proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
