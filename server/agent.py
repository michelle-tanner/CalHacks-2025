import os
import json
from openai import AsyncOpenAI  # <--- FIX 1: Import AsyncOpenAI
from server.json_memory import memory
from dotenv import load_dotenv
from server.prompt_builder import SYSTEM_PROMPT, KNOWLEDGE_BASE
import re
from typing import Dict, Any, List
# Import Pydantic for structured output schema
from pydantic import BaseModel, Field, ValidationError


# --------------------------------
# uAgents Imports and Setup
# --------------------------------

from datetime import datetime
from uuid import uuid4
import os
from dotenv import load_dotenv
# from openai import OpenAI
from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    StartSessionContent,
    EndSessionContent,
    AgentContent,
    TextContent,
    chat_protocol_spec,
)


# Load environment variables and initialize client (unchanged)
load_dotenv()

agent = Agent(
    name="child-imitation-agent",
    port=8002,
    seed=os.getenv("AGENT_SEED_PHRASE"),
    endpoint=("https://agentverse.ai/v1/submit"),
    mailbox=True,
)
protocol = Protocol(spec=chat_protocol_spec)

# Chat protocol so you can message through asi one and agentverse
@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id),
    )
    
    # 2. Check if the message content is text
    is_user_message = isinstance(msg.content[-1], TextContent)
    
    # Log the incoming message for debugging
    ctx.logger.info(f"Received message: {msg}")

    if is_user_message:
        # 3. Get the user's input text
        user_input = msg.content[-1].text
        ctx.logger.info(f"Processing text: '{user_input}'")
        
        response_text = "I'm not sure what to say." # Default response
        
        try:
            # 4. Call your existing ASI:One logic function
            # This function handles fact extraction, analysis, and getting the LLM reply
            response_data = await get_agent_response(user_input)
            
            # 5. Extract the reply text from the response dictionary
            response_text = response_data.get("reply", "I had a problem thinking of a reply.")
            
            # Optional: Log the analysis or facts for your own debugging
            ctx.logger.info(f"Analysis: {response_data.get('analysis')}")
            ctx.logger.info(f"Facts Updated: {response_data.get('facts_updated')}")

        except Exception as e:
            # 6. Handle any errors during the API call
            # <--- FIX 2: Added exc_info=True to see the full error stack trace
            ctx.logger.error(f"Error processing agent response: {e}", exc_info=True)
            response_text = "Oh dear, I had a little trouble thinking of a reply."

        # 7. Send the actual LLM response back to the user
        await ctx.send(sender, ChatMessage(
            timestamp=datetime.now(),
            msg_id=uuid4(),
            content=[
                TextContent(type="text", text=response_text),
                # This will keep the chat session open
                # EndSessionContent(type="end-session") 
            ]
        ))
        
@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass

# I believe you have to have this to register it to AgentVerse
agent.include(protocol, publish_manifest=True)


ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY")


if not ASI_ONE_API_KEY:
    print("⚠️ API Key not found! Please set the ASI_ONE_API_KEY environment variable.")
else:
    print("✅ API Key successfully loaded!")


# <--- FIX 3: Initialize AsyncOpenAI
client = AsyncOpenAI(
    api_key=os.getenv("ASI_ONE_API_KEY"),
    base_url="https://api.asi1.ai/v1",
#     model="asi1-mini"
)

# --- Load Diagnostic Prompts ---
try:
    # Assuming this file exists and is correctly structured
    with open("server/diagnostic_prompts.json", 'r') as f:
        DIAGNOSTIC_PROMPTS = json.load(f)
except Exception as e:
    print(f"Error loading diagnostic_prompts.json: {e}")
    DIAGNOSTIC_PROMPTS = []


# --- Pydantic Schema for Structured Parent Summary ---
class ParentSummary(BaseModel):
    """Defines the strict JSON structure for the Parent Summary response."""
    recommendation_needed: bool = Field(..., description="True if potential concerns warrant professional advice, False otherwise.")
    summary_for_analyst: str = Field(..., description="A detailed, clinical-style summary of concerning patterns and supporting evidence from the conversation/facts.")
    parent_message: str = Field(..., description="A supportive, non-alarming paragraph for the parent, recommending professional consultation.")
    potential_concerns: List[str] = Field(..., description="A list of potential mental health concerns (e.g., Anxiety, Depression, Behavioral Issues). Use 'None' if no serious concerns are noted.")


# --- Helper function for JSON cleaning ---
def clean_json_text(text: str) -> str:
    """Strips common markdown fences from JSON output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
        
    if text.endswith("```"):
        text = text[:-3]
    
    return text.strip()


# --- 1. Fact Extraction and Storage Logic (FIXED with JSON Cleaning) ---

# <--- FIX 4: Make the function async
async def extract_and_store_facts(user_input: str):
    """Uses the LLM to extract key personality facts and stores them."""
    
    current_facts = memory.get_facts()
    facts_str = json.dumps(current_facts) if current_facts else "None"
    
    fact_extraction_prompt = f"""
    You are a Fact Extractor. Your job is to analyze the user's input and extract key, enduring personal facts about the child (e.g., 'pet_name: Sparky', 'favorite_subject: Science', 'favorite_animal: Capybara').
    DO NOT extract temporary feelings. ONLY extract concrete, enduring facts.

    Current known facts: {facts_str}
    User Input: "{user_input}"
    
    Task: Return a SINGLE, complete JSON object containing ONLY the facts extracted or updated. If no new facts is found, return an empty JSON object: {{}}.
    """
    
    try:
        # Use user role and compatible response_format
        # <--- FIX 5: Use 'await' for the API call
        res = await client.chat.completions.create(
            model="asi1-mini",
            messages=[
                {"role": "user", "content": fact_extraction_prompt},
            ],
            response_format={"type": "json_object"}
        )
        
        # Extract and CLEAN the text before parsing
        json_text = res.choices[0].message.content
        cleaned_json = clean_json_text(json_text)
        
        # Parse the cleaned JSON
        new_facts = json.loads(cleaned_json)
        
        for key, value in new_facts.items():
            memory.add_fact(key, value)
        
        if new_facts:
            print(f"🧠 Learned new facts: {new_facts}")

    except Exception as e:
        # This will now catch JSONDecodeError if the cleaning fails
        print(f"⚠️ Fact extraction failed. Raw LLM output: {json_text if 'json_text' in locals() else 'N/A'}. Error: {e}")


# --- 2. State-Triggered Dialogue Logic (Diagnostic) ---
# (This function performs no I/O, so it remains synchronous)
def get_diagnostic_prompt(user_input: str) -> str:
    """Checks input against triggers and returns relevant diagnostic questions."""
    lowered_input = user_input.lower()
    
    for disorder_data in DIAGNOSTIC_PROMPTS:
        for keyword in disorder_data["trigger_keywords"]:
            if keyword in lowered_input:
                questions = disorder_data["diagnostic_questions"]
                # For simplicity, always use the first question when triggered
                diagnostic_question = questions[0]
                
                return f"!! DIAGNOSTIC MODE: The child has mentioned {disorder_data['disorder']} keywords. You MUST use this information to ask the following diagnostic question, using child-friendly language: '{diagnostic_question}'. Ensure your response maintains a supportive, non-clinical tone."
                
    return ""


# --- 3. Holistic Summary and Parent Prompt Logic ---

# <--- FIX 6: Make the function async
async def generate_parent_summary() -> Dict[str, Any]:
    """
    Analyzes the entire conversation history and facts to generate a
    holistic summary and parent prompt using a compatible JSON method.
    """
    context_str = json.dumps(memory.context)
    facts_str = json.dumps(memory.get_facts())
    
    # 1. Generate the JSON schema string from Pydantic model for the LLM to follow
    schema_json = ParentSummary.schema_json(indent=2)

    # Define the role/rules (SYSTEM message content)
    system_instruction = f"""
    You are a professional Mental Health Analyst. Your task is to identify patterns, not make a formal diagnosis.
    You MUST respond with a single JSON object that strictly adheres to the following JSON schema. Do not include any text outside the JSON block:
    {schema_json}
    """
    
    # Define the data/task (USER message content)
    user_task = f"""
    Review the following child's conversation history and personality facts.

    Personality Facts: {facts_str}
    Conversation History: {context_str}

    Based on the evidence, determine if there is a **POSSIBLE** mental health concern (e.g., Anxiety, Depression, Behavioral Issue). Generate the required JSON output.
    """
    
    json_text = "N/A (API call failed)" # Initialize for error reporting
    
    try:
        # Step 1: Call API using compatible response_format and both SYSTEM/USER messages
        # <--- FIX 7: Use 'await' for the API call
        res = await client.chat.completions.create(
            model="asi1-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_task},
            ],
            # Use the compatible response_format
            response_format={"type": "json_object"}
        )
        
        # Step 2: Extract text, CLEAN it, and parse it into a Python dictionary
        json_text = res.choices[0].message.content
        
        # Use the robust helper function for cleaning
        cleaned_json = clean_json_text(json_text)
        
        data = json.loads(cleaned_json)
        
        # Step 3: Validate and convert the parsed dictionary using the Pydantic model
        validated_summary = ParentSummary(**data)
        
        # The output is now guaranteed to be valid and structured
        return validated_summary.model_dump()
        
    except ValidationError as e:
        error_message = f"Pydantic Validation Error: {e.errors()}"
        print(f"⚠️ Parent summary generation failed: {error_message}")
        return {
            "recommendation_needed": False,
            "summary_for_analyst": f"Failed to generate summary. Error: {error_message}",
            "parent_message": "",
            "potential_concerns": ["JSON Validation Error"]
        }
    except Exception as e:
        # Catching generic API or parsing errors (including the original JSONDecodeError)
        error_message = str(e)
        print(f"⚠️ Parent summary generation failed: {error_message}")
        return {
            "recommendation_needed": False,
            "summary_for_analyst": f"Failed to generate summary. Error: {error_message}. Raw LLM output (if available): {json_text}",
            "parent_message": "",
            "potential_concerns": ["API/Parsing Error"]
        }


# --- Core Agent Response Function (Updated) ---

# (This function performs no I/O, so it remains synchronous)
def analyze_for_escalation(user_input: str) -> Dict[str, Any]:
    """
    Analyzes user input against escalation triggers.
    Refined logic to prevent false positives from common words like 'do'.
    """
    alerts = []
    
    # --- REFINED STOP WORDS AND CLEANING ---
    stop_words = {
        "or", "and", "the", "a", "an", "is", "of", "to", "in", "i", "am", "feeling",
        "my", "your", "what", "do", "you", "most", "about", "with", "like", "how",
        "it", "this", "that", "want", "have", "can", "if", "be", "just", "them",
        "for", "at", "but", "so", "sometimes", "are", "really"
    }
    
    lowered_input = user_input.lower()
    cleaned_input_words = set(
        re.findall(r'\b\w+\b', lowered_input)
    ) - stop_words
    
    escalation_triggers = [
        item for item in KNOWLEDGE_BASE
        if item.get("Record_Type") == "ESCALATION_TRIGGER"
    ]

    for trigger in escalation_triggers:
        criteria_keywords = set(
            re.findall(r'\b\w+\b', trigger.get("Criteria", "").lower())
        ) - stop_words
        
        trigger_words_found = list(criteria_keywords.intersection(cleaned_input_words))

        if trigger_words_found:
            alerts.append({
                "trigger_name": trigger.get("Trigger_Name"),
                "level": trigger.get("Category"),
                "action": trigger.get("Action"),
                "found_words": trigger_words_found
            })
            
    return {"alerts": alerts}



# (This function is already async, which is correct)
async def get_agent_response(user_input: str) -> Dict[str, Any]:
    """Use ASI:One model for a reply, run silent analysis, and manage memory."""
    
    # <--- FIX 8: 'await' the async function
    await extract_and_store_facts(user_input)

    # This function is sync, so no await is needed
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
    # <--- FIX 9: 'await' the main API call
    res = await client.chat.completions.create(
        model="asi1-mini",
        messages=[
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": user_input},
        ],
    )
    reply = res.choices[0].message.content.strip()
    
    # 5. Run silent safety analysis (this function is sync)
    safety_analysis = analyze_for_escalation(user_input)

    # 6. Store conversation turn (after analysis) (this is sync)
    memory.remember(user_input, reply)

    # 7. Print entire context for debugging (added for the user's previous request)
    # print("\n--- FULL CONVERSATION LOG (memory.context) ---")
    # print(json.dumps(memory.context, indent=2))
    # print("-------------------------------------------\n")
    
    # Return a structured dictionary
    return {
        "reply": reply,
        "analysis": safety_analysis,
        "facts_updated": memory.get_facts()
    }


# --- New Endpoint for Parent Summary ---
async def generate_parent_summary_response() -> Dict[str, Any]:
    # <--- FIX 10: 'await' the async function
    return await generate_parent_summary()

# <--- FIX 11: Moved this block to the end of the file
if __name__ == "__main__":
    print(f"Starting agent '{agent.name}' on address: {agent.address}")
    agent.run()