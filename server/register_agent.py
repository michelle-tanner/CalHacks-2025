# python register_agent.py
from fetchai.registration import register_with_agentverse
from uagents_core.crypto import Identity
import os
from dotenv import load_dotenv

load_dotenv()

#fetch api keys 
AGENT_SECRET_KEY = os.getenv("AGENT_SECRET_KEY")
AGENTVERSE_API_KEY = os.getenv("AGENTVERSE_API_KEY")
AGENT_ENDPOINT_URL = os.getenv("AGENT_ENDPOINT_URL")  # e.g., "http://localhost:8000"

#check for missing keys 
if not all([AGENT_SECRET_KEY, AGENTVERSE_API_KEY, AGENT_ENDPOINT_URL]):
    print("❌ ERROR: Missing one or more critical environment variables (.env file is incomplete).")
    print("Ensure AGENT_SECRET_KEY, AGENTVERSE_KEY, and AGENT_ENDPOINT_URL are set.")
    exit(1)


#agents unique identity 
identity = Identity.from_seed(AGENT_SECRET_KEY, 0)

#construct webhook URL using public endpoint 
webhook_url = f"{AGENT_ENDPOINT_URL}/protocol-chat"

#define agent's metadata (The README content)
agent_name = "KidHelperBot"
# This description is what ASI:One uses to find and understand your agent!
agent_readme = "domain:mental-health\n<description>A caring, supportive, and fun voice agent designed for children aged 9–12. Provides friendly chat and emotional support.</description>"


# 6. Register the agent
print(f"Attempting to register Agent: {agent_name} at {webhook_url}...")

try:
    register_with_agentverse(
        identity, 
        webhook_url,
        AGENTVERSE_API_KEY, 
        agent_name,
        agent_readme
    )
    print(f"✅ Successfully registered Agent: {agent_name}!")
    print(f"Agent Address: {identity.address}")
    
except Exception as e:
    print(f"❌ Registration failed: {e}")