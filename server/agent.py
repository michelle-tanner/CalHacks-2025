# child_agent/server/agent.py
import os
from openai import OpenAI
from server.json_memory import memory

from dotenv import load_dotenv
import os

# child_agent/server/agent.py
import os
from openai import OpenAI
from server.json_memory import memory
from dotenv import load_dotenv

# --- NEW IMPORTS ---
# Import the prompt and KB we just built
from server.prompt_builder import SYSTEM_PROMPT, KNOWLEDGE_BASE
import re
# ---------------------

# Load environment variables from the .env file
load_dotenv()

# (API Key loading code remains the same...)

client = OpenAI(
    api_key=os.getenv("ASI_ONE_API_KEY"),
    base_url="https://api.asi1.ai/v1"
)

# --- NEW FUNCTION: The "Hybrid" Part ---
def analyze_for_escalation(user_input: str) -> dict:
    """
    Silently checks the user's input against the clinical escalation triggers.
    This runs AFTER the LLM response is generated.
    """
    alerts = []
    lowered_input = user_input.lower()
    
    # Find all escalation triggers in our KB
    escalation_triggers = [
        item for item in KNOWLEDGE_BASE 
        if item.get("Record_Type") == "ESCALATION_TRIGGER"
    ]

    for trigger in escalation_triggers:
        # This is a simple regex check. You can make this smarter.
        # It checks if keywords in the "Criteria" are in the user input.
        # NOTE: This is a simplified check. A real system might
        # need to track "duration" across multiple sessions.
        
        criteria_keywords = re.findall(r'\b\w+\b', trigger.get("Criteria", ""))
        trigger_words_found = [
            kw for kw in criteria_keywords 
            if kw.lower() in lowered_input and kw.lower() not in ["or", "and", "gte", "for"]
        ]

        if trigger_words_found:
            alerts.append({
                "trigger_name": trigger.get("Trigger_Name"),
                "level": trigger.get("Category"),
                "action": trigger.get("Action"),
                "found_words": trigger_words_found
            })
            
    return {"alerts": alerts}
# ----------------------------------------


async def get_agent_response(user_input: str) -> dict: # Changed to return a dict
    """Use JSON fallback or ASI:One model for a reply."""
    
    # We remove the simple rule-based branch. Let the LLM handle "sad".
    # The system prompt is now smart enough to guide it.
    
    # --- UPDATED ---
    # The system_prompt is no longer from a .txt file
    # We use the globally-loaded SYSTEM_PROMPT from prompt_builder.py
    res = client.chat.completions.create(
        model="asi1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
    )
    reply = res.choices[0].message.content.strip()
    # -----------------
    
    # --- NEW: Run silent analysis AFTER getting the reply ---
    analysis = analyze_for_escalation(user_input)
    # --------------------------------------------------------

    # Return a structured dictionary
    return {
        "reply": reply,
        "analysis": analysis
    }