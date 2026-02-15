# tool_chain.py
"""
Automatic Tool Chaining and Parallel Execution
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Set
import asyncio


@dataclass
class ToolNode:
    """Node in the tool dependency graph"""
    name: str
    arguments: Dict[str, Any]
    dependencies: Set[str]  # Names of tools that must run first
    can_run_parallel: bool = False


class ToolDependencyGraph:
    """
    Represents dependencies between tools
    
    Example:
        list_directory → read_file → analyze_code → write_report
                      ↘ search_files ↗
    """
    
    def __init__(self):
        # Predefined common patterns
        self.common_patterns = {
            "debug_file": [
                ("read_file", {}),
                ("run_command", {"command": "python {file}"}),
                ("analyze_error", {}),
                ("write_file", {"path": "{file}"})
            ],
            
            "code_review": [
                ("list_directory", {"path": "."}),
                ("read_file", {}),
                ("run_command", {"command": "pylint {file}"}),
                ("run_command", {"command": "flake8 {file}"})
            ],
            
            "git_workflow": [
                ("git_status", {}),
                ("git_diff", {}),
                ("git_commit", {"message": "{msg}"})
            ]
        }
        
        # Tool execution rules
        self.execution_rules = {
            # Read operations can run in parallel
            "parallel_safe": {"read_file", "list_directory", "search_files", "git_status", "system_info"},
            
            # Write operations must be sequential
            "sequential_only": {"write_file", "replace_in_file", "git_commit", "run_command"},
            
            # Dependencies (tool A requires tool B output)
            "requires": {
                "write_file": ["read_file"],  # Often read before write
                "replace_in_file": ["read_file"],
                "git_commit": ["git_status"],
            }
        }
        
    def detect_chain(self, goal: str, llm) -> List[ToolNode]:
        """
        Auto-detect tool chain needed for a goal
        
        Returns ordered list of ToolNodes
        """
        
        prompt = f"""
    You are analyzing what tools are needed for this goal.

    GOAL: {goal}

    AVAILABLE TOOLS (with correct argument names):
    - read_file(path: str): Read file contents
    - write_file(path: str, content: str): Write to file
    - list_directory(path: str = "."): List files in directory
    - search_files(keyword: str, path: str = "."): Search for files by name
    - run_command(command: str, cwd: str = "."): Execute shell command
    - git_status(): Check git status
    - git_diff(): Show git diff
    - replace_in_file(path: str, search: str, replace: str): Find and replace in file

    OUTPUT FORMAT (JSON only):
    {{
    "tool_chain": [
        {{
        "tool": "list_directory",
        "arguments": {{"path": "."}},
        "dependencies": []
        }},
        {{
        "tool": "read_file",
        "arguments": {{"path": "config.py"}},
        "dependencies": ["list_directory"]
        }}
    ]
    }}


        IMPORTANT: List tools in dependency order.
        """
        
        try:
            response = llm.generate(prompt)
            
            import re
            import json
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            tool_nodes = []
            for item in data.get("tool_chain", []):
                node = ToolNode(
                    name=item["tool"],
                    arguments=item["arguments"],
                    dependencies=set(item.get("dependencies", [])),
                    can_run_parallel=item["tool"] in self.execution_rules["parallel_safe"]
                )
                tool_nodes.append(node)
            
            return tool_nodes
            
        except Exception as e:
            print(f"❌ Chain detection failed: {e}")
            return []
    
    def optimize_execution_order(self, tool_nodes: List[ToolNode]) -> List[List[ToolNode]]:
        """
        Group tools into parallel execution batches
        
        Returns: List of batches, where each batch can run in parallel
        
        Example:
            [
                [list_directory, system_info],  # Batch 1 (parallel)
                [read_file],                     # Batch 2
                [write_file]                     # Batch 3
            ]
        """
        
        batches = []
        remaining = tool_nodes.copy()
        completed = set()
        
        while remaining:
            # Find tools with satisfied dependencies
            ready = [
                node for node in remaining
                if node.dependencies.issubset(completed)
            ]
            
            if not ready:
                print("⚠️  Circular dependency detected!")
                break
            
            # Separate parallel-safe from sequential
            parallel_batch = [node for node in ready if node.can_run_parallel]
            sequential_batch = [node for node in ready if not node.can_run_parallel]
            
            # Add parallel batch
            if parallel_batch:
                batches.append(parallel_batch)
                for node in parallel_batch:
                    completed.add(node.name)
                    remaining.remove(node)
            
            # Add sequential (one at a time)
            for node in sequential_batch:
                batches.append([node])
                completed.add(node.name)
                remaining.remove(node)
        
        return batches


class ParallelExecutor:
    """Execute multiple tools in parallel safely"""
    
    async def execute_batch(
        self,
        mcp_client,
        server: str,
        batch: List[ToolNode]
    ) -> Dict[str, Any]:
        """
        Execute a batch of tools in parallel
        
        Returns dict mapping tool_name → result
        """
        
        print(f"\n⚡ Executing {len(batch)} tools in parallel...")
        
        async def execute_one(node: ToolNode):
            try:
                result = await mcp_client.call_tool(
                    server=server,
                    name=node.name,
                    arguments=node.arguments
                )
                return (node.name, result)
            except Exception as e:
                return (node.name, {"success": False, "error": str(e)})
        
        # Run all in parallel
        results = await asyncio.gather(*[execute_one(node) for node in batch])
        
        return dict(results)