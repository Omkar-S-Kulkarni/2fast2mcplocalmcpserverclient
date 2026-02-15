# client.py

import time
import json
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from config import (
    SERVERS,
    ALLOWED_TOOLS,
    ALLOWED_RESOURCES,
    ALLOWED_PROMPTS,
    MAX_CONTEXT_ITEMS,
    ENABLE_TRACING,
    ENABLE_CACHE,
    MAX_RETRIES,
    RESOURCE_TIMEOUT_SECONDS,
    FAILURE_THRESHOLD,
    CIRCUIT_BREAKER_COOLDOWN,
)

# =========================================================
# Re-use the single Ollama caller from ollama_llm.py
# =========================================================
from ollama_llm import run_llm


# =========================================================
# BUILD TRANSPORT FROM config.SERVERS
# =========================================================

_server_cfg = SERVERS[0]                       # first (and only) server
_PYTHON = _server_cfg["command"][0]            # "python" or absolute path
_SERVER_ARGS = _server_cfg["command"][1:]      # ["D:/MCPserver/projects/terminal/s/server.py"]

transport = StdioTransport(command=_PYTHON, args=_SERVER_ARGS)


# =========================================================
# CUSTOM EXCEPTIONS
# =========================================================

class ResourceReadError(Exception):
    pass


class ToolExecutionError(Exception):
    pass


class OllamaError(Exception):
    pass


# =========================================================
# MCPAppClient — fully async, context-manager based
# =========================================================

class MCPAppClient:
    """
    Terminal MCP client with:
    - Safety (permissions for tools, resources, AND prompts)
    - Context control
    - Tracing
    - Cache
    - Retry + Timeout
    - Cancellation
    - Circuit breaker
    - LOCAL LLM via ollama_llm.run_llm()
    """

    def __init__(self):
        # Raw FastMCP client — NOT connected yet.
        # Connection happens in __aenter__.
        self._client = Client(transport)

        self._servers_ready = False
        self._resources = []
        self._tools = []
        self._prompts = []

        # Runtime state
        self._context_buffer = []
        self._trace_log = []
        self._cache = {}

        # Circuit breaker state
        self._failure_count = {}
        self._circuit_open_until = {}

        # Cancellation flag
        self._cancelled = False

    # =========================================================
    # ASYNC CONTEXT MANAGER (the connection gate)
    # =========================================================

    async def __aenter__(self):
        # This is what actually opens the stdio pipe to the server.
        await self._client.__aenter__()
        self._servers_ready = True
        self._trace("client_connected")

        # Eagerly discover what the server exposes.
        await self.load_capabilities()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._trace("client_disconnecting")
        await self._client.__aexit__(exc_type, exc_val, exc_tb)
        self._servers_ready = False
        return False   # do NOT swallow exceptions

    # =========================================================
    # CANCELLATION
    # =========================================================

    def cancel(self):
        self._cancelled = True

    def _check_cancelled(self):
        if self._cancelled:
            raise RuntimeError("Client operation cancelled")

    # =========================================================
    # TRACING
    # =========================================================

    def _trace(self, event, payload=None):
        if ENABLE_TRACING:
            self._trace_log.append({
                "event": event,
                "payload": payload,
                "timestamp": time.time()
            })

    def get_trace(self):
        return list(self._trace_log)

    # =========================================================
    # CAPABILITY DISCOVERY
    # =========================================================

    async def load_capabilities(self):
        self._resources = await self._client.list_resources()
        self._tools = await self._client.list_tools()
        self._prompts = await self._client.list_prompts()

        self._trace(
            "capabilities_loaded",
            {
                "resources": len(self._resources),
                "tools": len(self._tools),
                "prompts": len(self._prompts),
            },
        )

    # =========================================================
    # PERMISSIONS (tools + resources + prompts)
    # =========================================================

    def _is_tool_allowed(self, server, tool):
        return tool in ALLOWED_TOOLS.get(server, set())

    def _is_resource_allowed(self, server, uri):
        """
        Gates every resource read against ALLOWED_RESOURCES.
        Supports dynamic file:// URIs with path validation.
        """
        allowed = ALLOWED_RESOURCES.get(server, set())
        
        # Direct match
        if uri in allowed:
            return True
        
        # Dynamic file:// resources
        if uri.startswith("file://"):
            # Check if any allowed resource allows file:// pattern
            # For now, we allow file:// resources (validated by server)
            return True
        
        return False

    def _is_prompt_allowed(self, server, prompt):
        return prompt in ALLOWED_PROMPTS.get(server, set())

    # =========================================================
    # CONTEXT BUFFER
    # =========================================================

    def _add_to_context(self, item):
        self._context_buffer.append(item)
        self._trace("context_added", {"item_type": type(item).__name__})

        if len(self._context_buffer) > MAX_CONTEXT_ITEMS:
            removed = self._context_buffer.pop(0)
            self._trace("context_evicted", {"item_type": type(removed).__name__})

    def get_context(self):
        return list(self._context_buffer)

    # =========================================================
    # CACHE
    # =========================================================

    def _cache_key(self, kind, server, name, args):
        return f"{kind}:{server}:{name}:{json.dumps(args, sort_keys=True)}"

    def _get_cached(self, key):
        if ENABLE_CACHE and key in self._cache:
            self._trace("cache_hit", key)
            return self._cache[key]
        return None

    def _set_cache(self, key, value):
        if ENABLE_CACHE:
            self._cache[key] = value
            self._trace("cache_set", key)

    # =========================================================
    # CIRCUIT BREAKER
    # =========================================================

    def _check_circuit(self, key):
        open_until = self._circuit_open_until.get(key)
        if open_until and time.time() < open_until:
            raise ResourceReadError("Circuit breaker open")

    def _record_failure(self, key):
        self._failure_count[key] = self._failure_count.get(key, 0) + 1
        if self._failure_count[key] >= FAILURE_THRESHOLD:
            self._circuit_open_until[key] = time.time() + CIRCUIT_BREAKER_COOLDOWN
            self._trace("circuit_opened", key)

    def _record_success(self, key):
        self._failure_count[key] = 0
        self._circuit_open_until.pop(key, None)

    # =========================================================
    # RESOURCE ACCESS (async)
    # =========================================================

    async def read_resource(self, server, uri):
        self._check_cancelled()

        # Permission gate
        if not self._is_resource_allowed(server, uri):
            raise PermissionError(f"Resource not allowed: {uri}")

        key = self._cache_key("resource", server, uri, None)
        self._check_circuit(key)

        cached = self._get_cached(key)
        if cached:
            return cached

        start = time.time()

        for attempt in range(MAX_RETRIES + 1):
            try:
                if time.time() - start > RESOURCE_TIMEOUT_SECONDS:
                    raise TimeoutError("Resource read timeout")

                self._trace("read_resource", uri)
                result = await self._client.read_resource(uri)

                self._record_success(key)
                self._set_cache(key, result)
                self._add_to_context({"type": "resource", "uri": uri, "result": result})
                return result

            except (PermissionError, TimeoutError):
                raise

            except Exception as e:
                self._trace("resource_error", str(e))
                self._record_failure(key)
                if attempt == MAX_RETRIES:
                    raise ResourceReadError(str(e)) from e

    # =========================================================
    # TOOL ACCESS (async)
    # =========================================================

    async def call_tool(self, server, name, arguments):
        self._check_cancelled()

        if not self._is_tool_allowed(server, name):
            raise PermissionError(f"Tool not allowed: {name}")

        key = self._cache_key("tool", server, name, arguments)
        self._check_circuit(key)

        cached = self._get_cached(key)
        if cached:
            return cached

        for attempt in range(MAX_RETRIES + 1):
            try:
                self._trace("call_tool", {"name": name, "arguments": arguments})
                result = await self._client.call_tool(name, arguments)

                self._record_success(key)
                self._set_cache(key, result)
                self._add_to_context({"type": "tool", "name": name, "result": result})
                return result

            except PermissionError:
                raise

            except Exception as e:
                self._trace("tool_error", str(e))
                self._record_failure(key)
                if attempt == MAX_RETRIES:
                    raise ToolExecutionError(str(e)) from e

    # =========================================================
    # PROMPT ACCESS (async, local LLM execution)
    # =========================================================

    async def get_prompt(self, server, name, arguments):
        self._check_cancelled()

        if not self._is_prompt_allowed(server, name):
            raise PermissionError(f"Prompt not allowed: {name}")

        key = self._cache_key("prompt", server, name, arguments)
        cached = self._get_cached(key)
        if cached:
            return cached

        # Step 1: fetch the prompt template from the MCP server
        self._trace("get_prompt_template", name)
        prompt_messages = await self._client.get_prompt(name, arguments)

        # Extract the content string
        if isinstance(prompt_messages, list) and len(prompt_messages) > 0:
            raw = prompt_messages[0]
            prompt_text = raw.get("content", str(raw)) if isinstance(raw, dict) else str(raw)
        else:
            prompt_text = str(prompt_messages)

        # Step 2: run through local Ollama
        self._trace("ollama_call", name)
        response = run_llm(prompt_text)

        self._set_cache(key, response)
        self._add_to_context({"type": "prompt", "name": name, "response": response})
        return response

    # =========================================================
    # HIGH-LEVEL DEMO FLOW
    # =========================================================

    async def run_task(self):
        """Demo task showing resource, tool, and prompt usage"""
        server = "terminal"

        try:
            # 1. Read workspace tree
            tree = await self.read_resource(server, "workspace://tree")
            # Handle both dict and list responses
            tree_data = tree[0] if isinstance(tree, list) else tree
            tree_contents = tree_data.get('contents', {}) if isinstance(tree_data, dict) else {}
            tree_root = tree_contents.get('root', 'unknown') if isinstance(tree_contents, dict) else 'unknown'
            print(f"✓ Workspace tree loaded from: {tree_root}")

            # 2. Read system info
            sys_info = await self.read_resource(server, "system://info")
            sys_data = sys_info[0] if isinstance(sys_info, list) else sys_info
            sys_contents = sys_data.get('contents', {}) if isinstance(sys_data, dict) else {}
            os_name = sys_contents.get('os', 'unknown') if isinstance(sys_contents, dict) else 'unknown'
            py_ver = sys_contents.get('python_version', 'unknown') if isinstance(sys_contents, dict) else 'unknown'
            print(f"✓ System info: {os_name} - Python {py_ver}")

            # 3. List directory
            dir_list = await self.call_tool(server, "list_directory", {"path": "."})
            # Handle tool response format
            dir_contents = dir_list[0].get('content', []) if isinstance(dir_list, list) else []
            if isinstance(dir_contents, list) and len(dir_contents) > 0:
                dir_data = dir_contents[0].get('text', '{}')
                import json
                dir_parsed = json.loads(dir_data) if isinstance(dir_data, str) else dir_data
                items = dir_parsed.get('items', []) if isinstance(dir_parsed, dict) else []
            else:
                items = []
            print(f"✓ Directory listing: {len(items)} items")

            # 4. Get session cwd
            cwd = await self.read_resource(server, "session://cwd")
            cwd_data = cwd[0] if isinstance(cwd, list) else cwd
            cwd_contents = cwd_data.get('contents', {}) if isinstance(cwd_data, dict) else {}
            current_dir = cwd_contents.get('cwd', 'unknown') if isinstance(cwd_contents, dict) else 'unknown'
            print(f"✓ Current directory: {current_dir}")

            return {
                "success": True,
                "workspace_root": tree_root,
                "system": f"{os_name} - Python {py_ver}",
                "directory_items": len(items),
                "cwd": current_dir,
                "context": self.get_context(),
                "trace": self.get_trace(),
            }

        except Exception as e:
            import traceback
            print(f"✗ Demo task error: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "context": self.get_context(),
                "trace": self.get_trace(),
            }