"""
Phase 4 Resources Test Suite
Tests all 7 new advanced resources
"""

import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from c.client import MCPAppClient


def extract_result(raw_result):
    """Extract actual result from resource response"""
    if isinstance(raw_result, list) and len(raw_result) > 0:
        first_item = raw_result[0]
        
        if hasattr(first_item, 'contents'):
            return first_item.contents
        
        if hasattr(first_item, 'text'):
            try:
                return json.loads(first_item.text)
            except:
                return first_item.text
        
        if isinstance(first_item, dict):
            return first_item
    
    if isinstance(raw_result, dict):
        return raw_result
    
    return {"error": f"Cannot extract result from {type(raw_result)}"}


class Phase4Tester:
    """Test suite for Phase 4 advanced resources"""
    
    def __init__(self):
        self.results = {
            "project_intelligence": {},
            "real_time_monitoring": {}
        }
        self.total_tests = 0
        self.passed_tests = 0
    
    def report_result(self, category: str, resource: str, success: bool, message: str = ""):
        """Record test result"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        self.results[category][resource] = {
            "success": success,
            "message": message
        }
        
        print(f"{status} | {resource}")
        if message:
            print(f"         {message}")
    
    async def test_project_intelligence(self, client):
        """Test project intelligence resources"""
        print("\n" + "=" * 60)
        print("TESTING: Project Intelligence Resources")
        print("=" * 60)
        
        # Test 1: project://complexity
        try:
            raw_result = await client.read_resource(
                "terminal",
                "project://complexity"
            )
            
            result = extract_result(raw_result)
            
            if isinstance(result, dict) and "summary" in result:
                summary = result["summary"]
                avg_complexity = summary.get("avg_complexity", 0)
                self.report_result(
                    "project_intelligence",
                    "project://complexity",
                    True,
                    f"Avg complexity: {avg_complexity}, Tech debt: {summary.get('tech_debt_score', 0)}"
                )
            else:
                self.report_result(
                    "project_intelligence",
                    "project://complexity",
                    False,
                    result.get("error", "Invalid response format")
                )
        except Exception as e:
            self.report_result("project_intelligence", "project://complexity", False, str(e))
        
        # Test 2: project://dependencies
        try:
            raw_result = await client.read_resource(
                "terminal",
                "project://dependencies"
            )
            
            result = extract_result(raw_result)
            
            if isinstance(result, dict) and "summary" in result:
                summary = result["summary"]
                total_files = summary.get("total_files", 0)
                external = summary.get("external_packages", 0)
                self.report_result(
                    "project_intelligence",
                    "project://dependencies",
                    True,
                    f"{total_files} files, {external} external packages"
                )
            else:
                self.report_result(
                    "project_intelligence",
                    "project://dependencies",
                    False,
                    result.get("error", "Invalid response format")
                )
        except Exception as e:
            self.report_result("project_intelligence", "project://dependencies", False, str(e))
        
        # Test 3: project://test-coverage
        try:
            raw_result = await client.read_resource(
                "terminal",
                "project://test-coverage"
            )
            
            result = extract_result(raw_result)
            
            if isinstance(result, dict):
                if result.get("coverage_exists"):
                    summary = result.get("summary", {})
                    coverage = summary.get("coverage_percent", 0)
                    self.report_result(
                        "project_intelligence",
                        "project://test-coverage",
                        True,
                        f"Coverage: {coverage}%"
                    )
                else:
                    # No coverage file is OK - tool works
                    self.report_result(
                        "project_intelligence",
                        "project://test-coverage",
                        True,
                        "Tool works (no .coverage file - run pytest --cov to generate)"
                    )
            else:
                self.report_result(
                    "project_intelligence",
                    "project://test-coverage",
                    False,
                    "Invalid response format"
                )
        except Exception as e:
            self.report_result("project_intelligence", "project://test-coverage", False, str(e))
    
    async def test_real_time_monitoring(self, client):
        """Test real-time monitoring resources"""
        print("\n" + "=" * 60)
        print("TESTING: Real-Time Monitoring Resources")
        print("=" * 60)
        
        # Test 1: monitor://cpu
        try:
            raw_result = await client.read_resource(
                "terminal",
                "monitor://cpu"
            )
            
            result = extract_result(raw_result)
            
            if isinstance(result, dict) and "system" in result:
                cpu_percent = result["system"].get("cpu_percent", 0)
                cpu_count = result["system"].get("cpu_count", 0)
                self.report_result(
                    "real_time_monitoring",
                    "monitor://cpu",
                    True,
                    f"CPU: {cpu_percent}% ({cpu_count} cores)"
                )
            else:
                self.report_result(
                    "real_time_monitoring",
                    "monitor://cpu",
                    False,
                    result.get("error", "Invalid response format")
                )
        except Exception as e:
            self.report_result("real_time_monitoring", "monitor://cpu", False, str(e))
        
        # Test 2: monitor://memory
        try:
            raw_result = await client.read_resource(
                "terminal",
                "monitor://memory"
            )
            
            result = extract_result(raw_result)
            
            if isinstance(result, dict) and "system" in result:
                mem_percent = result["system"].get("percent", 0)
                mem_used = result["system"].get("used_gb", 0)
                self.report_result(
                    "real_time_monitoring",
                    "monitor://memory",
                    True,
                    f"Memory: {mem_percent}% ({mem_used:.1f}GB used)"
                )
            else:
                self.report_result(
                    "real_time_monitoring",
                    "monitor://memory",
                    False,
                    result.get("error", "Invalid response format")
                )
        except Exception as e:
            self.report_result("real_time_monitoring", "monitor://memory", False, str(e))
        
        # Test 3: monitor://file-changes
        try:
            raw_result = await client.read_resource(
                "terminal",
                "monitor://file-changes"
            )
            
            result = extract_result(raw_result)
            
            if isinstance(result, dict) and "summary" in result:
                total_changes = result["summary"].get("total_changes", 0)
                self.report_result(
                    "real_time_monitoring",
                    "monitor://file-changes",
                    True,
                    f"{total_changes} files changed in last minute"
                )
            else:
                self.report_result(
                    "real_time_monitoring",
                    "monitor://file-changes",
                    False,
                    result.get("error", "Invalid response format")
                )
        except Exception as e:
            self.report_result("real_time_monitoring", "monitor://file-changes", False, str(e))
        
        # Test 4: monitor://disk
        try:
            raw_result = await client.read_resource(
                "terminal",
                "monitor://disk"
            )
            
            result = extract_result(raw_result)
            
            if isinstance(result, dict) and "workspace" in result:
                workspace_percent = result["workspace"].get("percent", 0)
                workspace_free = result["workspace"].get("free_gb", 0)
                self.report_result(
                    "real_time_monitoring",
                    "monitor://disk",
                    True,
                    f"Disk: {workspace_percent}% used ({workspace_free:.1f}GB free)"
                )
            else:
                self.report_result(
                    "real_time_monitoring",
                    "monitor://disk",
                    False,
                    result.get("error", "Invalid response format")
                )
        except Exception as e:
            self.report_result("real_time_monitoring", "monitor://disk", False, str(e))
    
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
            
            for resource, result in tests.items():
                status = "✅" if result["success"] else "❌"
                print(f"    {status} {resource}")
        
        print("\n" + "=" * 60)
        print(f"OVERALL: {self.passed_tests}/{self.total_tests} tests passed")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%")
        print("=" * 60)
        
        if self.passed_tests == self.total_tests:
            print("\n🎉 ALL TESTS PASSED! Phase 4 implementation successful!")
        elif self.passed_tests >= self.total_tests * 0.75:
            print("\n✅ Most tests passed. Review failed tests above.")
        else:
            print("\n⚠️  Many tests failed. Check installation and dependencies.")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("PHASE 4 RESOURCES TEST SUITE")
    print("=" * 60)
    print("\nThis will test all 7 new advanced resources.")
    print("Dependencies needed:")
    print("  pip install psutil --break-system-packages")
    print("  pip install coverage --break-system-packages (optional)")
    print("\nStarting tests...\n")
    
    tester = Phase4Tester()
    
    async with MCPAppClient() as client:
        print(f"✓ Connected to MCP server")
        print(f"  Resources available: {len(client._resources)}")
        
        # Run all test categories
        await tester.test_project_intelligence(client)
        await tester.test_real_time_monitoring(client)
        
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