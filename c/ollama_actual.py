# ollama_llm.py
"""
Ollama LLM wrapper for local model execution.

Features:
- Uses Ollama Python API (persistent connection → faster)
- Single source of truth for model (config.py)
- Timeout handling
- Debug logging for MCP troubleshooting
"""



# ============================================================
# GLOBAL SYSTEM PROMPT (FOR TOOL-CORRECT BEHAVIOR)
# ============================================================

SYSTEM_PROMPT = """
You are a terminal automation agent.

CRITICAL RULES:
1. If a task can be done using a tool, you MUST use the tool.
2. Never give manual instructions when a tool exists.
3. Never explain code.
4. Never output code directly.
5. Always return valid JSON when a tool is required.
6. Format for tool use:

{
  "tool": "<tool_name>",
  "arguments": { ... }
}

7. Do not add any text outside JSON.
8. Current working directory is already provided — do NOT read session://cwd.
9. Keep responses short and action-focused.
"""


import ollama
from config import OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS


# ============================================================
# LOW-LEVEL FUNCTION
# Used directly by client.py: from ollama_llm import run_llm
# ============================================================

def run_llm(prompt: str, model: str = None) -> str:
    """
    Local LLM call using Ollama Python API.

    Args:
        prompt: Text prompt to send
        model: Optional model override (defaults to config.OLLAMA_MODEL)

    Returns:
        Model response text
    """
    model_to_use = model or OLLAMA_MODEL

    try:
        # Debug info (very useful for MCP debugging)
        print(f"\n🧠 Calling Ollama model: {model_to_use}")
        print(f"   Prompt length: {len(prompt)} chars")

        response = ollama.chat(
            model=model_to_use,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
                
            options={
                "timeout": OLLAMA_TIMEOUT_SECONDS
            }
        )

        text = response["message"]["content"].strip()

        print(f"   Response length: {len(text)} chars")
        return text

    except Exception as e:
        raise RuntimeError(f"Ollama execution failed: {e}")


# ============================================================
# CLASS WRAPPER
# Used by agent.py:
#     self.llm = OllamaLLM(model="deepseek-r1")
#     self.llm.generate(prompt)
# ============================================================

class OllamaLLM:
    """
    Thin OOP wrapper around run_llm().
    Allows agent to call: llm.generate(prompt)
    """

    def __init__(self, model: str = None):
        # If model provided → use it
        # else → fallback to config
        self.model = model or OLLAMA_MODEL

    def generate(self, prompt: str) -> str:
        """Run the prompt through the local LLM and return the text."""
        return run_llm(prompt, self.model)