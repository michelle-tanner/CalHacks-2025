# /server/prompt_builder.py
import json
import os

# Define a constant path to your KB
KB_PATH = os.path.join(os.path.dirname(__file__), 'knowledge_base.json')

def load_knowledge_base():
    """Loads the normalized JSON data from the file."""
    try:
        with open(KB_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Knowledge Base file not found at {KB_PATH}")
        return []
    except json.JSONDecodeError:
        print(f"⚠️ Error decoding {KB_PATH}. Make sure it's valid JSON.")
        return []

def build_system_prompt(knowledge_base):
    """
    Converts the normalized JSON data into a single, comprehensive
    system prompt for the LLM.
    """
    prompt_parts = [
        "You are an empathetic, patient, and non-judgmental AI assistant supporting a child's mental wellness.",
        "Your primary goal is to listen, validate feelings, and create a safe space. You must strictly follow all rules."
    ]

    # --- Add Ethical Guardrails ---
    prompt_parts.append("\n## 1. CRITICAL ETHICAL GUARDRAILS (DO NOT VIOLATE)\n")
    for item in knowledge_base:
        if item.get("Record_Type") == "GUARDRAIL_STIGMA" or item.get("Record_Type") == "GUARDRAIL_TONE":
            rule = f"- **Rule:** {item.get('Rule_Type', 'N/A')}\n"
            rule += f"  - **DO NOT SAY:** \"{item.get('Avoid_Pattern', 'N/A')}\"\n"
            rule += f"  - **INSTEAD, SAY:** \"{item.get('Best_Practice', 'N/A')}\"\n"
            rule += f"  - **Reason:** {item.get('Justification', 'N/A')}\n"
            prompt_parts.append(rule)

    # --- Add Safety Guardrails ---
    prompt_parts.append("\n## 2. SAFETY & SCOPE RULES\n")
    for item in knowledge_base:
        if item.get("Record_Type") == "GUARDRAIL_SAFETY":
            prompt_parts.append(f"- **Rule:** {item.get('Rule_Type')}: {item.get('Avoid_Pattern')} {item.get('Best_Practice')}")

    # --- Add Dialogue Rules ---
    prompt_parts.append("\n## 3. CONVERSATIONAL DIALOGUE RULES\n")
    for item in knowledge_base:
        if item.get("Record_Type") == "DIALOGUE_RULE":
            prompt_parts.append(f"- **IF:** {item.get('Rule_Condition')}\n  - **THEN:** {item.get('Prioritized_Action')}\n")

    # --- Add Dialogue Pitfalls ---
    prompt_parts.append("\n## 4. CONVERSATIONAL PITFALLS TO AVOID\n")
    for item in knowledge_base:
        if item.get("Record_Type") == "DIALOGUE_PITFALL":
            prompt_parts.append(f"- **AVOID (Pitfall):** {item.get('Pitfall')}\n  - **SOLUTION:** {item.get('Solution_Rule')}\n")

    # --- Add Example Dialogue Prompts ---
    prompt_parts.append("\n## 5. EXAMPLE CONVERSATIONS (Follow this style)\n")
    for item in knowledge_base:
        if item.get("Record_Type") == "DIALOGUE_PROMPT":
            if item.get("Context_or_Condition", "").startswith("user_says:"):
                user = item['Context_or_Condition']
                agent = item['Agent_Prompt_Text']
                prompt_parts.append(f"- **User:** \"{user}\"\n  - **Agent:** \"{agent}\"\n")

    prompt_parts.append("\n## YOUR TASK\nNow, respond to the user's last message with empathy, following all rules above.")
    return "\n".join(prompt_parts)

# Load the KB and build the prompt ONCE when the module is imported
print("Loading Knowledge Base...")
KNOWLEDGE_BASE = load_knowledge_base()
SYSTEM_PROMPT = build_system_prompt(KNOWLEDGE_BASE)
print(f"✅ System Prompt built with {len(KNOWLEDGE_BASE)} records.")