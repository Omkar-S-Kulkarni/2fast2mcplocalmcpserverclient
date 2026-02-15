# memory.py

import json
import os
import time

MEMORY_FILE = "terminal_memory.json"


class LongTermMemory:
    """
    Persistent memory across runs for terminal interactions
    Stores command history, results, and learning
    """

    def __init__(self):
        self.memory = []
        self._load()

    def _load(self):
        """Load memory from disk if it exists"""
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r") as f:
                    self.memory = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load memory: {e}")
                self.memory = []

    def _save(self):
        """Save memory to disk"""
        try:
            with open(MEMORY_FILE, "w") as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save memory: {e}")

    def store(self, item, source="unknown"):
        """Store a new item in memory"""
        entry = {
            "timestamp": time.time(),
            "source": source,
            "data": item,
        }
        self.memory.append(entry)
        self._save()

    def retrieve(self, limit=10):
        """Retrieve recent memory items"""
        return self.memory[-limit:]

    def search(self, keyword):
        """Search memory for items containing keyword"""
        results = []
        for entry in self.memory:
            data_str = str(entry.get("data", "")).lower()
            if keyword.lower() in data_str:
                results.append(entry)
        return results

    def clear(self):
        """Clear all memory"""
        self.memory = []
        self._save()
