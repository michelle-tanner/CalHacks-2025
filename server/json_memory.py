# child_agent/server/json_memory.py
import json, os, random

class JsonMemory:
    def __init__(self, folder="data/responses"):
        self.folder = folder
        self.memory_file = "data/learning_log.json"
        os.makedirs(self.folder, exist_ok=True)
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)

        # Validate or create learning log
        self.context = self._safe_load_json(self.memory_file, default=[])

        # Validate all response JSON files on startup
        self._check_response_files()

    def _safe_load_json(self, path, default):
        """Load a JSON file safely; reset if missing or corrupt."""
        if not os.path.exists(path) or os.stat(path).st_size == 0:
            with open(path, "w") as f:
                json.dump(default, f)
            return default
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"⚠️ JSON file {path} invalid ({e}) — resetting.")
            with open(path, "w") as f:
                json.dump(default, f)
            return default

    def _check_response_files(self):
        """Ensure all .json files under data/responses are valid."""
        for filename in os.listdir(self.folder):
            if filename.endswith(".json"):
                path = os.path.join(self.folder, filename)
                self._safe_load_json(path, {"responses": []})

    def load_category(self, mood: str) -> str:
        """Return a friendly line from a mood category."""
        path = os.path.join(self.folder, f"{mood}.json")
        data = self._safe_load_json(path, {"responses": []})
        if not data.get("responses"):
            return "It's okay to feel that way. I'm here for you."
        return random.choice(data["responses"])

    def remember(self, user_text, bot_text):
        """Append conversation to memory safely."""
        self.context.append({"user": user_text, "bot": bot_text})
        with open(self.memory_file, "w") as f:
            json.dump(self.context, f, indent=2)

memory = JsonMemory()
