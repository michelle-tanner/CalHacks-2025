# child_agent/server/json_memory.py
import json, os, random

class JSONMemory:
    def __init__(self, filename="memory.json"):
        self.filename = filename
        self._load()

    def _load(self):
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                self.context = data.get("context", [])
                # --- NEW: Stores facts about the child ---
                self.facts = data.get("facts", {})
                # ------------------------------------------
        except (FileNotFoundError, json.JSONDecodeError):
            self.context = []
            self.facts = {}

    def _save(self):
        data = {
            "context": self.context,
            "facts": self.facts
        }
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=4)

    def remember(self, user_input: str, agent_reply: str):
        """Adds a turn to the conversation context."""
        self.context.append({"user": user_input, "agent": agent_reply})
        self._save()
        
    def add_fact(self, key: str, value: str):
        """Adds a fact to the child's personality profile."""
        self.facts[key] = value
        self._save()

    def get_facts(self) -> dict:
        """Returns the current stored facts about the child."""
        return self.facts

    def clear(self):
        """Clears all context and facts."""
        self.context = []
        self.facts = {}
        self._save()

# Initialize memory instance
memory = JSONMemory()


