# agent.py
"""
Advanced Agent with Multi-step Planning and Self-Correction
"""
from typing import List, Dict,Any
from ollama_actual import OllamaLLM
from memory import LongTermMemory
from policy import PolicyEngine, PolicyDecision
from execution_graph import ExecutionGraph

# NEW IMPORTS
from planner import HierarchicalPlanner, RollbackManager
from agentic_loop import SelfCorrectingAgent
from tool_chain import ToolDependencyGraph, ParallelExecutor
from context_manager import SessionStateManager, RelevanceScorer, ContextCompressor

import json
import re


def parse_resource(response):
    """Converts MCP resource response to dict safely"""
    if hasattr(response, "text"):
        try:
            return json.loads(response.text)
        except:
            return {"raw": response.text}
    
    if isinstance(response, list) and len(response) > 0:
        return parse_resource(response[0])
    
    if isinstance(response, dict):
        return response
    
    return {"raw": str(response)}


class TerminalAgent:
    """
    Advanced agent with:
    - Multi-step planning
    - Self-correction
    - Tool chaining
    - Context management
    """
    
    def __init__(self, mcp_client, debug_mode: bool = False):
        self.client = mcp_client
        self.llm = OllamaLLM(model="qwen2.5-coder:7b")
        self.memory = LongTermMemory()
        self.policy = PolicyEngine(dry_run=False)
        
        # NEW COMPONENTS - PASS CLIENT TO PLANNER
        self.planner = HierarchicalPlanner(self.llm, mcp_client=mcp_client)  # ADD mcp_client
        self.self_correcting_agent = SelfCorrectingAgent(
            self.llm,
            max_retries=3,
            debug_mode=debug_mode
        )
        self.tool_chain = ToolDependencyGraph()
        self.parallel_executor = ParallelExecutor()
        self.session_manager = SessionStateManager(session_id="main")
        self.relevance_scorer = RelevanceScorer(self.llm)
        self.context_compressor = ContextCompressor(max_tokens=4000)
        
        self.debug_mode = debug_mode
        
        if debug_mode:
            print("🤖 Advanced Agent initialized:")
            print("   - Multi-step planner: ✓")
            print("   - Self-correction: ✓")
            print("   - Tool chaining: ✓")
            print("   - Context management: ✓")

    def _gate_resource(self, uri: str):
        decision = self.policy.evaluate("resource", {"uri": uri})
        if self.debug_mode:
            print(f"   🔒 Policy: {uri} → {decision}")
        
        if decision == PolicyDecision.DENY:
            raise PermissionError(f"Policy denied: {uri}")
        
        return decision != PolicyDecision.DRY_RUN
    
    def _gate_tool(self, name: str, arguments: dict):
        decision = self.policy.evaluate("tool", {"name": name, "arguments": arguments})
        if self.debug_mode:
            print(f"   🔒 Policy: {name} → {decision}")
        
        if decision == PolicyDecision.DENY:
            raise PermissionError(f"Policy denied: {name}")
        
        return decision != PolicyDecision.DRY_RUN
    
    def _extract_tool_result(self, raw_result: Any) -> Dict[str, Any]:
        """Extract actual result from MCP CallToolResult object"""
        import json
        
        # Use .data attribute if it exists
        if hasattr(raw_result, 'data') and isinstance(raw_result.data, dict):
            return raw_result.data
        
        # Fallback: Extract from .content
        if hasattr(raw_result, 'content'):
            content = raw_result.content
            
            if isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                
                if hasattr(first_item, 'text'):
                    try:
                        return json.loads(first_item.text)
                    except:
                        return {"success": True, "output": first_item.text}
        
        if isinstance(raw_result, dict):
            return raw_result
        
        return {"success": False, "error": f"Cannot extract result from {type(raw_result)}"}
    

    def _enhance_arguments_with_results(
        self,
        task: 'SubTask',
        previous_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Enhance task arguments with results from previous tasks
        
        Example: If task_2 found files, and task_3 writes a report,
        inject the file list into task_3's content
        """
        args = task.arguments.copy()
        
        # For write_file tasks with empty content, try to fill from previous results
        if task.tool_name == "write_file" and not args.get("content"):
            # Find the most recent successful result
            for result in reversed(previous_results):
                if result["success"] and result.get("result"):
                    result_data = result["result"]
                    
                    # Extract useful info
                    if isinstance(result_data, dict):
                        # If it's a tool result, get the actual output
                        if "result" in result_data:
                            result_data = result_data["result"]
                        
                        # Build report content
                        content_parts = [f"Task: {task.description}\n"]
                        content_parts.append(f"Generated: {task.id}\n")
                        content_parts.append("\n=== Results ===\n")
                        content_parts.append(str(result_data))
                        
                        args["content"] = "\n".join(content_parts)
                        break
        
        return args
    

    async def answer(self, question: str) -> str:
        """Main entry point with advanced capabilities"""
        
        if self.debug_mode:
            print("\n" + "=" * 60)
            print(f"📝 Question: {question}")
            print("=" * 60)
        
        graph = ExecutionGraph()
        server = "terminal"
        
        # Add question to context
        self.session_manager.add_context(question, "user_query")
        
        # ============================================================
        # STEP 1: Gather Context
        # ============================================================
        if self.debug_mode:
            print("\n[1/7] Gathering context...")
        
        tool_names = [t.name for t in self.client._tools]
        context_info = {}
        
        # Get CWD
        try:
            if self._gate_resource("session://cwd"):
                cwd_response = await self.client.read_resource(
                    server=server,
                    uri="session://cwd"
                )
                cwd_data = parse_resource(cwd_response)
                context_info["cwd"] = cwd_data.get("cwd", "unknown")
        except Exception as e:
            context_info["cwd"] = "unknown"
        
        # Get system info
        try:
            if self._gate_resource("system://info"):
                sys_response = await self.client.read_resource(
                    server=server,
                    uri="system://info"
                )
                context_info["system"] = parse_resource(sys_response)
        except:
            context_info["system"] = {}
        
        context_info["tools"] = tool_names
        
        # ============================================================
        # STEP 2: Multi-step Planning
        # ============================================================
        if self.debug_mode:
            print("\n[2/7] Creating task plan...")
        
        task_plan = self.planner.decompose_task(question, context_info)
        
        if self.debug_mode:
            print(f"   ✓ Generated {len(task_plan.subtasks)} subtasks")
            for task in task_plan.subtasks:
                print(f"      - {task.id}: {task.description}")
        
        graph.add_node("plan", task_plan.to_dict())
        
# Validation is already done in planner.decompose_task()
# Just check if there are validation errors
        if task_plan.validation_errors:
            print(f"⚠️  Plan validation failed:")
            for error in task_plan.validation_errors:
                print(f"   - {error}")        
        # ============================================================
        # STEP 3: Detect Tool Chains
        # ============================================================
        if self.debug_mode:
            print("\n[3/7] Detecting tool chains...")
        
        tool_nodes = self.tool_chain.detect_chain(question, self.llm)
        
        if tool_nodes:
            batches = self.tool_chain.optimize_execution_order(tool_nodes)
            if self.debug_mode:
                print(f"   ✓ Optimized into {len(batches)} execution batches")
        
        # ============================================================
        # STEP 4: Execute Plan with Self-Correction
        # ============================================================
        if self.debug_mode:
            print("\n[4/7] Executing plan...")
        
        rollback_manager = RollbackManager()
        execution_results = []
        
        for task in task_plan.subtasks:
            if self.debug_mode:
                print(f"\n   Executing: {task.id} - {task.description}")
            
            # Check dependencies completed
            deps_complete = all(
                any(r["task_id"] == dep_id and r["success"] for r in execution_results)
                for dep_id in task.dependencies
            )
            
            if not deps_complete:
                print(f"   ⏭️  Skipping {task.id} - dependencies not met")
                continue
            
            # SMART ARGUMENT INJECTION: Use results from previous tasks
            enhanced_args = self._enhance_arguments_with_results(
                task,
                execution_results
            )
            # Gate the tool
            if not self._gate_tool(task.tool_name, task.arguments):
                print(f"   ⏭️  Skipping {task.id} - policy denied")
                continue
            
            # Execute with self-correction
            # Execute with self-correction
            result = await self.self_correcting_agent.act_with_retry(
                self.client,
                server,
                task.tool_name,
                enhanced_args,  # Use enhanced arguments
                question
            )
            
            execution_results.append({
                "task_id": task.id,
                "tool": task.tool_name,
                "success": result.get("success", False),
                "result": result
            })
            
            # Record rollback action
            rollback_manager.push_rollback(task)
            
            # Add to context
            self.session_manager.add_context(result, "tool_result")
        
        graph.add_node("execution", {"results": execution_results})
        
        # ============================================================
        # STEP 5: Context Management
        # ============================================================
        if self.debug_mode:
            print("\n[5/7] Managing context...")
        
        # Score relevance
        scored_context = self.relevance_scorer.score_batch(
            self.session_manager.context_items,
            question
        )
        
        # Compress if needed
        compressed_context = self.context_compressor.compress(scored_context)
        
        # Prune low-relevance items
        self.session_manager.prune_by_relevance(question, self.llm, keep_top_n=20)
        
        # ============================================================
        # STEP 6: Generate Final Answer
        # ============================================================
        if self.debug_mode:
            print("\n[6/7] Generating answer...")
        
        final_prompt = f"""
        You are a helpful AI assistant. Answer the user's question based on the tool execution results.

        User's question: {question}

        Number of tasks completed: {len(task_plan.subtasks)}

        Results from tools:
        {json.dumps(execution_results, indent=2)}

        Additional context:
        {compressed_context}

        IMPORTANT: Respond in natural, conversational language. Do NOT return JSON. Do NOT return tool calls. 
        Explain what was done and what the results mean in a clear, helpful way that directly answers the user's question.

        Your response (natural language only):
        """
        final_answer = self.llm.generate(final_prompt)
        
        # ============================================================
        # STEP 7: Save to Memory
        # ============================================================
        if self.debug_mode:
            print("\n[7/7] Saving to memory...")
        
        self.memory.store(
            {
                "question": question,
                "plan": task_plan.to_dict(),
                "execution_results": execution_results,
                "answer": final_answer,
                "execution_graph": graph.snapshot(),
                "self_correction_summary": self.self_correcting_agent.get_execution_summary()
            },
            source="advanced_terminal_agent"
        )
        
        # Save checkpoint
        if len(self.session_manager.context_items) % 10 == 0:
            self.session_manager.save_checkpoint(f"auto_{len(self.session_manager.context_items)}")
        
        if self.debug_mode:
            print("\n" + "=" * 60)
            print("✓ COMPLETE")
            print("=" * 60)
        
        return final_answer
    

