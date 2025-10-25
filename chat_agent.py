from uagents import Agent
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


agent = Agent()

