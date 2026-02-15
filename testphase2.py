"""
Phase 2 Tools Testing Script (FIXED)
Tests all 12 new advanced tools to verify implementation
"""

import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from client import MCPAppClient


def extract_result(raw_result):
    """Extract actual result from MCP CallToolResult object"""
    import json
    
    # Try .data attribute first (FastMCP)
    if hasattr(raw_result, 'data') and isinstance(raw_result.data, dict):
        return raw_result.data
    
    # Try .content attribute
    if hasattr(raw_result, 'content'):
        content = raw_result.content
        
        if isinstance(content, list) and len(content) > 0:
            first_item = content[0]
            
            if hasattr(first_item, 'text'):
                try:
                    return json.loads(first_item.text)
                except:
                    return {"success": True, "output": first_item.text}
        
        return {"success": False, "error": "Empty content"}
    
    # If already a dict, return as-is
    if isinstance(raw_result, dict):
        return raw_result
    
    return {"success": False, "error": f"Cannot extract result from {type(raw_result)}"}


class Phase2Tester:
    """Test suite for Phase 2 advanced tools"""
    
    def __init__(self):
        self.results = {
            "code_analysis": {},
            "project_operations": {},
            "debugging": {},
            "testing": {}
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
    
    async def test_code_analysis(self, client):
        """Test code analysis tools"""
        print("\n" + "=" * 60)
        print("TESTING: Code Analysis Tools")
        print("=" * 60)
        
        # Create test file
        test_file = "test_sample.py"
        test_code = '''
def hello(name):
    """Say hello"""
    print(f"Hello {name}")
    return True

class Calculator:
    def add(self, a, b):
        return a + b
    
    def divide(self, a, b):
        return a / b  # No zero check - security issue
'''
        
        with open(test_file, 'w') as f:
            f.write(test_code)
        
        try:
            # Test 1: analyze_code_quality
            try:
                raw_result = await client.call_tool(
                    "terminal",
                    "analyze_code_quality",
                    {"path": test_file}
                )
                
                result = extract_result(raw_result)
                success = result.get("success", False)
                has_results = "result" in result if success else False
                
                self.report_result(
                    "code_analysis",
                    "analyze_code_quality",
                    success and has_results,
                    "Tool executed successfully" if success else result.get("error", "Unknown error")
                )
            except Exception as e:
                self.report_result("code_analysis", "analyze_code_quality", False, str(e))
            
            # Test 2: detect_security_issues
            try:
                raw_result = await client.call_tool(
                    "terminal",
                    "detect_security_issues",
                    {"path": test_file}
                )
                
                result = extract_result(raw_result)
                success = result.get("success", False)
                self.report_result(
                    "code_analysis",
                    "detect_security_issues",
                    success,
                    "Security scan completed" if success else result.get("error", "Unknown error")
                )
            except Exception as e:
                self.report_result("code_analysis", "detect_security_issues", False, str(e))
            
            # Test 3: profile_code_performance
            try:
                raw_result = await client.call_tool(
                    "terminal",
                    "profile_code_performance",
                    {"file_path": test_file}
                )
                
                result = extract_result(raw_result)
                success = result.get("success", False)
                self.report_result(
                    "code_analysis",
                    "profile_code_performance",
                    success,
                    "Profiling completed" if success else result.get("error", "Unknown error")
                )
            except Exception as e:
                self.report_result("code_analysis", "profile_code_performance", False, str(e))
        
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.remove(test_file)
    
    async def test_project_operations(self, client):
        """Test project-level operation tools"""
        print("\n" + "=" * 60)
        print("TESTING: Project-Level Operations")
        print("=" * 60)
        
        # Test 1: analyze_project_structure
        try:
            raw_result = await client.call_tool(
                "terminal",
                "analyze_project_structure",
                {}
            )
            
            result = extract_result(raw_result)
            success = result.get("success", False)
            has_data = "result" in result and "python_files" in result.get("result", {}) if success else False
            
            self.report_result(
                "project_operations",
                "analyze_project_structure",
                success and has_data,
                f"Found {len(result.get('result', {}).get('python_files', []))} Python files" if success else result.get("error")
            )
        except Exception as e:
            self.report_result("project_operations", "analyze_project_structure", False, str(e))
        
        # Test 2: detect_circular_dependencies
        try:
            raw_result = await client.call_tool(
                "terminal",
                "detect_circular_dependencies",
                {}
            )
            
            result = extract_result(raw_result)
            success = result.get("success", False)
            self.report_result(
                "project_operations",
                "detect_circular_dependencies",
                success,
                f"Analyzed {result.get('result', {}).get('modules_analyzed', 0)} modules" if success else result.get("error")
            )
        except Exception as e:
            self.report_result("project_operations", "detect_circular_dependencies", False, str(e))
        
        # Test 3: generate_dependency_graph
        try:
            raw_result = await client.call_tool(
                "terminal",
                "generate_dependency_graph",
                {}
            )
            
            result = extract_result(raw_result)
            success = result.get("success", False)
            has_output = "result" in result and "output_file" in result.get("result", {}) if success else False
            
            self.report_result(
                "project_operations",
                "generate_dependency_graph",
                success and has_output,
                f"Generated graph with {result.get('result', {}).get('nodes', 0)} nodes" if success else result.get("error")
            )
            
            # Cleanup
            dot_file = result.get("result", {}).get("output_file")
            if dot_file and os.path.exists(dot_file):
                os.remove(dot_file)
        
        except Exception as e:
            self.report_result("project_operations", "generate_dependency_graph", False, str(e))
    
    async def test_debugging_tools(self, client):
        """Test debugging tools"""
        print("\n" + "=" * 60)
        print("TESTING: Debugging Tools")
        print("=" * 60)
        
        # Create test files
        test_file = "debug_sample.py"
        log_file = "test.log"
        compare_file1 = "compare1.txt"
        compare_file2 = "compare2.txt"
        
        with open(test_file, 'w') as f:
            f.write("def test():\n    return 42\n\ntest()")
        
        with open(log_file, 'w') as f:
            f.write("INFO: Starting\n")
            f.write("ERROR: File not found\n")
            f.write("EXCEPTION: Division by zero\n")
            f.write("INFO: Complete\n")
        
        with open(compare_file1, 'w') as f:
            f.write("Line 1\nLine 2\nLine 3")
        
        with open(compare_file2, 'w') as f:
            f.write("Line 1\nLine 2 Modified\nLine 3")
        
        try:
            # Test 1: trace_execution
            try:
                raw_result = await client.call_tool(
                    "terminal",
                    "trace_execution",
                    {"file_path": test_file}
                )
                
                result = extract_result(raw_result)
                success = result.get("success", False)
                self.report_result(
                    "debugging",
                    "trace_execution",
                    success,
                    "Execution traced" if success else result.get("error")
                )
            except Exception as e:
                self.report_result("debugging", "trace_execution", False, str(e))
            
            # Test 2: analyze_error_logs
            try:
                raw_result = await client.call_tool(
                    "terminal",
                    "analyze_error_logs",
                    {"log_path": log_file}
                )
                
                result = extract_result(raw_result)
                success = result.get("success", False)
                error_count = result.get("result", {}).get("total_errors", 0) if success else 0
                
                self.report_result(
                    "debugging",
                    "analyze_error_logs",
                    success and error_count > 0,
                    f"Found {error_count} errors" if success else result.get("error")
                )
            except Exception as e:
                self.report_result("debugging", "analyze_error_logs", False, str(e))
            
            # Test 3: compare_outputs
            try:
                raw_result = await client.call_tool(
                    "terminal",
                    "compare_outputs",
                    {"file1": compare_file1, "file2": compare_file2}
                )
                
                result = extract_result(raw_result)
                success = result.get("success", False)
                self.report_result(
                    "debugging",
                    "compare_outputs",
                    success,
                    "Files compared successfully" if success else result.get("error")
                )
            except Exception as e:
                self.report_result("debugging", "compare_outputs", False, str(e))
        
        finally:
            # Cleanup
            for f in [test_file, log_file, compare_file1, compare_file2]:
                if os.path.exists(f):
                    os.remove(f)
    
    async def test_testing_tools(self, client):
        """Test testing tools"""
        print("\n" + "=" * 60)
        print("TESTING: Testing Tools")
        print("=" * 60)
        
        # Create test file
        test_file = "sample_module.py"
        test_code = '''
def add(a, b):
    """Add two numbers"""
    return a + b

def multiply(a, b):
    """Multiply two numbers"""
    return a * b

class StringHelper:
    def uppercase(self, text):
        return text.upper()
    
    def lowercase(self, text):
        return text.lower()
'''
        
        with open(test_file, 'w') as f:
            f.write(test_code)
        
        try:
            # Test 1: generate_unit_tests
            try:
                raw_result = await client.call_tool(
                    "terminal",
                    "generate_unit_tests",
                    {"file_path": test_file}
                )
                
                result = extract_result(raw_result)
                success = result.get("success", False)
                test_file_created = os.path.exists(result.get("result", {}).get("test_file", "")) if success else False
                
                self.report_result(
                    "testing",
                    "generate_unit_tests",
                    success and test_file_created,
                    f"Generated {result.get('result', {}).get('functions_found', 0)} test stubs" if success else result.get("error")
                )
                
                # Cleanup generated test
                if test_file_created:
                    os.remove(result["result"]["test_file"])
            
            except Exception as e:
                self.report_result("testing", "generate_unit_tests", False, str(e))
            
            # Test 2: run_tests_with_coverage
            try:
                raw_result = await client.call_tool(
                    "terminal",
                    "run_tests_with_coverage",
                    {"test_path": "."}
                )
                
                result = extract_result(raw_result)
                success = result.get("success", False)
                self.report_result(
                    "testing",
                    "run_tests_with_coverage",
                    success,
                    "Tests executed" if success else result.get("error")
                )
            except Exception as e:
                self.report_result("testing", "run_tests_with_coverage", False, str(e))
            
            # Test 3: detect_test_gaps
            try:
                raw_result = await client.call_tool(
                    "terminal",
                    "detect_test_gaps",
                    {"module_path": test_file}
                )
                
                result = extract_result(raw_result)
                success = result.get("success", False)
                self.report_result(
                    "testing",
                    "detect_test_gaps",
                    success,
                    f"Coverage: {result.get('result', {}).get('coverage_percent', 0)}%" if success else result.get("error")
                )
            except Exception as e:
                self.report_result("testing", "detect_test_gaps", False, str(e))
        
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.remove(test_file)
    
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
            print("\n🎉 ALL TESTS PASSED! Phase 2 implementation successful!")
        elif self.passed_tests >= self.total_tests * 0.75:
            print("\n✅ Most tests passed. Review failed tests above.")
        else:
            print("\n⚠️  Many tests failed. Check installation and dependencies.")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("PHASE 2 TOOLS TEST SUITE")
    print("=" * 60)
    print("\nThis will test all 12 new advanced tools.")
    print("Make sure you have installed dependencies:")
    print("  pip install pylint flake8 mypy bandit pytest pytest-cov --break-system-packages")
    print("\nStarting tests...\n")
    
    tester = Phase2Tester()
    
    async with MCPAppClient() as client:
        print(f"✓ Connected to MCP server")
        print(f"  Tools available: {len(client._tools)}")
        
        # Run all test categories
        await tester.test_code_analysis(client)
        await tester.test_project_operations(client)
        await tester.test_debugging_tools(client)
        await tester.test_testing_tools(client)
        
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