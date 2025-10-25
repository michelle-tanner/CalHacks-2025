# python register_agent.py
from fetchai.registration import register_with_agentverse
from uagents_core.crypto import Identity
import os

identity = Identity.from_seed(os.getenv("AGENT_SECRET_KEY"), 0)
register_with_agentverse(identity, "http://localhost:8000/submit",
                         os.getenv("AGENTVERSE_KEY"), "KidHelperBot",
                         "domain:mental-health\n<description>9–12 friendly voice agent</description>")
