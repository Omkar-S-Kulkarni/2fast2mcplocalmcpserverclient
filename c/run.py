# run.py
"""
Enhanced Terminal MCP Client - Production Mode
With Phases 1-7 Integrated

Features:
- Phase 1: Core Architecture
- Phase 2: 12 Code Analysis Tools
- Phase 3: 5 Debugging Tools
- Phase 4: 7 Monitoring Resources
- Phase 5: Production Features (Undo, Sandbox, Metrics, Cache)
- Phase 7: AI-Powered Tools (Code Review, Docs, Search)

Commands:
    chat      -> Interactive chat mode
    tools     -> List all available tools
    resources -> List all available resources
    metrics   -> Show tool performance metrics
    cache     -> Show cache statistics
    review    -> AI code review on a file
    docs      -> Generate project documentation
    search    -> Semantic code search
    monitor   -> System monitoring dashboard
    help      -> Show all commands
    exit      -> Quit

Any other input is treated as a tool-aware query.
"""

import asyncio
import sys
import os
from typing import Optional

from client import MCPAppClient
from agent import TerminalAgent
from config import AGENT_DEBUG_MODE


class EnhancedTerminalClient:
    """Enhanced terminal client with all Phase 1-7 features"""
    
    def __init__(self, mcp_client: MCPAppClient, agent: TerminalAgent):
        self.client = mcp_client
        self.agent = agent
    
    async def show_tools(self):
        """Display all available tools grouped by phase"""
        print("\n" + "=" * 60)
        print("AVAILABLE TOOLS")
        print("=" * 60)
        
        # Group tools by phase
        phases = {
            "Core Terminal": [
                "run_command", "interactive_command", "read_file", "write_file",
                "list_directory", "search_files", "replace_in_file", "list_processes",
                "kill_process", "get_env", "system_info", "git_status", "git_diff",
                "git_commit", "tail_file", "check_port", "docker_ps"
            ],
            "Code Analysis (Phase 2)": [
                "analyze_code_quality", "detect_security_issues", "profile_code_performance",
                "analyze_project_structure", "detect_circular_dependencies", 
                "generate_dependency_graph", "trace_execution", "analyze_error_logs",
                "compare_outputs", "generate_unit_tests", "run_tests_with_coverage",
                "detect_test_gaps"
            ],
            "Debugging (Phase 3)": [
                "trace_error_origin", "find_breaking_change", "refactor_function_name",
                "inspect_running_process", "detect_memory_leaks"
            ],
            "Production (Phase 5)": [
                "undo_last_action", "run_command_sandboxed", "backup_before_operation",
                "clear_cache"
            ],
            "AI-Powered (Phase 7)": [
                "ai_code_review", "generate_docs", "semantic_code_search"
            ]
        }
        
        total_tools = 0
        for phase_name, tools in phases.items():
            print(f"\n{phase_name}:")
            available = [t for t in tools if t in self.client._tools]
            total_tools += len(available)
            
            for tool in available:
                print(f"  ✓ {tool}")
            
            missing = [t for t in tools if t not in self.client._tools]
            for tool in missing:
                print(f"  ✗ {tool} (not registered)")
        
        print(f"\n{'=' * 60}")
        print(f"Total Available: {total_tools} tools")
        print("=" * 60 + "\n")
    
    async def show_resources(self):
        """Display all available resources"""
        print("\n" + "=" * 60)
        print("AVAILABLE RESOURCES")
        print("=" * 60)
        
        resources = {
            "Workspace": ["workspace://tree", "workspace://summary"],
            "System": ["system://info", "system://env", "system://disk", "system://processes"],
            "Git": ["git://status", "git://diff", "git://log"],
            "Session": ["session://cwd", "session://tasks"],
            "Project Intelligence (Phase 4)": [
                "project://complexity", "project://dependencies", "project://test-coverage"
            ],
            "Monitoring (Phase 4)": [
                "monitor://cpu", "monitor://memory", "monitor://file-changes", "monitor://disk"
            ],
            "Metrics (Phase 5)": [
                "metrics://tool-performance", "cache://stats"
            ]
        }
        
        total_resources = 0
        for category, res_list in resources.items():
            print(f"\n{category}:")
            for res in res_list:
                if res in self.client._resources:
                    print(f"  ✓ {res}")
                    total_resources += 1
                else:
                    print(f"  ✗ {res} (not registered)")
        
        print(f"\n{'=' * 60}")
        print(f"Total Available: {total_resources} resources")
        print("=" * 60 + "\n")
    
    async def show_metrics(self):
        """Show tool performance metrics"""
        print("\n🔍 Fetching tool performance metrics...\n")
        
        try:
            result = await self.client.read_resource("terminal", "metrics://tool-performance")
            
            # Extract metrics
            if hasattr(result, '__iter__') and len(result) > 0:
                first_item = result[0]
                if hasattr(first_item, 'contents'):
                    import json
                    metrics_data = json.loads(first_item.contents)
                    
                    print("=" * 60)
                    print("TOOL PERFORMANCE METRICS")
                    print("=" * 60)
                    
                    if "metrics" in metrics_data:
                        metrics = metrics_data["metrics"]
                        
                        if not metrics:
                            print("\nNo metrics available yet. Use some tools first!\n")
                            return
                        
                        # Sort by total calls
                        sorted_tools = sorted(
                            metrics.items(), 
                            key=lambda x: x[1].get("total_calls", 0), 
                            reverse=True
                        )
                        
                        print(f"\n{'Tool':<30} {'Calls':<8} {'Success':<8} {'Avg (ms)':<10}")
                        print("-" * 60)
                        
                        for tool_name, data in sorted_tools[:20]:  # Top 20
                            calls = data.get("total_calls", 0)
                            success_rate = data.get("success_rate", 0)
                            avg_duration = data.get("avg_duration_ms", 0)
                            
                            print(f"{tool_name:<30} {calls:<8} {success_rate:<7.1f}% {avg_duration:<10.2f}")
                        
                        print("\n" + "=" * 60 + "\n")
                    else:
                        print("No metrics data found.\n")
            else:
                print("Could not retrieve metrics.\n")
        
        except Exception as e:
            print(f"Error fetching metrics: {e}\n")
    
    async def show_cache_stats(self):
        """Show cache statistics"""
        print("\n🔍 Fetching cache statistics...\n")
        
        try:
            result = await self.client.read_resource("terminal", "cache://stats")
            
            if hasattr(result, '__iter__') and len(result) > 0:
                first_item = result[0]
                if hasattr(first_item, 'contents'):
                    import json
                    cache_data = json.loads(first_item.contents)
                    
                    print("=" * 60)
                    print("CACHE STATISTICS")
                    print("=" * 60)
                    print(f"\nSize: {cache_data.get('size', 0)} / {cache_data.get('max_size', 0)} entries")
                    print(f"Memory: {cache_data.get('memory_mb', 0)} MB")
                    print(f"Utilization: {cache_data.get('utilization', 0)}%")
                    print("\n" + "=" * 60 + "\n")
        
        except Exception as e:
            print(f"Error fetching cache stats: {e}\n")
    
    async def ai_code_review_interactive(self):
        """Interactive AI code review"""
        print("\n" + "=" * 60)
        print("AI CODE REVIEW")
        print("=" * 60)
        
        file_path = input("Enter file path to review: ").strip()
        
        if not file_path:
            print("No file specified.\n")
            return
        
        print(f"\n🔍 Reviewing {file_path}...\n")
        
        response = await self.agent.answer(
            f"Please perform an AI code review on {file_path}. "
            f"Check for code quality, security issues, and style problems."
        )
        
        print(response)
        print()
    
    async def generate_docs_interactive(self):
        """Interactive documentation generation"""
        print("\n" + "=" * 60)
        print("GENERATE PROJECT DOCUMENTATION")
        print("=" * 60)
        
        project_root = input("Enter project root (default: current directory): ").strip()
        if not project_root:
            project_root = "."
        
        print(f"\n📝 Generating documentation for {project_root}...\n")
        
        response = await self.agent.answer(
            f"Generate comprehensive project documentation for {project_root}. "
            f"Include README, API docs, architecture overview, and examples."
        )
        
        print(response)
        print()
    
    async def semantic_search_interactive(self):
        """Interactive semantic code search"""
        print("\n" + "=" * 60)
        print("SEMANTIC CODE SEARCH")
        print("=" * 60)
        
        query = input("Enter your search query: ").strip()
        
        if not query:
            print("No query specified.\n")
            return
        
        print(f"\n🔍 Searching for: {query}...\n")
        
        response = await self.agent.answer(
            f"Search the codebase for: {query}"
        )
        
        print(response)
        print()
    
    async def system_monitor(self):
        """Show system monitoring dashboard"""
        print("\n" + "=" * 60)
        print("SYSTEM MONITORING DASHBOARD")
        print("=" * 60)
        
        try:
            # CPU
            print("\n📊 CPU Usage:")
            cpu_result = await self.client.read_resource("terminal", "monitor://cpu")
            if hasattr(cpu_result, '__iter__') and len(cpu_result) > 0:
                first_item = cpu_result[0]
                if hasattr(first_item, 'contents'):
                    import json
                    cpu_data = json.loads(first_item.contents)
                    print(f"  System: {cpu_data.get('system', {}).get('cpu_percent', 0)}%")
                    if 'server_process' in cpu_data:
                        print(f"  Server: {cpu_data['server_process'].get('cpu_percent', 0)}%")
            
            # Memory
            print("\n💾 Memory Usage:")
            mem_result = await self.client.read_resource("terminal", "monitor://memory")
            if hasattr(mem_result, '__iter__') and len(mem_result) > 0:
                first_item = mem_result[0]
                if hasattr(first_item, 'contents'):
                    import json
                    mem_data = json.loads(first_item.contents)
                    sys_mem = mem_data.get('system', {})
                    print(f"  Total: {sys_mem.get('total_gb', 0)} GB")
                    print(f"  Used: {sys_mem.get('used_gb', 0)} GB ({sys_mem.get('percent', 0)}%)")
                    print(f"  Available: {sys_mem.get('available_gb', 0)} GB")
            
            # Disk
            print("\n💿 Disk Usage:")
            disk_result = await self.client.read_resource("terminal", "monitor://disk")
            if hasattr(disk_result, '__iter__') and len(disk_result) > 0:
                first_item = disk_result[0]
                if hasattr(first_item, 'contents'):
                    import json
                    disk_data = json.loads(first_item.contents)
                    workspace = disk_data.get('workspace', {})
                    if workspace:
                        print(f"  Total: {workspace.get('total_gb', 0)} GB")
                        print(f"  Used: {workspace.get('used_gb', 0)} GB ({workspace.get('percent', 0)}%)")
                        print(f"  Free: {workspace.get('free_gb', 0)} GB")
            
            print("\n" + "=" * 60 + "\n")
        
        except Exception as e:
            print(f"\nError fetching monitoring data: {e}\n")
    
    def show_help(self):
        """Show all available commands"""
        print("\n" + "=" * 60)
        print("AVAILABLE COMMANDS")
        print("=" * 60)
        print("""
📋 Information:
  tools      - List all available tools
  resources  - List all available resources
  help       - Show this help message

📊 Monitoring:
  metrics    - Show tool performance metrics
  cache      - Show cache statistics
  monitor    - System monitoring dashboard

🤖 AI Features:
  review     - AI code review on a file
  docs       - Generate project documentation
  search     - Semantic code search

💬 Interaction:
  chat       - Interactive chat mode
  exit/quit  - Exit the application

📝 Direct Commands:
  Any other input is treated as a natural language query
  and will be processed by the AI agent with full tool access.

Examples:
  > analyze the code quality of app.py
  > find all functions without error handling
  > show me system resource usage
  > create a backup of config.py
  > review src/main.py for security issues
        """)
        print("=" * 60 + "\n")


async def main():
    print("=" * 60)
    print("🚀 Terminal MCP Client - Production Mode")
    print("=" * 60)
    print("\n✨ Features:")
    print("  • 42+ Advanced Tools")
    print("  • 9 Monitoring Resources")
    print("  • AI-Powered Code Review")
    print("  • Performance Metrics")
    print("  • Smart Caching")
    print("  • Production Safety Features")
    print()

    async with MCPAppClient() as mcp_client:
        print("✓ Connected to MCP server")
        print(f"  Tools     : {len(mcp_client._tools)}")
        print(f"  Resources : {len(mcp_client._resources)}")
        print(f"  Prompts   : {len(mcp_client._prompts)}")
        print()

        agent = TerminalAgent(mcp_client, debug_mode=AGENT_DEBUG_MODE)
        enhanced_client = EnhancedTerminalClient(mcp_client, agent)
        
        print("💡 Type 'help' for all commands, 'exit' to quit")
        print("-" * 60)

        while True:
            try:
                user_input = input("🖥️  > ").strip()

                # Exit
                if user_input.lower() in ["exit", "quit"]:
                    print("👋 Closing client...")
                    break

                # Help
                if user_input.lower() == "help":
                    enhanced_client.show_help()
                    continue

                # List tools
                if user_input.lower() == "tools":
                    await enhanced_client.show_tools()
                    continue

                # List resources
                if user_input.lower() == "resources":
                    await enhanced_client.show_resources()
                    continue

                # Show metrics
                if user_input.lower() == "metrics":
                    await enhanced_client.show_metrics()
                    continue

                # Show cache stats
                if user_input.lower() == "cache":
                    await enhanced_client.show_cache_stats()
                    continue

                # AI Code Review
                if user_input.lower() == "review":
                    await enhanced_client.ai_code_review_interactive()
                    continue

                # Generate Docs
                if user_input.lower() == "docs":
                    await enhanced_client.generate_docs_interactive()
                    continue

                # Semantic Search
                if user_input.lower() == "search":
                    await enhanced_client.semantic_search_interactive()
                    continue

                # System Monitor
                if user_input.lower() == "monitor":
                    await enhanced_client.system_monitor()
                    continue

                # Interactive Chat Mode
                if user_input.lower() == "chat":
                    print("\n💬 Chat mode (all features enabled)")
                    print("Type 'exit' to return\n")

                    while True:
                        msg = input("💬 > ").strip()

                        if msg.lower() in ["exit", "quit"]:
                            print("Leaving chat mode...\n")
                            break

                        if not msg:
                            continue

                        try:
                            print("\n🤖 Thinking...\n")
                            response = await agent.answer(msg)
                            print(response)
                            print()
                        except Exception as e:
                            print(f"❌ Error: {e}\n")

                    continue

                # Default: Tool-aware agent processing
                if not user_input:
                    continue

                print("\n🤖 Processing...\n")

                try:
                    response = await agent.answer(user_input)
                    print(response)
                    print()
                except Exception as e:
                    print(f"❌ Error: {e}\n")

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Closing client...")
                break
            except EOFError:
                print("\n\n👋 EOF received. Closing client...")
                break


# Entry Point
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)