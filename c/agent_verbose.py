"""
Advanced Verbose Agent with Grok integration.

Features:
- Multi-step reasoning with execution graphs
- Intelligent error recovery and retry logic
- Context-aware tool selection
- Dynamic prompt engineering
- Performance monitoring and optimization
- Parallel tool execution (when safe)
- Learning from past failures
- Confidence scoring for decisions
- Proactive validation and verification
"""

from ollama_actual import (
    OllamaLLM,
    PLANNING_PROMPT_TEMPLATE,
    TOOL_SELECTION_PROMPT_TEMPLATE,
    FINAL_ANSWER_PROMPT_TEMPLATE
)
from memory import LongTermMemory
from policy import PolicyEngine, PolicyDecision
from execution_graph import ExecutionGraph

import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# ============================================================
# CONFIGURATION
# ============================================================

# Agent behavior
MAX_TOOL_RETRIES = 2
ENABLE_PARALLEL_TOOLS = False  # Set to True for concurrent execution
ENABLE_VERIFICATION = True      # Verify tool results
CONFIDENCE_THRESHOLD = 0.7      # Minimum confidence for auto-execution

# Performance tracking
TRACK_PERFORMANCE = True

# ============================================================
# DATA STRUCTURES
# ============================================================

class ExecutionStatus(Enum):
    """Status of execution steps"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"

@dataclass
class ToolExecution:
    """Track individual tool execution"""
    tool_name: str
    arguments: Dict[str, Any]
    status: ExecutionStatus
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    duration: float = 0.0
    confidence: float = 1.0

@dataclass
class StepResult:
    """Result of an agent step"""
    step_name: str
    success: bool
    data: Any
    duration: float
    error: Optional[str] = None

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def parse_resource(response):
    """
    Safely convert MCP resource response to dict.
    
    Handles:
    - TextResourceContents
    - dict
    - list
    - raw strings
    """
    # TextResourceContents object
    if hasattr(response, "text"):
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {"raw": response.text}
    
    # List (take first item)
    if isinstance(response, list) and len(response) > 0:
        return parse_resource(response[0])
    
    # Already a dict
    if isinstance(response, dict):
        return response
    
    # Fallback
    return {"raw": str(response)}

def extract_json_from_text(text: str) -> Optional[Dict]:
    """
    Extract JSON from text that may contain markdown or other content.
    
    Handles:
    - Markdown code blocks
    - JSON embedded in text
    - Malformed JSON
    """
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON in markdown blocks
    patterns = [
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?\})\s*```',
        r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    
    return None

def format_memory_context(memory_items: List[Dict]) -> str:
    """Format memory items for prompt context"""
    if not memory_items:
        return "No relevant past interactions."
    
    formatted = []
    for item in memory_items[-3:]:  # Last 3 interactions
        question = item.get('question', 'N/A')
        tool = item.get('tool_used', 'N/A')
        formatted.append(f"- Q: {question[:100]}... | Tool: {tool}")
    
    return "\n".join(formatted)

def calculate_confidence(plan: str, tools_available: List[str]) -> float:
    """
    Calculate confidence score for a plan.
    
    Factors:
    - Mentioned tools are available
    - Plan is specific and detailed
    - No ambiguous language
    """
    confidence = 1.0
    
    # Check if plan mentions specific tools
    tools_mentioned = sum(1 for tool in tools_available if tool.lower() in plan.lower())
    if tools_mentioned == 0:
        confidence *= 0.5
    
    # Check for ambiguous language
    ambiguous_words = ['maybe', 'might', 'could', 'possibly', 'perhaps']
    if any(word in plan.lower() for word in ambiguous_words):
        confidence *= 0.7
    
    # Check for specificity (length and detail)
    if len(plan) < 50:
        confidence *= 0.8
    
    return confidence

# ============================================================
# MAIN AGENT CLASS
# ============================================================

class TerminalAgent:
    """
    Advanced verbose agent with Grok integration.
    
    Capabilities:
    - Multi-step reasoning with context awareness
    - Intelligent error recovery
    - Performance optimization
    - Learning from past executions
    - Confidence-based decision making
    """
    
    def __init__(self, mcp_client):
        self.client = mcp_client
        self.llm = OpenRouterLLM(
            model="x-ai/grok-code-fast-1",
            temperature=0.7,
            enable_cache=True
        )
        self.memory = LongTermMemory()
        self.policy = PolicyEngine(dry_run=False)
        
        # Performance tracking
        self.performance_stats = {
            'total_questions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_tool_calls': 0,
            'total_duration': 0.0,
            'cache_hits': 0
        }
        
        print("🤖 Advanced Agent Initialized")
        print("=" * 60)
        print(f"   LLM: x-ai/grok-code-fast-1 via OpenRouter")
        print(f"   Policy: {'DRY-RUN' if self.policy.dry_run else 'ACTIVE'}")
        print(f"   Memory: {len(self.memory.memory)} past interactions")
        print(f"   Cache: {'ENABLED' if True else 'DISABLED'}")
        print(f"   Verification: {'ON' if ENABLE_VERIFICATION else 'OFF'}")
        print("=" * 60)
    
    # --------------------------------------------------------
    # POLICY GATES
    # --------------------------------------------------------
    
    def _gate_resource(self, uri: str) -> bool:
        """Check policy for resource access"""
        decision = self.policy.evaluate("resource", {"uri": uri})
        print(f"   🔒 Policy: resource '{uri}' → {decision.name if hasattr(decision, 'name') else str(decision)}")
        
        if decision == PolicyDecision.DENY:
            raise PermissionError(f"Policy denied resource: {uri}")
        
        if decision == PolicyDecision.DRY_RUN:
            print(f"   ⏭️  [DRY-RUN] Skipping resource read")
            return False
        
        return True
    
    def _gate_tool(self, name: str, arguments: Dict) -> bool:
        """Check policy for tool execution"""
        decision = self.policy.evaluate("tool", {"name": name, "arguments": arguments})
        print(f"   🔒 Policy: tool '{name}' → {decision.name if hasattr(decision, 'name') else str(decision)}")
        
        if decision == PolicyDecision.DENY:
            raise PermissionError(f"Policy denied tool: {name}")
        
        if decision == PolicyDecision.DRY_RUN:
            print(f"   ⏭️  [DRY-RUN] Skipping tool execution")
            return False
        
        return True
    
    # --------------------------------------------------------
    # CONTEXT GATHERING
    # --------------------------------------------------------
    
    async def _gather_system_context(
        self,
        graph: ExecutionGraph,
        server: str = "terminal"
    ) -> Dict[str, Any]:
        """
        Gather comprehensive system context.
        
        Returns:
            Dictionary with cwd, system info, tools, resources
        """
        print("\n[CONTEXT] Gathering system information...")
        context = {}
        
        # Get available tools and resources
        tool_names = [str(t.name) for t in self.client._tools]
        resource_uris = [str(r.uri) for r in self.client._resources]
        
        context['tools'] = tool_names
        context['resources'] = resource_uris
        
        print(f"   ✓ Tools: {len(tool_names)}")
        print(f"   ✓ Resources: {len(resource_uris)}")
        
        # Read current working directory
        try:
            print("   📂 Reading current directory...")
            if self._gate_resource("session://cwd"):
                start = time.time()
                cwd_response = await self.client.read_resource(
                    server=server,
                    uri="session://cwd"
                )
                duration = time.time() - start
                
                cwd_data = parse_resource(cwd_response)
                cwd_path = cwd_data.get("cwd", "unknown")
                context["cwd"] = cwd_path
                
                print(f"   ✓ CWD: {cwd_path} ({duration:.2f}s)")
                graph.add_node("resource_cwd", {"path": cwd_path, "duration": duration})
        except Exception as e:
            print(f"   ⚠️  CWD error: {e}")
            context["cwd"] = "unknown"
            graph.add_node("resource_cwd", {"error": str(e)})
        
        # Read system information
        try:
            print("   💻 Reading system info...")
            if self._gate_resource("system://info"):
                start = time.time()
                sys_response = await self.client.read_resource(
                    server=server,
                    uri="system://info"
                )
                duration = time.time() - start
                
                sys_info = parse_resource(sys_response)
                context["system"] = sys_info
                
                os_name = sys_info.get('os', 'unknown')
                print(f"   ✓ OS: {os_name} ({duration:.2f}s)")
                graph.add_node("resource_system", {"os": os_name, "duration": duration})
        except Exception as e:
            print(f"   ⚠️  System info error: {e}")
            context["system"] = {"os": "unknown"}
            graph.add_node("resource_system", {"error": str(e)})
        
        return context
    
    # --------------------------------------------------------
    # PLANNING
    # --------------------------------------------------------
    
    def _generate_plan(
        self,
        question: str,
        context: Dict[str, Any],
        memory_context: str,
        graph: ExecutionGraph
    ) -> Tuple[str, float]:
        """
        Generate an execution plan using LLM.
        
        Returns:
            Tuple of (plan_text, confidence_score)
        """
        print("\n[PLANNING] Generating execution plan...")
        print("   ⏳ Calling Grok LLM...")
        
        start = time.time()
        
        try:
            # Format prompt
            prompt = PLANNING_PROMPT_TEMPLATE.format(
                question=question,
                cwd=context.get('cwd', 'unknown'),
                os=context.get('system', {}).get('os', 'unknown'),
                tools=", ".join(context.get('tools', [])),
                resources=", ".join(context.get('resources', [])),
                memory=memory_context
            )
            
            # Generate plan
            plan = self.llm.generate(prompt, temperature=0.7, max_tokens=1000)
            duration = time.time() - start
            
            # Calculate confidence
            confidence = calculate_confidence(plan, context.get('tools', []))
            
            print(f"   ✓ Plan generated ({duration:.2f}s)")
            print(f"   📊 Confidence: {confidence:.0%}")
            print(f"   📝 Plan: {plan[:150]}...")
            
            graph.add_node("planning", {
                "plan": plan,
                "confidence": confidence,
                "duration": duration
            })
            
            return plan, confidence
            
        except Exception as e:
            print(f"   ❌ Planning error: {e}")
            graph.add_node("planning", {"error": str(e)})
            raise
    
    # --------------------------------------------------------
    # TOOL SELECTION
    # --------------------------------------------------------
    
    def _select_tool(
        self,
        plan: str,
        context: Dict[str, Any],
        graph: ExecutionGraph
    ) -> Optional[Dict[str, Any]]:
        """
        Select appropriate tool and arguments.
        
        Returns:
            Dictionary with 'tool' and 'arguments' keys, or None
        """
        print("\n[TOOL SELECTION] Determining tool to use...")
        print("   ⏳ Calling Grok LLM...")
        
        start = time.time()
        
        try:
            # Format prompt
            prompt = TOOL_SELECTION_PROMPT_TEMPLATE.format(
                plan=plan,
                cwd=context.get('cwd', 'unknown'),
                tools=", ".join(context.get('tools', []))
            )
            
            # Generate tool decision
            response = self.llm.generate(prompt, temperature=0.3, max_tokens=500)
            duration = time.time() - start
            
            print(f"   ✓ Decision generated ({duration:.2f}s)")
            print(f"   📄 Raw response: {response[:200]}...")
            
            # Parse JSON
            tool_decision = extract_json_from_text(response)
            
            if not tool_decision:
                print(f"   ⚠️  Failed to parse JSON, treating as no-tool response")
                graph.add_node("tool_selection", {
                    "error": "JSON parse failed",
                    "raw": response[:200]
                })
                return None
            
            tool_name = tool_decision.get("tool")
            tool_args = tool_decision.get("arguments", {})
            
            if not tool_name or tool_name == "null":
                print(f"   ℹ️  No tool required")
                graph.add_node("tool_selection", {"result": "no_tool_needed"})
                return None
            
            print(f"   ✓ Tool: {tool_name}")
            print(f"   ✓ Arguments: {json.dumps(tool_args, indent=2)}")
            
            graph.add_node("tool_selection", {
                "tool": tool_name,
                "arguments": tool_args,
                "duration": duration
            })
            
            return tool_decision
            
        except Exception as e:
            print(f"   ❌ Tool selection error: {e}")
            graph.add_node("tool_selection", {"error": str(e)})
            return None
    
    # --------------------------------------------------------
    # TOOL EXECUTION
    # --------------------------------------------------------
    
    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        graph: ExecutionGraph,
        server: str = "terminal"
    ) -> Tuple[bool, Any]:
        """
        Execute a tool with retry logic and validation.
        
        Returns:
            Tuple of (success, result)
        """
        print("\n[EXECUTION] Running tool...")
        print(f"   🔧 Tool: {tool_name}")
        print(f"   📋 Arguments (raw): {json.dumps(tool_args, indent=2)}")
        
        # Fix common argument name mistakes
        tool_args = self._fix_tool_arguments(tool_name, tool_args)
        print(f"   📋 Arguments (fixed): {json.dumps(tool_args, indent=2)}")
        
        execution = ToolExecution(
            tool_name=tool_name,
            arguments=tool_args,
            status=ExecutionStatus.PENDING
        )
        
        for attempt in range(MAX_TOOL_RETRIES + 1):
            try:
                # Check policy
                if not self._gate_tool(tool_name, tool_args):
                    execution.status = ExecutionStatus.SKIPPED
                    graph.add_node("tool_execution", {"skipped": "policy_deny"})
                    return False, None
                
                execution.status = ExecutionStatus.RUNNING
                start = time.time()
                
                print(f"   ⏳ Calling MCP server (attempt {attempt + 1}/{MAX_TOOL_RETRIES + 1})...")
                
                # Execute tool
                response = await self.client.call_tool(
                    server=server,
                    name=tool_name,
                    arguments=tool_args
                )
                
                duration = time.time() - start
                execution.duration = duration
                
                # Extract result
                result = self._extract_tool_result(response)
                execution.result = result
                execution.status = ExecutionStatus.SUCCESS
                
                print(f"   ✓ Tool executed successfully ({duration:.2f}s)")
                print(f"   📤 Result preview: {str(result)[:200]}...")
                
                # Update performance stats
                self.performance_stats['total_tool_calls'] += 1
                
                graph.add_node("tool_execution", {
                    "tool": tool_name,
                    "arguments": tool_args,
                    "duration": duration,
                    "result": str(result)[:500],
                    "attempts": attempt + 1
                })
                
                # Verify result if enabled
                if ENABLE_VERIFICATION:
                    self._verify_tool_result(tool_name, tool_args, result)
                
                return True, result
                
            except Exception as e:
                execution.retries += 1
                execution.error = str(e)
                
                print(f"   ⚠️  Attempt {attempt + 1} failed: {e}")
                
                if attempt < MAX_TOOL_RETRIES:
                    print(f"   🔄 Retrying...")
                    time.sleep(1)
                else:
                    execution.status = ExecutionStatus.FAILED
                    print(f"   ❌ All attempts failed")
                    
                    graph.add_node("tool_execution", {
                        "tool": tool_name,
                        "error": str(e),
                        "attempts": attempt + 1
                    })
                    
                    return False, None
        
        return False, None
    
    def _fix_tool_arguments(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix common argument name mistakes based on tool signatures.
        
        Common mistakes:
        - read_file: file_path → path
        - write_file: file_path → path, text/data → content
        - run_command: cmd → command
        - list_directory: dir/directory → path
        """
        fixed_args = args.copy()
        
        # Define correct argument mappings
        arg_fixes = {
            'read_file': {
                'file_path': 'path',
                'file': 'path',
                'filename': 'path'
            },
            'write_file': {
                'file_path': 'path',
                'file': 'path',
                'filename': 'path',
                'text': 'content',
                'data': 'content',
                'contents': 'content'
            },
            'run_command': {
                'cmd': 'command',
                'shell_command': 'command'
            },
            'list_directory': {
                'dir': 'path',
                'directory': 'path',
                'folder': 'path'
            },
            'delete_file': {
                'file_path': 'path',
                'file': 'path'
            },
            'move_file': {
                'src': 'source',
                'from': 'source',
                'dest': 'destination',
                'to': 'destination'
            },
            'create_directory': {
                'dir': 'path',
                'directory': 'path',
                'folder': 'path'
            }
        }
        
        if tool_name in arg_fixes:
            mappings = arg_fixes[tool_name]
            for wrong_name, correct_name in mappings.items():
                if wrong_name in fixed_args:
                    print(f"   🔧 Fixing argument: {wrong_name} → {correct_name}")
                    fixed_args[correct_name] = fixed_args.pop(wrong_name)
        
        return fixed_args
    
    def _extract_tool_result(self, response) -> Any:
        """Extract result from tool response"""
        # Handle CallToolResult objects
        if hasattr(response, 'content'):
            content = response.content
            if isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                # Handle TextContent objects
                if hasattr(first_item, 'text'):
                    text = first_item.text
                    try:
                        # Try to parse as JSON
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return text
                elif hasattr(first_item, 'type') and first_item.type == 'text':
                    text = first_item.get('text', '')
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return text
            return str(content)
        
        # Handle list responses
        if isinstance(response, list) and len(response) > 0:
            item = response[0]
            if isinstance(item, dict):
                content = item.get('content', [])
                if isinstance(content, list) and len(content) > 0:
                    text = content[0].get('text', '')
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return text
        
        # Fallback to string conversion
        return str(response)
    
    def _verify_tool_result(self, tool_name: str, args: Dict, result: Any):
        """Verify tool execution was successful"""
        # Add custom verification logic here
        # For example, check if file was created for write_file
        if tool_name == "write_file":
            path = args.get('path', '')
            if path and isinstance(result, dict):
                if result.get('success') or 'created' in str(result).lower():
                    print(f"   ✓ Verification: File created at {path}")
                else:
                    print(f"   ⚠️  Verification: Uncertain if file created")
    
    # --------------------------------------------------------
    # ANSWER GENERATION
    # --------------------------------------------------------
    
    def _generate_final_answer(
        self,
        question: str,
        plan: str,
        tool_name: Optional[str],
        tool_result: Any,
        context: Dict[str, Any],
        graph: ExecutionGraph
    ) -> str:
        """
        Generate final answer for user.
        
        Returns:
            Final answer text
        """
        print("\n[ANSWER] Generating final response...")
        print("   ⏳ Calling Grok LLM...")
        
        start = time.time()
        
        try:
            # Safely convert tool_result to string
            if tool_result is not None:
                try:
                    # If it's already a dict or simple type, use JSON
                    if isinstance(tool_result, (dict, list, str, int, float, bool)):
                        result_str = json.dumps(tool_result, indent=2)
                    else:
                        # Otherwise convert to string
                        result_str = str(tool_result)
                except Exception as e:
                    result_str = f"[Result conversion error: {e}]"
            else:
                result_str = "N/A"
            
            # Format prompt
            prompt = FINAL_ANSWER_PROMPT_TEMPLATE.format(
                question=question,
                plan=plan,
                tool=tool_name or "None",
                result=result_str,
                context=json.dumps(context, indent=2)
            )
            
            # Generate answer
            answer = self.llm.generate(prompt, temperature=0.5, max_tokens=1000)
            duration = time.time() - start
            
            print(f"   ✓ Answer generated ({duration:.2f}s)")
            print(f"   📝 Preview: {answer[:150]}...")
            
            graph.add_node("final_answer", {
                "answer": answer,
                "duration": duration
            })
            
            return answer
            
        except Exception as e:
            print(f"   ❌ Answer generation error: {e}")
            graph.add_node("final_answer", {"error": str(e)})
            # Fallback answer with actual result information
            if tool_result:
                return f"Task completed. Plan: {plan}. Tool result: {str(tool_result)[:200]}"
            else:
                return f"I attempted to {plan}, but encountered an error: {e}"
    
    # --------------------------------------------------------
    # MAIN ANSWER FLOW
    # --------------------------------------------------------
    
    async def answer(self, question: str) -> str:
        """
        Main entry point - answer user question.
        
        This orchestrates the full agent pipeline:
        1. Load memory
        2. Gather context
        3. Generate plan
        4. Select tool
        5. Execute tool
        6. Generate answer
        7. Store memory
        
        Returns:
            Final answer text
        """
        print("\n" + "=" * 60)
        print(f"📝 QUESTION: {question}")
        print("=" * 60)
        
        overall_start = time.time()
        graph = ExecutionGraph()
        self.performance_stats['total_questions'] += 1
        
        try:
            # ── STEP 1: Load Memory ──
            print("\n[STEP 1/7] Loading memory...")
            past_context = self.memory.retrieve()
            memory_context = format_memory_context(past_context)
            print(f"   ✓ Loaded {len(past_context)} past interactions")
            graph.add_node("memory_load", {"count": len(past_context)})
            
            # ── STEP 2: Gather Context ──
            print("\n[STEP 2/7] Gathering system context...")
            context = await self._gather_system_context(graph)
            print(f"   ✓ Context gathered: {len(context)} items")
            
            # ── STEP 3: Generate Plan ──
            print("\n[STEP 3/7] Planning...")
            plan, confidence = self._generate_plan(question, context, memory_context, graph)
            
            if confidence < CONFIDENCE_THRESHOLD:
                print(f"   ⚠️  Low confidence ({confidence:.0%}), proceeding with caution")
            
            # ── STEP 4: Select Tool ──
            print("\n[STEP 4/7] Selecting tool...")
            tool_decision = self._select_tool(plan, context, graph)
            
            # ── STEP 5: Execute Tool(s) ──
            print("\n[STEP 5/7] Executing...")
            tool_result = None
            tool_name = None
            all_results = []
            
            if tool_decision and tool_decision.get("tool"):
                tool_name = tool_decision["tool"]
                tool_args = tool_decision.get("arguments", {})
                
                success, tool_result = await self._execute_tool(
                    tool_name,
                    tool_args,
                    graph
                )
                
                all_results.append({
                    "step": 1,
                    "tool": tool_name,
                    "success": success,
                    "result": tool_result
                })
                
                # Check if we need follow-up actions
                if success:
                    # Check for multi-step patterns in the question
                    question_lower = question.lower()
                    needs_execute = any(word in question_lower for word in ['execute', 'run'])
                    needs_fix = any(word in question_lower for word in ['error', 'fix', 'correct', 'rectify'])
                    is_batch = any(phrase in question_lower for phrase in ['all .py', 'all files', 'all python', 'folder', 'directory'])
                    
                    print(f"   🔍 Multi-step check: execute={needs_execute}, fix={needs_fix}, batch={is_batch}")
                    
                    # BATCH PROCESSING: Handle multiple files in a folder
                    if tool_name == "list_directory" and is_batch and needs_execute:
                        print("\n[BATCH PROCESSING] Processing multiple files...")
                        
                        # Extract file list from result
                        file_list = []
                        if isinstance(tool_result, dict):
                            result_data = tool_result.get('result', {})
                            if isinstance(result_data, dict):
                                items = result_data.get('items', [])
                                # Filter only .py files
                                file_list = [
                                    item['name'] for item in items 
                                    if isinstance(item, dict) and item.get('type') == 'file' and item.get('name', '').endswith('.py')
                                ]
                        
                        print(f"   📁 Found {len(file_list)} Python files: {file_list}")
                        
                        # Get the folder path
                        folder_path = tool_args.get('path', '.')
                        
                        # Process each file
                        batch_results = []
                        for idx, filename in enumerate(file_list, 1):
                            print(f"\n   🔄 [{idx}/{len(file_list)}] Processing: {filename}")
                            file_path = f"{folder_path}/{filename}" if folder_path != '.' else filename
                            
                            try:
                                # Step 1: Read the file
                                print(f"      📖 Reading {filename}...")
                                read_success, read_result = await self._execute_tool(
                                    "read_file",
                                    {"path": file_path},
                                    graph
                                )
                                
                                if not read_success:
                                    print(f"      ⚠️  Failed to read {filename}, skipping")
                                    batch_results.append({"file": filename, "status": "read_failed"})
                                    continue
                                
                                # Extract content
                                content = ""
                                if isinstance(read_result, dict):
                                    result_data = read_result.get('result', {})
                                    if isinstance(result_data, dict):
                                        content = result_data.get('content', '')
                                
                                # Step 2: Execute the file
                                print(f"      ▶️  Executing {filename}...")
                                exec_success, exec_result = await self._execute_tool(
                                    "run_command",
                                    {"command": f"python {file_path}"},
                                    graph
                                )
                                
                                # Step 3: Check for errors
                                has_error = False
                                exec_str = str(exec_result).lower() if exec_result else ""
                                
                                # Error detection
                                has_keyword_error = any(err in exec_str for err in ['error', 'exception', 'traceback', 'syntaxerror', 'nameerror', 'typeerror'])
                                
                                has_return_code_error = False
                                if isinstance(exec_result, dict):
                                    result_data = exec_result.get('result', {})
                                    if isinstance(result_data, dict):
                                        return_code = result_data.get('return_code', 0)
                                        success_flag = result_data.get('success', True)
                                        has_return_code_error = (return_code != 0) or (not success_flag)
                                
                                # Source error detection
                                syntax_issues = ['prin(', 'sy.exit', 'pri(', 'improt ', 'except :', 'except  :']
                                has_source_error = any(issue in content for issue in syntax_issues)
                                
                                has_error = has_keyword_error or has_return_code_error or has_source_error
                                
                                print(f"      🔍 Error check: keyword={has_keyword_error}, return_code={has_return_code_error}, source={has_source_error}")
                                
                                # Step 4: Fix and rewrite if errors found
                                if has_error and needs_fix:
                                    print(f"      🔧 Analyzing and fixing errors in {filename}...")
                                    
                                    # Extract actual error messages
                                    error_output = ""
                                    if isinstance(exec_result, dict):
                                        result_data = exec_result.get('result', {})
                                        if isinstance(result_data, dict):
                                            error_output = result_data.get('output', '')
                                    
                                    # Use LLM to intelligently fix the code
                                    print(f"      🧠 Asking AI to fix errors...")
                                    
                                    fix_prompt = f"""You are a Python code debugger. Fix the errors in this code.

ORIGINAL CODE:
```python
{content}
```

EXECUTION ERROR:
```
{error_output}
```

CRITICAL INSTRUCTIONS:
1. Output ONLY the corrected Python code
2. NO explanations, NO markdown, NO comments about what you fixed
3. NO ```python``` code blocks - just the raw code
4. Fix ALL syntax errors, typos, and issues
5. Preserve the original logic and structure
6. Return the complete corrected file

OUTPUT (code only):
"""
                                    
                                    try:
                                        # Use lower temperature for more deterministic fixes
                                        corrected = self.llm.generate(fix_prompt, temperature=0.2, max_tokens=4000)
                                        
                                        # Clean up any markdown that might have slipped through
                                        corrected = corrected.strip()
                                        if corrected.startswith('```python'):
                                            corrected = corrected[9:]
                                        if corrected.startswith('```'):
                                            corrected = corrected[3:]
                                        if corrected.endswith('```'):
                                            corrected = corrected[:-3]
                                        corrected = corrected.strip()
                                        
                                        print(f"      📄 Original: {len(content)} chars")
                                        print(f"      ✅ AI Fixed: {len(corrected)} chars")
                                        
                                        # Verify the fix makes sense (basic sanity check)
                                        if len(corrected) < len(content) * 0.5:
                                            print(f"      ⚠️  AI output too short, falling back to basic fixes")
                                            raise ValueError("AI output suspiciously short")
                                        
                                        # Only write if content actually changed
                                        if corrected != content:
                                            # Write back to same file
                                            print(f"      💾 Writing AI-corrected {filename}...")
                                            write_success, write_result = await self._execute_tool(
                                                "write_file",
                                                {"path": file_path, "content": corrected},
                                                graph
                                            )
                                            
                                            if write_success:
                                                print(f"      ✅ {filename} corrected and saved")
                                                batch_results.append({"file": filename, "status": "fixed_by_ai", "errors_found": True})
                                            else:
                                                print(f"      ❌ Failed to write {filename}")
                                                batch_results.append({"file": filename, "status": "write_failed"})
                                        else:
                                            print(f"      ℹ️  No changes made by AI")
                                            batch_results.append({"file": filename, "status": "no_changes", "errors_found": True})
                                    
                                    except Exception as e:
                                        print(f"      ⚠️  AI fix failed: {e}")
                                        print(f"      🔧 Falling back to basic pattern fixes...")
                                        
                                        # Fallback to basic fixes if AI fails
                                        import re
                                        corrected = content
                                        corrected = corrected.replace('prin(', 'print(')
                                        corrected = corrected.replace('sy.exit', 'sys.exit')
                                        corrected = corrected.replace('pri(', 'print(')
                                        corrected = re.sub(r'int\(\(', 'int(', corrected)
                                        corrected = re.sub(r'async\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', r'async def \1(', corrected)
                                        
                                        if corrected != content:
                                            print(f"      💾 Writing pattern-corrected {filename}...")
                                            write_success, write_result = await self._execute_tool(
                                                "write_file",
                                                {"path": file_path, "content": corrected},
                                                graph
                                            )
                                            
                                            if write_success:
                                                print(f"      ✅ {filename} corrected with fallback fixes")
                                                batch_results.append({"file": filename, "status": "fixed_fallback", "errors_found": True})
                                            else:
                                                batch_results.append({"file": filename, "status": "write_failed"})
                                        else:
                                            batch_results.append({"file": filename, "status": "no_fix_applied", "errors_found": True})
                                else:
                                    print(f"      ✅ {filename} executed successfully (no errors)")
                                    batch_results.append({"file": filename, "status": "ok", "errors_found": False})
                            
                            except Exception as e:
                                print(f"      ❌ Error processing {filename}: {e}")
                                batch_results.append({"file": filename, "status": "error", "message": str(e)})
                        
                        # Summary
                        print(f"\n   📊 Batch Processing Summary:")
                        fixed_count = sum(1 for r in batch_results if r.get('status') == 'fixed')
                        ok_count = sum(1 for r in batch_results if r.get('status') == 'ok')
                        failed_count = len(batch_results) - fixed_count - ok_count
                        
                        print(f"      ✅ Fixed: {fixed_count}")
                        print(f"      ✓ OK: {ok_count}")
                        print(f"      ❌ Failed: {failed_count}")
                        
                        all_results.append({
                            "batch_processing": True,
                            "total_files": len(file_list),
                            "results": batch_results
                        })
                        
                        tool_result = {
                            "batch_summary": {
                                "total": len(file_list),
                                "fixed": fixed_count,
                                "ok": ok_count,
                                "failed": failed_count
                            },
                            "details": batch_results
                        }
                        tool_name = f"list_directory → batch_process({len(file_list)} files)"
                    
                    # SINGLE FILE PROCESSING
                    elif tool_name == "read_file" and needs_execute:
                        print("\n[FOLLOW-UP] Multi-step execution required...")
                        
                        # Step 2: Execute the file
                        print("   📍 Step 2: Executing the file...")
                        
                        # Extract filename from previous args
                        filename = tool_args.get('path', 'test.py')
                        
                        exec_success, exec_result = await self._execute_tool(
                            "run_command",
                            {"command": f"python {filename}"},
                            graph
                        )
                        
                        all_results.append({
                            "step": 2,
                            "tool": "run_command",
                            "success": exec_success,
                            "result": exec_result
                        })
                        
                        # Step 3: Check for errors and fix if needed
                        if needs_fix:
                            print("   🔍 Checking for errors to fix...")
                            
                            # Check if execution had errors
                            exec_str = str(exec_result).lower() if exec_result else ""
                            
                            # Multiple error detection methods
                            has_exec_error = False
                            
                            # Method 1: Check for error keywords
                            error_keywords = ['error', 'exception', 'traceback', 'syntaxerror', 'nameerror', 'typeerror', 'valueerror']
                            has_keyword_error = any(err in exec_str for err in error_keywords)
                            
                            # Method 2: Check return code (if available)
                            has_return_code_error = False
                            if isinstance(exec_result, dict):
                                result_data = exec_result.get('result', {})
                                if isinstance(result_data, dict):
                                    return_code = result_data.get('return_code', 0)
                                    success = result_data.get('success', True)
                                    # Non-zero return code OR success=False indicates error
                                    has_return_code_error = (return_code != 0) or (not success)
                            
                            # Method 3: Check for syntax errors in source
                            has_source_error = False
                            source_content = ""
                            if isinstance(tool_result, dict):
                                result_data = tool_result.get('result', {})
                                if isinstance(result_data, dict):
                                    source_content = result_data.get('content', '')
                            
                            # Common syntax errors to detect
                            syntax_issues = [
                                'prin(',      # print typo
                                'sy.exit',    # sys typo
                                'pri(',       # print typo
                                'improt',     # import typo
                                'def ',       # check for indentation issues (basic)
                            ]
                            has_source_error = any(issue in source_content for issue in syntax_issues)
                            
                            # Combine all checks
                            has_exec_error = has_keyword_error or has_return_code_error or has_source_error
                            
                            print(f"   🔍 Error check details:")
                            print(f"      - Keyword error: {has_keyword_error}")
                            print(f"      - Return code error: {has_return_code_error}")
                            print(f"      - Source error: {has_source_error}")
                            print(f"      - Overall: {has_exec_error}")
                            
                            if has_exec_error:
                                print("   📍 Step 3: Error detected, creating corrected file...")
                                
                                # Get the original content
                                original_content = source_content
                                
                                print(f"   📄 Original content: {original_content[:100]}...")
                                
                                # Fix common issues
                                corrected_content = original_content
                                corrected_content = corrected_content.replace('prin(', 'print(')
                                corrected_content = corrected_content.replace('sy.exit', 'sys.exit')
                                corrected_content = corrected_content.replace('pri(', 'print(')
                                corrected_content = corrected_content.replace('improt ', 'import ')
                                corrected_content = corrected_content.replace('except :', 'except:')
                                corrected_content = corrected_content.replace('except  :', 'except:')
                                
                                print(f"   ✅ Corrected content: {corrected_content[:100]}...")
                                
                                # Determine output filename
                                output_file = "aa.py"  # Default
                                # Look for output filename in question
                                import re
                                match = re.search(r'in\s+(\w+\.py)', question)
                                if match:
                                    output_file = match.group(1)
                                
                                print(f"   💾 Writing to: {output_file}")
                                
                                write_success, write_result = await self._execute_tool(
                                    "write_file",
                                    {"path": output_file, "content": corrected_content},
                                    graph
                                )
                                
                                all_results.append({
                                    "step": 3,
                                    "tool": "write_file",
                                    "success": write_success,
                                    "result": write_result
                                })
                                
                                # Update for final summary
                                tool_result = {
                                    "all_steps": all_results,
                                    "final_action": f"Created corrected file: {output_file}"
                                }
                                tool_name = "read_file → run_command → write_file"
                            else:
                                print("   ℹ️  No errors detected, skipping fix step")
                
                if success or all_results:
                    self.performance_stats['successful_executions'] += 1
                else:
                    self.performance_stats['failed_executions'] += 1
            else:
                print("   ℹ️  No tool execution needed")
            
            # Add graph edges
            graph.add_edge("memory_load", "planning")
            graph.add_edge("planning", "tool_selection")
            if tool_decision:
                graph.add_edge("tool_selection", "tool_execution")
                graph.add_edge("tool_execution", "final_answer")
            else:
                graph.add_edge("tool_selection", "final_answer")
            
            # ── STEP 6: Generate Final Answer ──
            print("\n[STEP 6/7] Generating final answer...")
            final_answer = self._generate_final_answer(
                question,
                plan,
                tool_name,
                tool_result,
                context,
                graph
            )
            
            # ── STEP 7: Store Memory ──
            print("\n[STEP 7/7] Storing to memory...")
            self.memory.store(
                {
                    "question": question,
                    "plan": plan,
                    "confidence": confidence,
                    "tool_used": tool_name,
                    "tool_result": str(tool_result)[:500] if tool_result else None,
                    "answer": final_answer,
                    "execution_graph": graph.snapshot(),
                    "duration": time.time() - overall_start
                },
                source="terminal_agent"
            )
            print(f"   ✓ Memory updated")
            
            # ── Performance Summary ──
            total_duration = time.time() - overall_start
            self.performance_stats['total_duration'] += total_duration
            
            print("\n" + "=" * 60)
            print("✓ EXECUTION COMPLETE")
            print("=" * 60)
            print(f"⏱️  Total duration: {total_duration:.2f}s")
            print(f"🎯 Confidence: {confidence:.0%}")
            print(f"🔧 Tool used: {tool_name or 'None'}")
            
            # LLM usage stats
            usage_stats = self.llm.get_usage_stats()
            print(f"📊 Tokens used: {usage_stats['total_tokens']}")
            print(f"💰 Est. cost: {usage_stats['estimated_cost']}")
            if 'cache' in usage_stats:
                cache_stats = usage_stats['cache']
                print(f"💾 Cache: {cache_stats['hit_rate']} hit rate")
            print("=" * 60 + "\n")
            
            return final_answer
            
        except Exception as e:
            print(f"\n❌ FATAL ERROR: {e}")
            print("=" * 60 + "\n")
            self.performance_stats['failed_executions'] += 1
            
            # Store error in memory
            self.memory.store(
                {
                    "question": question,
                    "error": str(e),
                    "execution_graph": graph.snapshot()
                },
                source="terminal_agent_error"
            )
            
            raise
    
    def _needs_follow_up(self, question: str, last_tool: str, result: Any) -> bool:
        """
        Determine if the question requires follow-up actions.
        
        Examples:
        - "read and execute" → read_file needs follow-up run_command
        - "execute and fix" → run_command with error needs follow-up write_file
        """
        question_lower = question.lower()
        
        # Multi-step patterns
        multi_step_keywords = [
            ('read', 'execute', 'run'),
            ('execute', 'error', 'fix', 'correct', 'write'),
            ('read', 'fix', 'write'),
            ('and then', 'then', 'after that')
        ]
        
        # Check if question mentions multiple actions
        has_multiple_actions = any(
            all(keyword in question_lower for keyword in pattern)
            for pattern in multi_step_keywords
        )
        
        if not has_multiple_actions:
            return False
        
        # Specific follow-up rules
        if last_tool == "read_file":
            # If read was successful and question mentions execute/run
            return any(word in question_lower for word in ['execute', 'run', 'test'])
        
        if last_tool == "run_command":
            # If execution might have errors and question mentions fix/correct
            if any(word in question_lower for word in ['error', 'fix', 'correct', 'rectify']):
                # Check if there was an error in the result
                result_str = str(result).lower()
                if any(err in result_str for err in ['error', 'exception', 'traceback', 'failed']):
                    return True
        
        return False
    
    # --------------------------------------------------------
    # UTILITY METHODS
    # --------------------------------------------------------
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = self.performance_stats.copy()
        
        if stats['total_questions'] > 0:
            stats['success_rate'] = (
                stats['successful_executions'] / stats['total_questions'] * 100
            )
            stats['avg_duration'] = (
                stats['total_duration'] / stats['total_questions']
            )
        
        stats['llm_usage'] = self.llm.get_usage_stats()
        
        return stats
    
    def print_stats(self):
        """Print performance statistics"""
        stats = self.get_performance_stats()
        
        print("\n" + "=" * 60)
        print("PERFORMANCE STATISTICS")
        print("=" * 60)
        print(f"Total questions: {stats['total_questions']}")
        print(f"Successful: {stats['successful_executions']}")
        print(f"Failed: {stats['failed_executions']}")
        print(f"Success rate: {stats.get('success_rate', 0):.1f}%")
        print(f"Total tool calls: {stats['total_tool_calls']}")
        print(f"Avg duration: {stats.get('avg_duration', 0):.2f}s")
        print(f"\nLLM Usage:")
        print(f"  Total tokens: {stats['llm_usage']['total_tokens']}")
        print(f"  Est. cost: {stats['llm_usage']['estimated_cost']}")
        if 'cache' in stats['llm_usage']:
            cache = stats['llm_usage']['cache']
            print(f"  Cache hit rate: {cache['hit_rate']}")
        print("=" * 60 + "\n")
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.performance_stats = {
            'total_questions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_tool_calls': 0,
            'total_duration': 0.0,
            'cache_hits': 0
        }
        self.llm.reset_stats()
        print("✓ Statistics reset")

# ============================================================
# EXPORTS
# ============================================================

__all__ = ['TerminalAgent']