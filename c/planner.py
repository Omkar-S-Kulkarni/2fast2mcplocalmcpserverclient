# planner.py
"""
Hierarchical Task Planner with Validation and Rollback
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import re



def fix_common_json_errors(json_str: str) -> str:
    """Fix common JSON formatting errors from LLM output"""
    import re
    
    # Remove markdown code blocks
    json_str = re.sub(r'^```json\s*', '', json_str)
    json_str = re.sub(r'^```\s*', '', json_str)
    json_str = re.sub(r'\s*```$', '', json_str)
    
    # Fix trailing commas before } or ]
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    
    # Fix double closing braces (common error)
    json_str = re.sub(r'}\s*},\s*"', r'}, "', json_str)
    
    # Fix missing commas between objects
    json_str = re.sub(r'}\s*{', r'}, {', json_str)
    
    # Fix single quotes (JSON requires double quotes)
    # But be careful not to replace quotes inside strings
    # This is a simple version - may need improvement
    json_str = json_str.replace("'", '"')
    
    return json_str.strip()



class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class SubTask:
    """Individual atomic task"""
    id: str
    description: str
    tool_name: str
    arguments: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    rollback_action: Optional[Dict[str, Any]] = None


@dataclass
class TaskPlan:
    """Complete execution plan with hierarchy"""
    goal: str
    subtasks: List[SubTask] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    
    def add_subtask(self, subtask: SubTask) -> None:
        """Add a subtask to the plan"""
        self.subtasks.append(subtask)
    
    def get_task(self, task_id: str) -> Optional[SubTask]:
        """Get task by ID"""
        for task in self.subtasks:
            if task.id == task_id:
                return task
        return None
    
    def validate_with_tools(self, valid_tools: set) -> bool:
        """Validate the plan with a specific set of valid tools"""
        self.validation_errors = []
        
        # Check 1: All tasks have valid tools
        for task in self.subtasks:
            if task.tool_name not in valid_tools:
                self.validation_errors.append(
                    f"Task {task.id}: Invalid tool '{task.tool_name}'"
                )
        
        # Check 2: Dependency graph is acyclic
        if self._has_circular_dependencies():
            self.validation_errors.append("Circular dependency detected in task plan")
        
        # Check 3: All dependencies exist
        task_ids = {t.id for t in self.subtasks}
        for task in self.subtasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    self.validation_errors.append(
                        f"Task {task.id}: Unknown dependency '{dep_id}'"
                    )
        
        # Check 4: Execution order is valid
        if not self._validate_execution_order():
            self.validation_errors.append("Invalid execution order - dependencies not satisfied")
        
        return len(self.validation_errors) == 0
    
    def _has_circular_dependencies(self) -> bool:
        """Detect circular dependencies using DFS"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            task = self.get_task(task_id)
            if task:
                for dep_id in task.dependencies:
                    if dep_id not in visited:
                        if has_cycle(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True
            
            rec_stack.remove(task_id)
            return False
        
        for task in self.subtasks:
            if task.id not in visited:
                if has_cycle(task.id):
                    return True
        
        return False
    
    def _validate_execution_order(self) -> bool:
        """Ensure execution order respects dependencies"""
        completed = set()
        
        for task_id in self.execution_order:
            task = self.get_task(task_id)
            if not task:
                return False
            
            for dep_id in task.dependencies:
                if dep_id not in completed:
                    return False
            
            completed.add(task_id)
        
        return True
    
    def compute_execution_order(self) -> List[str]:
        """Compute topological sort for execution order"""
        in_degree = {task.id: len(task.dependencies) for task in self.subtasks}
        queue = [task.id for task in self.subtasks if in_degree[task.id] == 0]
        order = []
        
        while queue:
            task_id = queue.pop(0)
            order.append(task_id)
            
            for task in self.subtasks:
                if task_id in task.dependencies:
                    in_degree[task.id] -= 1
                    if in_degree[task.id] == 0:
                        queue.append(task.id)
        
        self.execution_order = order
        return order
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize plan"""
        return {
            "goal": self.goal,
            "subtasks": [
                {
                    "id": t.id,
                    "description": t.description,
                    "tool_name": t.tool_name,
                    "arguments": t.arguments,
                    "dependencies": t.dependencies,
                    "status": t.status.value,
                    "result": str(t.result) if t.result else None,
                    "error": t.error,
                    "rollback_action": t.rollback_action
                }
                for t in self.subtasks
            ],
            "execution_order": self.execution_order,
            "validation_errors": self.validation_errors
        }


def get_valid_tools_from_client(mcp_client=None) -> set:
    """Get list of valid tools dynamically"""
    
    if mcp_client and hasattr(mcp_client, '_tools'):
        return {tool.name for tool in mcp_client._tools}
    
    return {
        "run_command", "interactive_command", "read_file", "write_file", 
        "list_directory", "search_files", "replace_in_file", 
        "list_processes", "kill_process", "get_env", "system_info",
        "git_status", "git_diff", "git_commit", "tail_file", 
        "check_port", "docker_ps"
    }


class HierarchicalPlanner:
    """Decomposes complex tasks into executable subtasks"""
    
    def __init__(self, llm, mcp_client=None):
        self.llm = llm
        self.mcp_client = mcp_client
    
    def _build_tool_schemas(self) -> str:
        """Build human-readable tool schemas for the LLM"""
        
        schemas = {
            "run_command": {
                "args": {"command": "str", "cwd": "str (optional)"},
                "description": "Execute a shell command"
            },
            "read_file": {
                "args": {"path": "str"},
                "description": "Read file contents"
            },
            "write_file": {
                "args": {"path": "str", "content": "str"},
                "description": "Write content to file"
            },
            "list_directory": {
                "args": {"path": "str (optional, default: '.')"},
                "description": "List files in directory"
            },
            "search_files": {
                "args": {"keyword": "str", "path": "str (optional, default: '.')"},
                "description": "Search for files by name keyword"
            },
            "replace_in_file": {
                "args": {"path": "str", "search": "str", "replace": "str"},
                "description": "Find and replace in file"
            },
            "create_report_from_results": {
                "args": {"title": "str", "results_summary": "str", "output_path": "str (optional)"},
                "description": "Create a formatted report from results"
            },
            "git_status": {
                "args": {},
                "description": "Get git status"
            },
            "git_diff": {
                "args": {},
                "description": "Get git diff"
            },
            "git_commit": {
                "args": {"message": "str"},
                "description": "Commit changes"
            },
            "system_info": {
                "args": {},
                "description": "Get system information"
            }
        }
        
        lines = []
        for tool_name, schema in schemas.items():
            args_str = ", ".join([f"{k}: {v}" for k, v in schema["args"].items()])
            lines.append(f"- {tool_name}({args_str}) - {schema['description']}")
        
        return "\n".join(lines)    
    def decompose_task(self, goal: str, context: Dict[str, Any]) -> TaskPlan:
        """Break down a complex goal into subtasks using LLM"""
        
        valid_tools = get_valid_tools_from_client(self.mcp_client)
        tool_schemas = self._build_tool_schemas()
        
        prompt = f"""
        You are a task planner. Break down this goal into ATOMIC subtasks.

        GOAL: {goal}

        CONTEXT:
        - Current directory: {context.get('cwd', 'unknown')}

        AVAILABLE TOOLS WITH CORRECT ARGUMENT NAMES:
        {tool_schemas}

        CRITICAL RULES:
        1. Use EXACT argument names shown above (e.g., "keyword" for search_files, NOT "pattern")
        2. Output ONLY valid JSON - no markdown, no backticks, no extra text
        3. For file operations, always use relative paths (e.g., "report.txt" not "D:/...")
        4. For grep/search commands, use proper syntax: grep -r 'pattern' --include='*.ext' .
        5. Chain tools logically: search → read → process → write

        EXAMPLE TASK BREAKDOWN:
        Goal: "Find Python files importing os and create report"
        {{
        "subtasks": [
            {{
            "id": "task_1",
            "description": "Search for all Python files",
            "tool": "search_files",
            "arguments": {{"keyword": ".py", "path": "."}},
            "dependencies": [],
            "rollback": null
            }},
            {{
            "id": "task_2",
            "description": "Search within Python files for 'import os'",
            "tool": "run_command",
            "arguments": {{"command": "grep -r 'import os' --include='*.py' ."}},
            "dependencies": ["task_1"],
            "rollback": null
            }},
            {{
            "id": "task_3",
            "description": "Create report with results",
            "tool": "write_file",
            "arguments": {{"path": "os_imports_report.txt", "content": "Files importing os:\\n"}},
            "dependencies": ["task_2"],
            "rollback": null
            }}
        ]
        }}

        NOW CREATE A PLAN FOR THIS GOAL:
        {goal}

        OUTPUT (pure JSON only):
        

            IMPORTANT: Respond with ONLY the JSON object above. No explanation, no markdown.
            """                
        try:
            response = self.llm.generate(prompt)
            
            # IMPROVED: Strip markdown code blocks first
            
            
            # Remove ```json and ``` markers
            cleaned = response.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned)
            cleaned = re.sub(r'^```\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            
            # Try to find JSON object
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                
                # IMPROVED: Fix common JSON errors
                # Fix trailing commas before closing braces/brackets
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                # Fix double closing braces
                json_str = re.sub(r'}\s*}', r'}', json_str)
                
                data = json.loads(json_str)
            else:
                # Try parsing the cleaned response directly
                data = json.loads(cleaned)
            
            plan = TaskPlan(goal=goal)
            
            for task_data in data.get("subtasks", []):
                subtask = SubTask(
                    id=task_data["id"],
                    description=task_data["description"],
                    tool_name=task_data["tool"],
                    arguments=task_data["arguments"],
                    dependencies=task_data.get("dependencies", []),
                    rollback_action=task_data.get("rollback")
                )
                plan.add_subtask(subtask)
            
            plan.compute_execution_order()
            plan.validate_with_tools(valid_tools)
            
            return plan
            
        except Exception as e:
            print(f"❌ Failed to parse plan: {e}")
            print(f"LLM Response: {response[:500]}...")  # Only show first 500 chars
            
            # Fallback plan
            plan = TaskPlan(goal=goal)
            plan.add_subtask(SubTask(
                id="fallback_1",
                description=goal,
                tool_name="run_command",
                arguments={"command": f"echo 'Task: {goal}'"},
                dependencies=[]
            ))
            plan.compute_execution_order()
            return plan
            
        except Exception as e:
            print(f"❌ Failed to parse plan: {e}")
            print(f"LLM Response: {response}")
            
            # CRITICAL FIX: Return a fallback plan instead of None
            plan = TaskPlan(goal=goal)
            plan.add_subtask(SubTask(
                id="fallback_1",
                description=goal,
                tool_name="run_command",
                arguments={"command": "echo 'Manual intervention needed'"},
                dependencies=[]
            ))
            plan.compute_execution_order()
            return plan


class RollbackManager:
    """Manages rollback of failed task sequences"""
    
    def __init__(self):
        self.rollback_stack = []
    
    def push_rollback(self, task: SubTask) -> None:
        """Record a rollback action"""
        if task.rollback_action:
            self.rollback_stack.append({
                "task_id": task.id,
                "action": task.rollback_action
            })
    
    async def rollback(self, mcp_client, server: str) -> None:
        """Execute all rollback actions in reverse order"""
        print("🔄 Starting rollback...")
        
        while self.rollback_stack:
            rollback_item = self.rollback_stack.pop()
            print(f"   Rolling back task: {rollback_item['task_id']}")
            
            action = rollback_item['action']
            tool_name = action.get('tool')
            arguments = action.get('arguments', {})
            
            try:
                await mcp_client.call_tool(
                    server=server,
                    name=tool_name,
                    arguments=arguments
                )
                print(f"   ✓ Rolled back {rollback_item['task_id']}")
            except Exception as e:
                print(f"   ✗ Rollback failed for {rollback_item['task_id']}: {e}")
        
        print("✓ Rollback complete")