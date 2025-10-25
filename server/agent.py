import os
import json
from openai import OpenAI
from server.json_memory import memory
from dotenv import load_dotenv
from server.prompt_builder import SYSTEM_PROMPT, KNOWLEDGE_BASE
import re
from typing import Dict, Any, List

# Load environment variables and initialize client (unchanged)
load_dotenv()
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY")

if not ASI_ONE_API_KEY:
    print("⚠️ API Key not found! Please set the ASI_ONE_API_KEY environment variable.")
else:
    print("✅ API Key successfully loaded!")

client = OpenAI(
    api_key=os.getenv("ASI_ONE_API_KEY"),
    base_url="https://api.asi1.ai/v1"
)

# --- Load Diagnostic Prompts ---
try:
    with open("server/diagnostic_prompts.json", 'r') as f:
        DIAGNOSTIC_PROMPTS = json.load(f)
except Exception as e:
    print(f"Error loading diagnostic_prompts.json: {e}")
    DIAGNOSTIC_PROMPTS = []

# --- 1. Fact Extraction and Storage Logic ---

def extract_and_store_facts(user_input: str):
    """Uses the LLM to extract key personality facts and stores them."""
    
    current_facts = memory.get_facts()
    facts_str = json.dumps(current_facts) if current_facts else "None"
    
    fact_extraction_prompt = f"""
    You are a Fact Extractor. Your job is to analyze the user's input and extract key, enduring personal facts about the child (e.g., 'pet_name: Sparky', 'favorite_subject: Science', 'habit: bites nails when stressed').
    DO NOT extract temporary feelings. ONLY extract concrete, enduring facts.

    Current known facts: {facts_str}
    User Input: "{user_input}"
    
    Task: Return a SINGLE, complete JSON object containing ONLY the facts extracted or updated. If no new facts are found, return an empty JSON object: {{}}.
    """
    
    try:
        res = client.chat.completions.create(
            model="asi1-mini",
            messages=[
                {"role": "system", "content": fact_extraction_prompt},
            ],
            response_model={"type": "object"}
        )
        
        new_facts = json.loads(res.choices[0].message.content)
        
        for key, value in new_facts.items():
            memory.add_fact(key, value)
        
        if new_facts:
            print(f"🧠 Learned new facts: {new_facts}")

    except Exception as e:
        print(f"⚠️ Fact extraction failed: {e}")

# --- 2. State-Triggered Dialogue Logic (Diagnostic) ---

def get_diagnostic_prompt(user_input: str) -> str:
    """Checks input against triggers and returns relevant diagnostic questions."""
    lowered_input = user_input.lower()
    
    for disorder_data in DIAGNOSTIC_PROMPTS:
        for keyword in disorder_data["trigger_keywords"]:
            if keyword in lowered_input:
                questions = disorder_data["diagnostic_questions"]
                diagnostic_question = questions[0] 
                
                return f"!! DIAGNOSTIC MODE: The child has mentioned {disorder_data['disorder']} keywords. You MUST use this information to ask the following diagnostic question, using child-friendly language: '{diagnostic_question}'. Ensure your response maintains a supportive, non-clinical tone."
                
    return ""

# --- 3. Holistic Summary and Parent Prompt Logic ---

def generate_parent_summary() -> Dict[str, Any]:
    """
    Analyzes the entire conversation history and facts to generate a 
    holistic summary and parent prompt.
    """
    context_str = json.dumps(memory.context)
    facts_str = json.dumps(memory.get_facts())
    
    summary_prompt = f"""
    You are a professional Mental Health Analyst. Review the following child's conversation history and personality facts. Your task is to identify patterns, not make a formal diagnosis.

    Personality Facts: {facts_str}
    Conversation History: {context_str}

    Based on the evidence, determine if there is a **POSSIBLE** mental health concern (e.g., Anxiety, Depression, Behavioral Issue).

    ---
    OUTPUT JSON FORMAT:
    {{
      "recommendation_needed": true/false,
      "summary_for_analyst": "A detailed, clinical-style summary of concerning patterns and supporting evidence from the conversation/facts.",
      "parent_message": "A supportive, non-alarming paragraph for the parent, recommending they seek a professional consultation for their child's well-being.",
      "potential_concerns": ["Anxiety", "Behavioral Issues", "None"] 
    }}
    """
    
    try:
        res = client.chat.completions.create(
            model="asi1-mini",
            messages=[
                {"role": "system", "content": summary_prompt},
            ],
            response_model={"type": "object"}
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Parent summary generation failed: {e}")
        return {"recommendation_needed": False, "summary_for_analyst": "Failed to generate summary.", "parent_message": "", "potential_concerns": ["Error"]}


# --- Core Agent Response Function (Updated) ---

def analyze_for_escalation(user_input: str) -> Dict[str, Any]:
    """
    Analyzes user input against escalation triggers.
    Refined logic to prevent false positives from common words like 'do'.
    """
    alerts = []
    
    # --- REFINED STOP WORDS AND CLEANING ---
    # Expanded list to filter out common conversational words that shouldn't trigger critical alerts
    stop_words = {
        "or", "and", "the", "a", "an", "is", "of", "to", "in", "i", "am", "feeling",
        "my", "your", "what", "do", "you", "most", "about", "with", "like", "how", 
        "it", "this", "that", "want", "have", "can", "if", "be", "just", "them",
        "for", "at", "but", "so", "sometimes", "are", "really"
    } 
    
    # 1. Clean the user input: lowercase, remove punctuation, and split into words
    lowered_input = user_input.lower()
    cleaned_input_words = set(
        re.findall(r'\b\w+\b', lowered_input)
    ) - stop_words
    
    # Convert back to a string for easier comparison, though the set is key
    # cleaned_input_str = " ".join(cleaned_input_words)
    
    # ----------------------------------------
    
    escalation_triggers = [
        item for item in KNOWLEDGE_BASE 
        if item.get("Record_Type") == "ESCALATION_TRIGGER"
    ]

    for trigger in escalation_triggers:
        # 2. Get the criteria keywords and remove stop words from the criteria itself
        criteria_keywords = set(
            re.findall(r'\b\w+\b', trigger.get("Criteria", "").lower())
        ) - stop_words
        
        # 3. Find intersections between the cleaned user input and the cleaned criteria
        trigger_words_found = list(criteria_keywords.intersection(cleaned_input_words))

        if trigger_words_found:
            alerts.append({
                "trigger_name": trigger.get("Trigger_Name"),
                "level": trigger.get("Category"),
                "action": trigger.get("Action"),
                "found_words": trigger_words_found
            })
            
    return {"alerts": alerts}


async def get_agent_response(user_input: str) -> Dict[str, Any]:
    """Use ASI:One model for a reply, run silent analysis, and manage memory."""
    
    extract_and_store_facts(user_input)

    diagnostic_instruction = get_diagnostic_prompt(user_input)
    
    current_facts_str = json.dumps(memory.get_facts())
    current_context_str = json.dumps(memory.context[-5:]) # Only pass last 5 turns for context
    
    full_system_prompt = f"""
    {SYSTEM_PROMPT}

    --- PERSISTENT FACTS ABOUT CHILD (Use to personalize reply) ---
    {current_facts_str}
    
    --- CONVERSATION HISTORY (Most Recent Last) ---
    {current_context_str}
    
    --- URGENT INSTRUCTION ---
    {diagnostic_instruction}
    """

    # 4. Generate Reply
    res = client.chat.completions.create(
        model="asi1-mini",
        messages=[
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": user_input},
        ],
    )
    reply = res.choices[0].message.content.strip()
    
    # 5. Run silent safety analysis
    safety_analysis = analyze_for_escalation(user_input)

    # 6. Store conversation turn (after analysis)
    memory.remember(user_input, reply)
    
    # Return a structured dictionary
    return {
        "reply": reply,
        "analysis": safety_analysis,
        "facts_updated": memory.get_facts()
    }

# --- New Endpoint for Parent Summary ---
async def generate_parent_summary_response() -> Dict[str, Any]:
    return generate_parent_summary()
