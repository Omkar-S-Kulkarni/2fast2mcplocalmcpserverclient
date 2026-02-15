# config.py

import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# ============================================================
# SERVER CONNECTION
# ============================================================

SERVERS = [
    {
        "name": "terminal",
        "command": ["python", "D:/MCPserver/projects/terminal/s/server.py"],
    }
]

# ============================================================
# SAFETY: ALLOWED TOOLS
# ============================================================

ALLOWED_TOOLS = {
    "terminal": {
        # Terminal execution
        "run_command",
        "interactive_command",
        
        # Filesystem operations
        "read_file",
        "write_file",
        "list_directory",
        "search_files",
        "replace_in_file",
        
        # Process management
        "list_processes",
        "kill_process",
        
        # Environment & system
        "get_env",
        "system_info",
        
        # Git operations
        "git_status",
        "git_diff",
        "git_commit",
        
        # Logs & monitoring
        "tail_file",
        
        # Network
        "check_port",
        
        # Docker
        "docker_ps",

        "analyze_code_quality",
        "detect_security_issues",
        "profile_code_performance",
        
        # Project-Level Operations
        "analyze_project_structure",
        "detect_circular_dependencies",
        "generate_dependency_graph",
        
        # Debugging Tools
        "trace_execution",
        "analyze_error_logs",
        "compare_outputs",
        
        # Testing Tools
        "generate_unit_tests",
        "run_tests_with_coverage",
        "detect_test_gaps",
        "trace_error_origin",
        "find_breaking_change",
        "refactor_function_name",
        "inspect_running_process",
        "detect_memory_leaks",
        # Phase 5
        "undo_last_action",
        "run_command_sandboxed",
        "backup_before_operation",
        "clear_cache",

        # Phase 7
        "ai_code_review",
        "generate_docs",
        "semantic_code_search",
        "list_directory_contents"
    }
}

# ============================================================
# SAFETY: ALLOWED RESOURCES
# ============================================================

ALLOWED_RESOURCES = {
    "terminal": {
        # Workspace resources
        "workspace://tree",
        "workspace://summary",
        
        # File resources (dynamic paths handled separately)
        # "file://{path}" - validated at runtime
        
        # System resources
        "system://info",
        "system://env",
        "system://disk",
        "system://processes",
        
        # Terminal resources
        "terminal://history",
        
        # Git resources
        "git://status",
        "git://diff",
        "git://log",
        
        # Log resources
        "logs://app",
        "logs://errors",
        
        # Session resources
        "session://cwd",
        "session://tasks",
        "project://complexity",
        "project://dependencies",
        "project://test-coverage",
        "monitor://cpu",
        "monitor://memory",
        "monitor://file-changes",
        "monitor://disk",
        # Phase 5
        "metrics://tool-performance",
        "cache://stats",
        "monitor://cpu",
    }
}

# ============================================================
# SAFETY: ALLOWED PROMPTS
# ============================================================

ALLOWED_PROMPTS = {
    "terminal": {
        "terminal_system_prompt",
        "terminal_command_planning_prompt",
        "terminal_resource_usage_prompt",
        "terminal_execution_rules_prompt",
        "terminal_debugging_prompt",
        "terminal_long_running_prompt",
        "terminal_safety_prompt",
        "terminal_response_style_prompt",
    }
}

# ============================================================
# CONTEXT CONTROL
# ============================================================

MAX_CONTEXT_ITEMS = 10  # Terminal sessions may need more context

# ============================================================
# OBSERVABILITY
# ============================================================

ENABLE_TRACING = True
ENABLE_CACHE = True

# ============================================================
# RETRIES / TIMEOUT
# ============================================================

MAX_RETRIES = 2
RESOURCE_TIMEOUT_SECONDS = 10  # Terminal operations may take longer
COMMAND_TIMEOUT_SECONDS = 300  # 5 minutes for long-running commands

# ============================================================
# CIRCUIT BREAKER
# ============================================================

FAILURE_THRESHOLD = 3
CIRCUIT_BREAKER_COOLDOWN = 10

# ============================================================
# LLM CONFIGURATION
# ============================================================

OLLAMA_MODEL = "qwen2.5-coder:7b"
OLLAMA_TIMEOUT_SECONDS = 600

# OPENROUTER_API_KEY = "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"

# # OPENROUTER_API_KEY = "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"
# OPENROUTER_TIMEOUT_SECONDS = 120
# OPENROUTER_MODEL = "x-ai/grok-code-fast-1"
#i will conver this to opnline later so  i have commented out this 



# ============================================================
# ADVANCED AGENT CONFIGURATION
# ============================================================

# Planning
MAX_SUBTASKS = 10
PLAN_VALIDATION_STRICT = True

# Self-correction
MAX_RETRIES = 3
RETRY_STRATEGIES = ["alternative_tool", "modified_arguments", "different_approach"]

# Context management
MAX_CONTEXT_ITEMS = 50
CONTEXT_RELEVANCE_THRESHOLD = 0.3
AUTO_CHECKPOINT_INTERVAL = 10  # Save checkpoint every N interactions

# Tool chaining
ENABLE_PARALLEL_EXECUTION = True
MAX_PARALLEL_TOOLS = 3

# Debug mode
AGENT_DEBUG_MODE = True  # Set to False for production


