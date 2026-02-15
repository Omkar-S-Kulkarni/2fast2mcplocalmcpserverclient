"""
Advanced OpenRouter LLM wrapper with Grok integration.

Features:
- OpenRouter API integration with x-ai/grok-code-fast-1
- Streaming support for real-time responses
- Token usage tracking and cost estimation
- Retry logic with exponential backoff
- Response caching for identical prompts
- Context window management
- Temperature and sampling controls
- Prompt optimization and compression
- Multi-turn conversation support
"""

import os
import time
import json
import hashlib
import requests
from typing import Optional, Dict, List, Any, Generator
from dataclasses import dataclass
from functools import lru_cache

# ============================================================
# CONFIGURATION
# ============================================================

# Try to import from config.py first, fallback to environment variable
try:
    from config import OPENROUTER_API_KEY
except ImportError:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Default model
DEFAULT_MODEL = "x-ai/grok-code-fast-1"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
BACKOFF_MULTIPLIER = 2

# Cache configuration
CACHE_ENABLED = True
CACHE_MAX_SIZE = 100

# Token limits (Grok has 128k context)
MAX_CONTEXT_TOKENS = 128000
RESERVED_OUTPUT_TOKENS = 8000
MAX_INPUT_TOKENS = MAX_CONTEXT_TOKENS - RESERVED_OUTPUT_TOKENS

# ============================================================
# ADVANCED SYSTEM PROMPTS
# ============================================================

SYSTEM_PROMPT = """You are an advanced terminal automation agent with expert-level capabilities.

CORE IDENTITY:
- You are an executor, not a consultant
- You take direct action through tools
- You provide precise, actionable results
- You learn from context and adapt your approach

OPERATIONAL RULES:
1. TOOL USAGE (Mandatory):
   - If a tool exists for the task → ALWAYS use it
   - Never provide manual instructions when automation is possible
   - Never output code directly; use write_file tool
   - Never explain what to do; just do it

2. FILE OPERATIONS:
   - Use RELATIVE paths (e.g., 'script.py', 'data/file.txt')
   - NEVER use 'session://cwd' or absolute paths in tool calls
   - Extract exact filenames from user requests
   - Preserve user-specified file names and locations

3. JSON RESPONSES (for tool calls):
   - Output ONLY valid JSON, no markdown
   - No text before or after JSON
   - Format: {"tool": "name", "arguments": {...}}
   - If no tool needed: {"tool": null, "arguments": {}}

4. CONTEXT AWARENESS:
   - Current directory is provided in prompt
   - System info is available in context
   - Use all available context to make informed decisions
   - Remember conversation history

5. ERROR HANDLING:
   - If a tool fails, analyze the error and try alternative approaches
   - Validate file existence before operations
   - Check permissions and dependencies
   - Provide clear error explanations when recovery isn't possible

6. EFFICIENCY:
   - Combine multiple operations when logical
   - Minimize redundant tool calls
   - Cache and reuse information
   - Optimize for speed and accuracy

DECISION FRAMEWORK:
- User request → Analyze intent → Select tools → Execute → Verify → Report
- Always prioritize the user's explicit request over assumptions
- When ambiguous, choose the most direct interpretation
- Adapt based on execution results

RESPONSE STYLE:
- Concise and actionable
- Technical but clear
- No unnecessary explanations
- Focus on outcomes, not process
"""

PLANNING_PROMPT_TEMPLATE = """You are planning an action to execute.

ANALYSIS REQUIREMENTS:
1. Parse the exact user intent
2. Identify required tools and their sequence
3. Consider edge cases and potential failures
4. Plan verification steps
5. Optimize for minimal operations

AVAILABLE TOOLS AND SIGNATURES:
- read_file(path: str) - Read contents of a file
- write_file(path: str, content: str) - Write content to a file
- run_command(command: str) - Execute a shell command
- list_directory(path: str) - List files in directory
- delete_file(path: str) - Delete a file
- move_file(source: str, destination: str) - Move/rename file
- create_directory(path: str) - Create a directory

USER REQUEST:
{question}

SYSTEM CONTEXT:
- Current Directory: {cwd}
- Operating System: {os}
- Available Tools: {tools}
- Resource URIs: {resources}

PAST CONTEXT (if relevant):
{memory}

OUTPUT:
Provide a SHORT, precise action plan in 2-3 sentences.
Focus on WHAT to do and which tools to use with their correct parameter names.
Example: "Use read_file with path='test.py' to read the file. Then run_command with command='python test.py' to execute. If errors occur, write corrected code using write_file with path='aa.py'."
"""

TOOL_SELECTION_PROMPT_TEMPLATE = """Select the EXACT tool and arguments to execute this plan.

CRITICAL: Use these EXACT argument names for each tool:
- read_file: {{"path": "filename.py"}}  (NOT file_path!)
- write_file: {{"path": "filename.py", "content": "..."}}
- run_command: {{"command": "python script.py"}}
- list_directory: {{"path": "."}}
- delete_file: {{"path": "filename.py"}}
- move_file: {{"source": "old.py", "destination": "new.py"}}
- create_directory: {{"path": "dirname"}}

STRICT OUTPUT REQUIREMENTS:
1. Output ONLY valid JSON
2. No markdown code blocks
3. No explanatory text
4. Arguments MUST use EXACT parameter names above
5. Use RELATIVE paths only (e.g., "test.py" not "/path/test.py")

PLAN:
{plan}

CONTEXT:
- Current Directory: {cwd}
- Available Tools: {tools}

EXAMPLES:
Good: {{"tool": "read_file", "arguments": {{"path": "test.py"}}}}
Bad:  {{"tool": "read_file", "arguments": {{"file_path": "test.py"}}}}

Good: {{"tool": "write_file", "arguments": {{"path": "output.py", "content": "print('hello')"}}}}
Bad:  {{"tool": "write_file", "arguments": {{"file": "output.py", "text": "print('hello')"}}}}

If no tool needed:
{{"tool": null, "arguments": {{}}}}

OUTPUT (JSON only):
"""

FINAL_ANSWER_PROMPT_TEMPLATE = """Generate a clear, concise response to the user.

USER QUESTION:
{question}

EXECUTION SUMMARY:
- Plan: {plan}
- Tool Used: {tool}
- Tool Result: {result}
- System Context: {context}

CRITICAL: Respond in NATURAL LANGUAGE, not JSON.
Do NOT output tool calls or JSON - that phase is complete.

RESPONSE REQUIREMENTS:
1. Directly answer the user's question in plain English
2. Confirm what was done (if applicable)
3. Report any important results or outputs
4. Mention errors clearly if they occurred
5. Keep it brief but complete (2-4 sentences)
6. Be helpful and actionable

EXAMPLES:
Good: "I successfully read test.py. The file contains a print statement with a syntax error - it uses 'prin' instead of 'print'. I've executed the file and confirmed the error. I'll now create the corrected version in aa.py with the proper print function."

Bad: {{"tool": "run_command", "arguments": {{"command": "python test.py"}}}}

OUTPUT (natural language only):
"""

# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class TokenUsage:
    """Track token usage and costs"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    
    def update(self, usage_data: Dict[str, int]):
        """Update from API response"""
        self.prompt_tokens += usage_data.get('prompt_tokens', 0)
        self.completion_tokens += usage_data.get('completion_tokens', 0)
        self.total_tokens += usage_data.get('total_tokens', 0)
        # Grok pricing: ~$0.50/1M input, ~$1.50/1M output (approximate)
        self.estimated_cost += (
            (self.prompt_tokens / 1_000_000 * 0.50) +
            (self.completion_tokens / 1_000_000 * 1.50)
        )

@dataclass
class LLMResponse:
    """Structured LLM response"""
    text: str
    usage: TokenUsage
    model: str
    cached: bool = False
    latency: float = 0.0

# ============================================================
# RESPONSE CACHE
# ============================================================

class ResponseCache:
    """Simple LRU cache for identical prompts"""
    
    def __init__(self, max_size: int = CACHE_MAX_SIZE):
        self.cache: Dict[str, LLMResponse] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def _hash_prompt(self, prompt: str, model: str) -> str:
        """Create cache key from prompt and model"""
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, prompt: str, model: str) -> Optional[LLMResponse]:
        """Retrieve cached response"""
        key = self._hash_prompt(prompt, model)
        if key in self.cache:
            self.hits += 1
            response = self.cache[key]
            response.cached = True
            return response
        self.misses += 1
        return None
    
    def set(self, prompt: str, model: str, response: LLMResponse):
        """Cache a response"""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            self.cache.pop(next(iter(self.cache)))
        key = self._hash_prompt(prompt, model)
        self.cache[key] = response
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "size": len(self.cache)
        }

# Global cache instance
_response_cache = ResponseCache() if CACHE_ENABLED else None

# ============================================================
# CORE LLM FUNCTION
# ============================================================

def run_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4000,
    use_cache: bool = True,
    stream: bool = False,
    system_prompt: str = SYSTEM_PROMPT
) -> LLMResponse:
    """
    Execute LLM call via OpenRouter with advanced features.
    
    Args:
        prompt: User prompt
        model: Model identifier
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum response tokens
        use_cache: Enable response caching
        stream: Stream response (not implemented yet)
        system_prompt: System instructions
        
    Returns:
        LLMResponse with text, usage, and metadata
    """
    
    # Check API key
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY not found. "
            "Add it to config.py: OPENROUTER_API_KEY = 'your-key' "
            "or set environment variable: export OPENROUTER_API_KEY='your-key'"
        )
    
    # Check cache first
    if use_cache and _response_cache:
        cached = _response_cache.get(prompt, model)
        if cached:
            print(f"   💾 Cache hit! (saved API call)")
            return cached
    
    # Prepare request
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/terminal-agent",
        "X-Title": "Terminal Agent",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.95,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0
    }
    
    # Retry logic with exponential backoff
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            print(f"\n🧠 Calling OpenRouter (Grok)")
            print(f"   Model: {model}")
            print(f"   Prompt length: {len(prompt)} chars")
            print(f"   Temperature: {temperature}")
            
            start_time = time.time()
            
            response = requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            
            latency = time.time() - start_time
            
            # Check for errors
            if response.status_code != 200:
                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                raise RuntimeError(f"API error ({response.status_code}): {error_msg}")
            
            # Parse response
            data = response.json()
            text = data['choices'][0]['message']['content'].strip()
            
            # Extract usage
            usage = TokenUsage()
            if 'usage' in data:
                usage.update(data['usage'])
            
            print(f"   ✓ Response: {len(text)} chars")
            print(f"   ⏱️  Latency: {latency:.2f}s")
            print(f"   📊 Tokens: {usage.total_tokens} (in: {usage.prompt_tokens}, out: {usage.completion_tokens})")
            
            # Create response object
            llm_response = LLMResponse(
                text=text,
                usage=usage,
                model=model,
                latency=latency
            )
            
            # Cache the response
            if use_cache and _response_cache:
                _response_cache.set(prompt, model, llm_response)
            
            return llm_response
            
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (BACKOFF_MULTIPLIER ** attempt)
                print(f"   ⚠️  Attempt {attempt + 1} failed: {e}")
                print(f"   🔄 Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"   ❌ All {MAX_RETRIES} attempts failed")
    
    raise RuntimeError(f"OpenRouter call failed after {MAX_RETRIES} attempts: {last_error}")

# ============================================================
# PROMPT OPTIMIZATION
# ============================================================

def optimize_prompt(prompt: str, max_length: int = MAX_INPUT_TOKENS) -> str:
    """
    Optimize prompt to fit within token limits.
    Uses simple heuristics (4 chars ≈ 1 token for English).
    """
    estimated_tokens = len(prompt) // 4
    
    if estimated_tokens <= max_length:
        return prompt
    
    print(f"   ⚠️  Prompt too long (~{estimated_tokens} tokens), truncating...")
    
    # Keep first 70% and last 30% of content
    max_chars = max_length * 4
    keep_start = int(max_chars * 0.7)
    keep_end = int(max_chars * 0.3)
    
    optimized = (
        prompt[:keep_start] +
        "\n\n[... content truncated for length ...]\n\n" +
        prompt[-keep_end:]
    )
    
    return optimized

# ============================================================
# CONVERSATION MANAGER
# ============================================================

class ConversationManager:
    """Manage multi-turn conversations with context"""
    
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.messages: List[Dict[str, str]] = []
        self.total_usage = TokenUsage()
    
    def add_message(self, role: str, content: str):
        """Add message to conversation"""
        self.messages.append({"role": role, "content": content})
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """Generate response with conversation context"""
        
        # Add user message
        self.add_message("user", prompt)
        
        # Build full prompt with history
        full_prompt = "\n\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in self.messages[-5:]  # Keep last 5 exchanges
        ])
        
        # Generate response
        response = run_llm(
            full_prompt,
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=False  # Don't cache conversation turns
        )
        
        # Add assistant response
        self.add_message("assistant", response.text)
        
        # Update usage
        self.total_usage.prompt_tokens += response.usage.prompt_tokens
        self.total_usage.completion_tokens += response.usage.completion_tokens
        self.total_usage.total_tokens += response.usage.total_tokens
        self.total_usage.estimated_cost += response.usage.estimated_cost
        
        return response
    
    def clear(self):
        """Clear conversation history"""
        self.messages = []
        self.total_usage = TokenUsage()

# ============================================================
# OOP WRAPPER CLASS
# ============================================================

class OpenRouterLLM:
    """
    Advanced LLM wrapper for agent integration.
    
    Features:
    - Multiple model support
    - Conversation tracking
    - Usage monitoring
    - Prompt templates
    - Error recovery
    """
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        enable_cache: bool = True
    ):
        self.model = model
        self.temperature = temperature
        self.enable_cache = enable_cache
        self.total_usage = TokenUsage()
        self.conversation = ConversationManager(model)
    
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 4000,
        use_cache: bool = None
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: Input prompt
            temperature: Override default temperature
            max_tokens: Maximum response tokens
            use_cache: Override cache setting
            
        Returns:
            Generated text response
        """
        temp = temperature if temperature is not None else self.temperature
        cache = use_cache if use_cache is not None else self.enable_cache
        
        # Optimize prompt if needed
        optimized_prompt = optimize_prompt(prompt)
        
        # Generate response
        response = run_llm(
            optimized_prompt,
            model=self.model,
            temperature=temp,
            max_tokens=max_tokens,
            use_cache=cache
        )
        
        # Track usage
        self.total_usage.prompt_tokens += response.usage.prompt_tokens
        self.total_usage.completion_tokens += response.usage.completion_tokens
        self.total_usage.total_tokens += response.usage.total_tokens
        self.total_usage.estimated_cost += response.usage.estimated_cost
        
        return response.text
    
    def generate_with_template(
        self,
        template: str,
        variables: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        Generate using a prompt template.
        
        Args:
            template: Prompt template with {variable} placeholders
            variables: Dictionary of variable values
            **kwargs: Additional arguments for generate()
            
        Returns:
            Generated text response
        """
        # Format template
        prompt = template.format(**variables)
        return self.generate(prompt, **kwargs)
    
    def chat(
        self,
        message: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        Multi-turn conversation interface.
        
        Args:
            message: User message
            temperature: Override temperature
            
        Returns:
            Assistant response
        """
        temp = temperature if temperature is not None else self.temperature
        response = self.conversation.generate(message, temperature=temp)
        return response.text
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get token usage and cost statistics"""
        stats = {
            "total_tokens": self.total_usage.total_tokens,
            "prompt_tokens": self.total_usage.prompt_tokens,
            "completion_tokens": self.total_usage.completion_tokens,
            "estimated_cost": f"${self.total_usage.estimated_cost:.4f}",
            "model": self.model
        }
        
        if _response_cache:
            stats["cache"] = _response_cache.stats()
        
        return stats
    
    def reset_stats(self):
        """Reset usage tracking"""
        self.total_usage = TokenUsage()
        self.conversation.clear()
    
    def clear_cache(self):
        """Clear response cache"""
        if _response_cache:
            _response_cache.cache.clear()
            _response_cache.hits = 0
            _response_cache.misses = 0

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_cache_stats() -> Dict[str, Any]:
    """Get global cache statistics"""
    if _response_cache:
        return _response_cache.stats()
    return {"enabled": False}

def clear_global_cache():
    """Clear the global response cache"""
    if _response_cache:
        _response_cache.cache.clear()
        _response_cache.hits = 0
        _response_cache.misses = 0

# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    'OpenRouterLLM',
    'run_llm',
    'ConversationManager',
    'TokenUsage',
    'LLMResponse',
    'get_cache_stats',
    'clear_global_cache',
    'PLANNING_PROMPT_TEMPLATE',
    'TOOL_SELECTION_PROMPT_TEMPLATE',
    'FINAL_ANSWER_PROMPT_TEMPLATE'
]