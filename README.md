# Project Capy: Early Intervention AI Companion
## Overview: The Trust Bridge
Project Capy addresses the challenge that childhood emotional difficulties often go undetected because children are hesitant to confide in adults. Capy is a multi-agent system designed to act as a **non-judgmental AI companion for the child** while providing **structured, actionable intelligence to the adult**.

The core system uses a specialized LLM (ASI:One) to bridge the gap between a child's casual, emotional conversation and a parent/analyst's need for objective, clinical insight.
## Core Features & Capabilities
This system is built around three core generative AI functionalities:
1. **Child Agent (Capy):** A friendly, supportive, and non-clinical persona designed to encourage open dialogue.
- **Persistent Personalization:** Remembers specific facts (favorite hobbies, pets, friends) extracted during the conversation to build rapport and demonstrate genuine listening.
- **Relatable Tone:** Employs age-appropriate language, slang, and emojis to maintain a peer-like connection.
2. **Silent Safety Analysis:** Every message the child sends is immediately and silently evaluated against a clinical knowledge base for keywords and semantic risk indicators (e.g., "sad," "hopeless," "lonely").
- **Structured Output:** Generates a structured JSON analysis with an **Escalation Category** (LOW, MODERATE, HIGH) and a recommended **Action** for the system to log.
3. **Parent Summary & Reporting:** On demand, the system synthesizes the entire conversation log and the extracted facts into a Pydantic-enforced report for the adult.
- **Objective Analysis:** Provides a clear, non-alarming, and objective summary of emotional trends and key topics discussed.
- **Actionable Guidance:** Offers specific recommendations for follow-up actions based on the detected escalation levels.
## ASI:One Discoverability and Sample Prompts
**To ensure the agent is discoverable via ASI:One, this agent implements the **Agent Chat Protocol** and publishes a comprehensive manifest.

The more detailed your prompt is when querying the agent, the better its response.

**Use Case**
**Sample Query**
**Expected Agent Action**
**Rapport Building & Fact Extraction**
"I had a rough day at school, but I saw a cool capybara video. My friend Chloe was with me."
**Capy Agent:** Responds empathetically, references capybaras, and stores favorite_animal: Capybara and friend_name: Chloe in the Facts Base.
**Safety Analysis (LOW)**
"I'm kind of annoyed about a test I failed."
**Capy Agent:** Validates feelings. System: Logs LOW escalation for minor frustration.
**Safety Analysis (HIGH)**
"I feel like things will never get better, and I just want to stop trying."
**Capy Agent:** Responds with non-alarming, supportive language, prioritizing the safe conversation space. **System**: Logs HIGH escalation and triggers the relevant clinical action in the analysis.
**Parent/Analyst Report**
GET /parent_summary (System Query)
**Reporter Agent**: Generates Pydantic-enforced summary: Emotional trends, facts base, and recommended adult intervention steps.

## Architecture and Deployment
The project is built on the **Fetch AI uAgents** framework and **FastAPI** for its core structure.

- **Backend**: Python 3.11+, FastAPI.
- **LLM Integration**: ASI:One (used for all generative/reasoning tasks).
- **Data Storage**: Custom JSONMemory for managing Conversation History and Facts Base.
## Key Deployment Files
- *server/main.py:* Defines the FastAPI endpoints and initializes the agent components.
- *server/agent.py*: Contains the core logic for get_agent_response, fact extraction, and safety analysis using the ASI:One LLM.
- *server/json_memory.py:* Handles persistent storage of conversation context and extracted facts.
