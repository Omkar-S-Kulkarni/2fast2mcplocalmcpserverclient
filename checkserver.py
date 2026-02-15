"""
Diagnostic Script - Check what's breaking the MCP server

Run this to see exactly what's wrong:
python check_server.py
"""

import sys
import os

# Add your project path
sys.path.insert(0, "D:/MCPserver/projects/terminal")

print("=" * 60)
print("MCP SERVER DIAGNOSTIC CHECK")
print("=" * 60)
print()

# Check 1: Can we import tools.py?
print("1. Checking tools.py import...")
try:
    from s import tools
    print("   ✅ tools.py imports successfully")
except Exception as e:
    print(f"   ❌ ERROR importing tools.py:")
    print(f"      {str(e)}")
    import traceback
    traceback.print_exc()
    print()
    print("   SOLUTION: The error above shows the exact line causing the crash")
    sys.exit(1)

# Check 2: Can we import resources.py?
print("\n2. Checking resources.py import...")
try:
    from s import resources
    print("   ✅ resources.py imports successfully")
except Exception as e:
    print(f"   ❌ ERROR importing resources.py:")
    print(f"      {str(e)}")
    import traceback
    traceback.print_exc()

# Check 3: Are tools registered?
print("\n3. Checking tool registration...")
try:
    from s.state import get_server_state
    state = get_server_state()
    print(f"   ✅ {len(state.registered_tools)} tools registered")
    
    # Check for Phase 2-7 tools
    phase2_tools = ["analyze_code_quality", "detect_security_issues"]
    phase3_tools = ["trace_error_origin", "inspect_running_process"]
    phase5_tools = ["undo_last_action", "clear_cache"]
    
    for tool in phase2_tools + phase3_tools + phase5_tools:
        if tool in state.registered_tools:
            print(f"   ✅ {tool} registered")
        else:
            print(f"   ❌ {tool} NOT registered")
    
except Exception as e:
    print(f"   ❌ ERROR checking registration:")
    print(f"      {str(e)}")

# Check 4: Are resources registered?
print("\n4. Checking resource registration...")
try:
    phase4_resources = ["project_complexity", "cpu_usage_stream"]
    phase5_resources = ["tool_performance_stats", "cache_statistics"]
    
    for resource in phase4_resources + phase5_resources:
        if resource in state.registered_resources:
            print(f"   ✅ {resource} registered")
        else:
            print(f"   ❌ {resource} NOT registered")
    
except Exception as e:
    print(f"   ❌ ERROR checking resources:")
    print(f"      {str(e)}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
print("\nIf you see ❌ errors above, that's what's breaking your server!")
print("Copy the error message and I'll help you fix it.")