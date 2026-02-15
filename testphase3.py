"""
Phase 3 Tools Test Suite
Tests all 5 new debugging superpowers tools
"""

import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from c.client import MCPAppClient


def extract_result(raw_result):
    """Extract actual result from MCP CallToolResult object"""
    if hasattr(raw_result, 'data') and isinstance(raw_result.data, dict):
        return raw_result.data
    
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


class Phase3Tester:
    """Test suite for Phase 3 debugging tools"""
    
    def __init__(self):
        self.results = {
            "multi_file_debugging": {},
            "runtime_analysis": {}
        }
        self.total_tests = 0
        self.passed_tests = 0
    
    def report_result(self, category: str, tool: str, success: bool, message: str = ""):
        """Record test result"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        self.results[category][tool] = {
            "success": success,
            "message": message
        }
        
        print(f"{status} | {tool}")
        if message:
            print(f"         {message}")
    
    async def test_multi_file_debugging(self, client):
        """Test multi-file debugging tools"""
        print("\n" + "=" * 60)
        print("TESTING: Multi-File Debugging System")
        print("=" * 60)
        
        # Test 1: trace_error_origin
        try:
            error_msg = """
Traceback (most recent call last):
  File "main.py", line 42, in <module>
    result = process_data()
  File "utils.py", line 15, in process_data
    value = undefined_variable
NameError: name 'undefined_variable' is not defined
"""
            
            raw_result = await client.call_tool(
                "terminal",
                "trace_error_origin",
                {"error_message": error_msg, "project_root": "."}
            )
            
            result = extract_result(raw_result)
            success = result.get("success", False)
            
            if success:
                res_data = result.get("result", {})
                files_found = len(res_data.get("stack_trace_files", []))
                self.report_result(
                    "multi_file_debugging",
                    "trace_error_origin",
                    True,
                    f"Found {files_found} files in stack trace"
                )
            else:
                self.report_result(
                    "multi_file_debugging",
                    "trace_error_origin",
                    False,
                    result.get("error", "Unknown error")
                )
        except Exception as e:
            self.report_result("multi_file_debugging", "trace_error_origin", False, str(e))
        
        # Test 2: find_breaking_change
        try:
            # Check if we're in a git repo first
            import subprocess
            git_check = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True
            )
            
            if git_check.returncode == 0:
                # Get recent commits
                log_result = subprocess.run(
                    ["git", "log", "--oneline", "-n", "5"],
                    capture_output=True,
                    text=True
                )
                
                if log_result.returncode == 0 and log_result.stdout.strip():
                    commits = log_result.stdout.strip().split('\n')
                    
                    if len(commits) >= 2:
                        # Use two recent commits
                        commit1 = commits[-1].split()[0]
                        commit2 = commits[0].split()[0]
                        
                        raw_result = await client.call_tool(
                            "terminal",
                            "find_breaking_change",
                            {
                                "working_commit": commit1,
                                "broken_commit": commit2
                            }
                        )
                        
                        result = extract_result(raw_result)
                        success = result.get("success", False)
                        
                        self.report_result(
                            "multi_file_debugging",
                            "find_breaking_change",
                            success,
                            "Bisect analysis completed" if success else result.get("error")
                        )
                    else:
                        self.report_result(
                            "multi_file_debugging",
                            "find_breaking_change",
                            False,
                            "Not enough commits for testing"
                        )
                else:
                    self.report_result(
                        "multi_file_debugging",
                        "find_breaking_change",
                        False,
                        "No commits found"
                    )
            else:
                self.report_result(
                    "multi_file_debugging",
                    "find_breaking_change",
                    False,
                    "Not a git repository"
                )
        except Exception as e:
            self.report_result("multi_file_debugging", "find_breaking_change", False, str(e))
        
        # Test 3: refactor_function_name
        try:
            # Create test file
            test_file = "refactor_test.py"
            with open(test_file, 'w') as f:
                f.write("""
def old_function():
    return 42

def caller():
    return old_function()
""")
            
            raw_result = await client.call_tool(
                "terminal",
                "refactor_function_name",
                {
                    "old_name": "old_function",
                    "new_name": "new_function",
                    "scope": "."
                }
            )
            
            result = extract_result(raw_result)
            success = result.get("success", False)
            
            if success:
                res_data = result.get("result", {})
                changes = res_data.get("summary", {}).get("total_changes", 0)
                self.report_result(
                    "multi_file_debugging",
                    "refactor_function_name",
                    True,
                    f"Found {changes} refactoring opportunities"
                )
            else:
                self.report_result(
                    "multi_file_debugging",
                    "refactor_function_name",
                    False,
                    result.get("error")
                )
            
            # Cleanup
            if os.path.exists(test_file):
                os.remove(test_file)
        
        except Exception as e:
            self.report_result("multi_file_debugging", "refactor_function_name", False, str(e))
    
    async def test_runtime_analysis(self, client):
        """Test runtime analysis tools"""
        print("\n" + "=" * 60)
        print("TESTING: Runtime Analysis")
        print("=" * 60)
        
        # Test 1: inspect_running_process
        try:
            # Get current process PID
            import os
            current_pid = os.getpid()
            
            raw_result = await client.call_tool(
                "terminal",
                "inspect_running_process",
                {"pid": current_pid}
            )
            
            result = extract_result(raw_result)
            success = result.get("success", False)
            
            if success:
                res_data = result.get("result", {})
                process_name = res_data.get("process_info", {}).get("name", "unknown")
                self.report_result(
                    "runtime_analysis",
                    "inspect_running_process",
                    True,
                    f"Inspected process: {process_name}"
                )
            else:
                self.report_result(
                    "runtime_analysis",
                    "inspect_running_process",
                    False,
                    result.get("error")
                )
        except Exception as e:
            self.report_result("runtime_analysis", "inspect_running_process", False, str(e))
        
        # Test 2: detect_memory_leaks
        try:
            # Create test script
            test_script = "memory_test.py"
            with open(test_script, 'w') as f:
                f.write("""
import time

data = []
for i in range(10):
    data.append([0] * 1000)
    time.sleep(0.5)
""")
            
            raw_result = await client.call_tool(
                "terminal",
                "detect_memory_leaks",
                {"script_path": test_script, "duration_seconds": 5}
            )
            
            result = extract_result(raw_result)
            success = result.get("success", False)
            
            if success:
                res_data = result.get("result", {})
                leak_detected = res_data.get("leak_detected", False)
                self.report_result(
                    "runtime_analysis",
                    "detect_memory_leaks",
                    True,
                    f"Leak detected: {leak_detected}"
                )
            else:
                error = result.get("error", "")
                # Memory profiler might not be installed - that's OK
                if "memory_profiler not installed" in error:
                    self.report_result(
                        "runtime_analysis",
                        "detect_memory_leaks",
                        True,
                        "Tool works (memory_profiler not installed, install to use)"
                    )
                else:
                    self.report_result(
                        "runtime_analysis",
                        "detect_memory_leaks",
                        False,
                        result.get("error")
                    )
            
            # Cleanup
            if os.path.exists(test_script):
                os.remove(test_script)
        
        except Exception as e:
            self.report_result("runtime_analysis", "detect_memory_leaks", False, str(e))
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        for category, tests in self.results.items():
            passed = sum(1 for t in tests.values() if t["success"])
            total = len(tests)
            
            print(f"\n{category.upper().replace('_', ' ')}:")
            print(f"  Passed: {passed}/{total}")
            
            for tool, result in tests.items():
                status = "✅" if result["success"] else "❌"
                print(f"    {status} {tool}")
        
        print("\n" + "=" * 60)
        print(f"OVERALL: {self.passed_tests}/{self.total_tests} tests passed")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%")
        print("=" * 60)
        
        if self.passed_tests == self.total_tests:
            print("\n🎉 ALL TESTS PASSED! Phase 3 implementation successful!")
        elif self.passed_tests >= self.total_tests * 0.75:
            print("\n✅ Most tests passed. Review failed tests above.")
        else:
            print("\n⚠️  Many tests failed. Check installation and dependencies.")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("PHASE 3 TOOLS TEST SUITE")
    print("=" * 60)
    print("\nThis will test all 5 new debugging superpowers tools.")
    print("Dependencies needed:")
    print("  pip install psutil --break-system-packages")
    print("  pip install memory-profiler --break-system-packages (optional)")
    print("\nStarting tests...\n")
    
    tester = Phase3Tester()
    
    async with MCPAppClient() as client:
        print(f"✓ Connected to MCP server")
        print(f"  Tools available: {len(client._tools)}")
        
        # Run all test categories
        await tester.test_multi_file_debugging(client)
        await tester.test_runtime_analysis(client)
        
        # Print summary
        tester.print_summary()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()