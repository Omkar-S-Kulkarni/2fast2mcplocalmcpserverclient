# agentic_loop.py
"""
Observation → Reflection → Action Loop with Self-Correction
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum
import time


class ReflectionType(Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    NEED_MORE_INFO = "need_more_info"


@dataclass
class Observation:
    """Result of an action execution"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class Reflection:
    """Agent's analysis of an observation"""
    observation_id: str
    reflection_type: ReflectionType
    insights: List[str]
    suggested_actions: List[Dict[str, Any]]
    confidence: float  # 0.0 to 1.0
    reasoning: str


class SelfCorrectingAgent:
    """Agent that can observe, reflect, and self-correct"""
    
    def __init__(self, llm, max_retries: int = 3, debug_mode: bool = False):
        self.llm = llm
        self.max_retries = max_retries
        self.debug_mode = debug_mode
        self.observations_history = []
        self.reflections_history = []
    
    def observe(self, tool_name: str, arguments: Dict[str, Any], result: Any) -> Observation:
        """Record an observation from tool execution"""
        
        # Determine success
        success = False
        error = None
        
        if isinstance(result, dict):
            success = result.get("success", False)
            error = result.get("error")
        
        observation = Observation(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            success=success,
            error=error
        )
        
        self.observations_history.append(observation)
        
        if self.debug_mode:
            print(f"\n📊 OBSERVATION:")
            print(f"   Tool: {tool_name}")
            print(f"   Success: {success}")
            if error:
                print(f"   Error: {error}")
        
        return observation
    
    def reflect(self, observation: Observation, goal: str) -> Reflection:
        """Analyze observation and decide next action"""
        
        if self.debug_mode:
            print(f"\n🤔 REFLECTING...")
        
        # Build reflection prompt
        prompt = f"""
You are an AI agent analyzing the result of a tool execution.

GOAL: {goal}

TOOL EXECUTED: {observation.tool_name}
ARGUMENTS: {observation.arguments}
SUCCESS: {observation.success}
RESULT: {observation.result}
ERROR: {observation.error}

TASK: Analyze this result and provide guidance.

OUTPUT FORMAT (JSON only):
{{
  "reflection_type": "success|partial_success|failure|need_more_info",
  "insights": ["insight 1", "insight 2"],
  "suggested_actions": [
    {{"tool": "tool_name", "arguments": {{}}, "reason": "why this action"}}
  ],
  "confidence": 0.0-1.0,
  "reasoning": "explain your analysis"
}}

REFLECTION TYPES:
- success: Task completed successfully
- partial_success: Made progress but not complete
- failure: Action failed, try different approach
- need_more_info: Need to gather more context
"""
        
        try:
            response = self.llm.generate(prompt)
            
            # Parse response
            import re
            import json
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            reflection = Reflection(
                observation_id=f"obs_{len(self.observations_history)}",
                reflection_type=ReflectionType(data["reflection_type"]),
                insights=data.get("insights", []),
                suggested_actions=data.get("suggested_actions", []),
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", "")
            )
            
            self.reflections_history.append(reflection)
            
            if self.debug_mode:
                print(f"   Type: {reflection.reflection_type.value}")
                print(f"   Confidence: {reflection.confidence:.2f}")
                print(f"   Reasoning: {reflection.reasoning}")
                print(f"   Suggested actions: {len(reflection.suggested_actions)}")
            
            return reflection
            
        except Exception as e:
            print(f"❌ Reflection failed: {e}")
            
            # Fallback reflection
            return Reflection(
                observation_id=f"obs_{len(self.observations_history)}",
                reflection_type=ReflectionType.FAILURE,
                insights=["Failed to analyze observation"],
                suggested_actions=[],
                confidence=0.0,
                reasoning=f"Error during reflection: {e}"
            )
                
    async def act_with_retry(
        self,
        mcp_client,
        server: str,
        initial_tool: str,
        initial_args: Dict[str, Any],
        goal: str
    ) -> Dict[str, Any]:
        """Execute action with automatic retry using different strategies"""
        
        current_tool = initial_tool
        current_args = initial_args
        attempt = 0
        
        while attempt < self.max_retries:
            attempt += 1
            
            if self.debug_mode:
                print(f"\n🎯 ACTION (Attempt {attempt}/{self.max_retries}):")
                print(f"   Tool: {current_tool}")
                print(f"   Arguments: {current_args}")
            
            # Execute tool
            try:
                raw_result = await mcp_client.call_tool(
                    server=server,
                    name=current_tool,
                    arguments=current_args
                )
                
                # Extract result using .data attribute
                result = self._extract_tool_result(raw_result)
                
            except Exception as e:
                result = {"success": False, "error": str(e)}
                if self.debug_mode:
                    print(f"   ❌ Tool execution error: {e}")
            
            # Observe
            observation = self.observe(current_tool, current_args, result)
            
            # If successful, return
            if observation.success:
                if self.debug_mode:
                    print("✓ Action succeeded!")
                return result
            
            # If max retries reached, return failure
            if attempt >= self.max_retries:
                print(f"❌ Max retries reached. Final error: {observation.error}")
                return result
            
            # Reflect on failure
            reflection = self.reflect(observation, goal)
            
            # If no suggestions, stop
            if not reflection.suggested_actions:
                print("❌ No alternative actions suggested")
                return result
            
            # Try first suggested action
            suggested = reflection.suggested_actions[0]
            current_tool = suggested.get("tool", current_tool)
            current_args = suggested.get("arguments", {})
            
            if self.debug_mode:
                print(f"🔄 Retrying with: {current_tool}")
                print(f"   Reason: {suggested.get('reason', 'Unknown')}")
        
        return result

    def _extract_tool_result(self, raw_result: Any) -> Dict[str, Any]:
        """Extract actual result from MCP CallToolResult object"""
        import json
        
        # Use .data attribute if it exists (FastMCP)
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
    # def _extract_tool_result(self, raw_result: Any) -> Dict[str, Any]:
    #     """
    #     Extract the actual result from MCP CallToolResult object
        
    #     The CallToolResult has multiple attributes:
    #     - .data: Direct dict (EASIEST)
    #     - .content: List of TextContent objects
    #     - .structured_content: Also a dict
    #     """
    #     import json
        
    #     # EASIEST: Use .data attribute if it exists
    #     if hasattr(raw_result, 'data') and isinstance(raw_result.data, dict):
    #         return raw_result.data
        
    #     # Fallback: Extract from .content
    #     if hasattr(raw_result, 'content'):
    #         content = raw_result.content
            
    #         if isinstance(content, list) and len(content) > 0:
    #             first_item = content[0]
                
    #             if hasattr(first_item, 'text'):
    #                 text = first_item.text
    #                 try:
    #                     return json.loads(text)
    #                 except:
    #                     return {"success": True, "output": text}
                
    #             return {"success": True, "content": str(first_item)}
            
    #         return {"success": False, "error": "Empty content"}
        
    #     # If already a dict, return as-is
    #     if isinstance(raw_result, dict):
    #         return raw_result
        
    #     # Fallback
    #     return {"success": False, "error": f"Cannot extract result from {type(raw_result)}"}
        
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of all observations and reflections"""
        return {
            "total_observations": len(self.observations_history),
            "total_reflections": len(self.reflections_history),
            "success_rate": sum(1 for obs in self.observations_history if obs.success) / max(len(self.observations_history), 1),
            "observations": [
                {
                    "tool": obs.tool_name,
                    "success": obs.success,
                    "timestamp": obs.timestamp
                }
                for obs in self.observations_history
            ],
            "reflections": [
                {
                    "type": ref.reflection_type.value,
                    "confidence": ref.confidence,
                    "insights": ref.insights
                }
                for ref in self.reflections_history
            ]
        }
    
    # Make sure this method is INSIDE the SelfCorrectingAgent class
    # (around line 150, after get_execution_summary method)

    def _extract_tool_result(self, raw_result: Any) -> Dict[str, Any]:
        """Extract actual result from MCP CallToolResult object"""
        import json
        
        # Use .data attribute if it exists (FastMCP)
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