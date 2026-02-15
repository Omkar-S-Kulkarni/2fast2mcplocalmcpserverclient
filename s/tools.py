from __future__ import annotations
import shutil
import os
import socket
import platform
import json
import ast
import subprocess
import sys
from typing import Dict, Any, List, Set, Tuple, Optional
from pathlib import Path
import re
from collections import defaultdict,OrderedDict
import tempfile
from mcp_instance import mcp
from datetime import datetime
import time 
from state import get_server_state
import cProfile
import pstats
import io
import hashlib
from datetime import timedelta
from pstats import SortKey
from helper import (
    execute_command,
    resolve_workspace_path,
    validate_workspace_path,
    truncate_output,
    kill_process as kill_registered_process,
)


def _run_tool(name, logic):
    """Wrapper for consistent tool execution and error handling"""
    try:
        result = logic()
        return {
            "success": True,
            "tool": name,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "tool": name,
            "error": str(e)
        }


# ============================================================
# EXISTING TERMINAL TOOLS (keeping all original functionality)
# ============================================================

@mcp.tool
def run_command(command: str, cwd: str = ".") -> Dict[str, Any]:
    def logic():
        return execute_command(command, cwd=cwd)
    return _run_tool("run_command", logic)


@mcp.tool
def interactive_command(command: str, cwd: str = ".") -> Dict[str, Any]:
    def logic():
        cwd_path = resolve_workspace_path(cwd)

        if not validate_workspace_path(cwd_path):
            return {"success": False, "error": "Invalid working directory"}

        try:
            os.popen(command)
            return {
                "success": True,
                "message": "Command started interactively"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    return _run_tool("interactive_command", logic)


@mcp.tool
def read_file(path: str) -> Dict[str, Any]:
    def logic():
        file_path = resolve_workspace_path(path)

        if not validate_workspace_path(file_path):
            return {"success": False, "error": "Invalid path"}

        if not os.path.exists(file_path):
            return {"success": False, "error": "File not found"}

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        return {
            "success": True,
            "content": truncate_output(content)
        }

    return _run_tool("read_file", logic)


def normalize_tool_path(path: str) -> str:
    """
    Normalize paths coming from the LLM.
    Fixes:
    - session://cwd/a.py  -> a.py
    - Windows double slashes
    """
    if not path:
        return path

    # Remove session prefix
    if path.startswith("session://cwd/"):
        path = path.replace("session://cwd/", "")

    # Fix Windows slashes
    path = path.replace("\\\\", "\\")

    # Remove leading slash if relative
    path = path.lstrip("/")

    return path


@mcp.tool
def write_file(path: str, content: str) -> Dict[str, Any]:
    def logic():
        normalized_path = normalize_tool_path(path)
        file_path = resolve_workspace_path(normalized_path)

        if not validate_workspace_path(file_path):
            return {"success": False, "error": "Invalid path"}

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {"success": True}

    return _run_tool("write_file", logic)


@mcp.tool
def list_directory(path: str = ".") -> Dict[str, Any]:
    def logic():
        dir_path = resolve_workspace_path(path)

        if not validate_workspace_path(dir_path):
            return {"success": False, "error": "Invalid path"}

        items = []
        for name in os.listdir(dir_path):
            full = os.path.join(dir_path, name)
            items.append({
                "name": name,
                "type": "dir" if os.path.isdir(full) else "file",
                "size": os.path.getsize(full) if os.path.isfile(full) else None
            })

        return {"success": True, "items": items}

    return _run_tool("list_directory", logic)


@mcp.tool
def search_files(keyword: str, path: str = ".") -> Dict[str, Any]:
    def logic():
        root = resolve_workspace_path(path)

        if not validate_workspace_path(root):
            return {"success": False, "error": "Invalid path"}

        matches = []
        for dirpath, _, filenames in os.walk(root):
            for file in filenames:
                if keyword.lower() in file.lower():
                    matches.append(os.path.join(dirpath, file))

        return {"success": True, "matches": matches}

    return _run_tool("search_files", logic)


@mcp.tool
def replace_in_file(path: str, search: str, replace: str) -> Dict[str, Any]:
    def logic():
        file_path = resolve_workspace_path(path)

        if not validate_workspace_path(file_path):
            return {"success": False, "error": "Invalid path"}

        if not os.path.exists(file_path):
            return {"success": False, "error": "File not found"}

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = content.replace(search, replace)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {"success": True}

    return _run_tool("replace_in_file", logic)


@mcp.tool
def list_processes() -> Dict[str, Any]:
    def logic():
        state = get_server_state()
        return {
            "success": True,
            "processes": state.running_processes
        }

    return _run_tool("list_processes", logic)


@mcp.tool
def kill_process(process_id: str) -> Dict[str, Any]:
    def logic():
        success = kill_registered_process(process_id)
        return {"success": success}

    return _run_tool("kill_process", logic)


@mcp.tool
def get_env(key: str = None) -> Dict[str, Any]:
    def logic():
        if key:
            return {"success": True, "value": os.environ.get(key)}
        return {"success": True, "env": dict(os.environ)}

    return _run_tool("get_env", logic)


@mcp.tool
def system_info() -> Dict[str, Any]:
    def logic():
        return {
            "success": True,
            "system": platform.system(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "cwd": os.getcwd(),
        }

    return _run_tool("system_info", logic)


@mcp.tool
def git_status() -> Dict[str, Any]:
    def logic():
        return execute_command("git status")
    return _run_tool("git_status", logic)


@mcp.tool
def git_diff() -> Dict[str, Any]:
    def logic():
        return execute_command("git diff")
    return _run_tool("git_diff", logic)


@mcp.tool
def git_commit(message: str) -> Dict[str, Any]:
    def logic():
        execute_command("git add .")
        return execute_command(["git", "commit", "-m", message])

    return _run_tool("git_commit", logic)


@mcp.tool
def tail_file(path: str, lines: int = 50) -> Dict[str, Any]:
    def logic():
        file_path = resolve_workspace_path(path)

        if not validate_workspace_path(file_path):
            return {"success": False, "error": "Invalid path"}

        if not os.path.exists(file_path):
            return {"success": False, "error": "File not found"}

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.readlines()

        return {
            "success": True,
            "content": "".join(content[-lines:])
        }

    return _run_tool("tail_file", logic)


@mcp.tool
def check_port(port: int, host: str = "localhost") -> Dict[str, Any]:
    def logic():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)

        try:
            result = sock.connect_ex((host, port))
            return {"success": True, "open": result == 0}
        finally:
            sock.close()

    return _run_tool("check_port", logic)


@mcp.tool
def docker_ps() -> Dict[str, Any]:
    def logic():
        return execute_command("docker ps")

    return _run_tool("docker_ps", logic)


@mcp.tool
def create_report_from_results(title: str, results_summary: str, output_path: str = "report.txt") -> Dict[str, Any]:
    """Create a formatted report from task execution results"""
    def logic():
        from datetime import datetime
        
        file_path = resolve_workspace_path(output_path)
        
        if not validate_workspace_path(file_path):
            return {"success": False, "error": "Invalid path"}
        
        report_lines = [
            "=" * 60,
            f"REPORT: {title}",
            "=" * 60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "=" * 60,
            "RESULTS",
            "=" * 60,
            results_summary,
            "",
            "=" * 60,
            "END OF REPORT",
            "=" * 60
        ]
        
        content = "\n".join(report_lines)
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return {
            "success": True,
            "path": file_path,
            "size": len(content)
        }
    
    return _run_tool("create_report_from_results", logic)


# ============================================================
# PHASE 2.1: CODE ANALYSIS TOOLS
# ============================================================

@mcp.tool
def analyze_code_quality(path: str) -> Dict[str, Any]:
    """
    Run multiple code quality checks on Python code:
    - pylint: comprehensive code analysis
    - flake8: style guide enforcement
    - mypy: static type checking
    """
    def logic():
        file_path = resolve_workspace_path(path)
        
        if not validate_workspace_path(file_path):
            return {"error": "Invalid path"}
        
        if not os.path.exists(file_path):
            return {"error": "File not found"}
        
        results = {
            "file": file_path,
            "pylint": None,
            "flake8": None,
            "mypy": None,
            "summary": {}
        }
        
        # Run pylint
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pylint", file_path, "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.stdout:
                pylint_data = json.loads(result.stdout)
                results["pylint"] = {
                    "score": None,
                    "issues": pylint_data
                }
                # Extract score from messages
                for msg in pylint_data:
                    if "score" in str(msg).lower():
                        results["summary"]["pylint_issues"] = len(pylint_data)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            results["pylint"] = {"error": "pylint not available or timeout"}
        
        # Run flake8
        try:
            result = subprocess.run(
                [sys.executable, "-m", "flake8", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            issues = result.stdout.strip().split('\n') if result.stdout else []
            results["flake8"] = {
                "issues": [i for i in issues if i],
                "count": len([i for i in issues if i])
            }
            results["summary"]["flake8_issues"] = len([i for i in issues if i])
        except (subprocess.TimeoutExpired, FileNotFoundError):
            results["flake8"] = {"error": "flake8 not available or timeout"}
        
        # Run mypy
        try:
            result = subprocess.run(
                [sys.executable, "-m", "mypy", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            results["mypy"] = {
                "output": result.stdout,
                "errors": result.stderr,
                "return_code": result.returncode
            }
            # Count issues
            issue_count = len([line for line in result.stdout.split('\n') if 'error:' in line])
            results["summary"]["mypy_issues"] = issue_count
        except (subprocess.TimeoutExpired, FileNotFoundError):
            results["mypy"] = {"error": "mypy not available or timeout"}
        
        return results
    
    return _run_tool("analyze_code_quality", logic)


@mcp.tool
def detect_security_issues(path: str) -> Dict[str, Any]:
    """
    Run bandit security scanner on Python code
    Detects common security vulnerabilities
    """
    def logic():
        file_path = resolve_workspace_path(path)
        
        if not validate_workspace_path(file_path):
            return {"error": "Invalid path"}
        
        if not os.path.exists(file_path):
            return {"error": "File not found"}
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "bandit", "-f", "json", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                bandit_data = json.loads(result.stdout)
                
                return {
                    "file": file_path,
                    "results": bandit_data.get("results", []),
                    "summary": {
                        "total_issues": len(bandit_data.get("results", [])),
                        "high_severity": len([r for r in bandit_data.get("results", []) if r.get("issue_severity") == "HIGH"]),
                        "medium_severity": len([r for r in bandit_data.get("results", []) if r.get("issue_severity") == "MEDIUM"]),
                        "low_severity": len([r for r in bandit_data.get("results", []) if r.get("issue_severity") == "LOW"])
                    },
                    "metrics": bandit_data.get("metrics", {})
                }
            else:
                return {"error": "No output from bandit", "stderr": result.stderr}
                
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            return {"error": f"bandit not available or error: {str(e)}"}
    
    return _run_tool("detect_security_issues", logic)


@mcp.tool
def profile_code_performance(file_path: str, function_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Run cProfile on Python code and analyze performance bottlenecks
    """
    def logic():
        resolved_path = resolve_workspace_path(file_path)
        
        if not validate_workspace_path(resolved_path):
            return {"error": "Invalid path"}
        
        if not os.path.exists(resolved_path):
            return {"error": "File not found"}
        

        
        pr = cProfile.Profile()
        
        # Read and execute the file
        with open(resolved_path, 'r') as f:
            code = f.read()
        
        try:
            # Profile the execution
            pr.enable()
            exec(compile(code, resolved_path, 'exec'), {'__name__': '__main__'})
            pr.disable()
            
            # Capture stats
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s)
            ps.sort_stats(SortKey.CUMULATIVE)
            ps.print_stats(20)  # Top 20 functions
            
            stats_output = s.getvalue()
            
            # Parse stats for structured data
            lines = stats_output.split('\n')
            bottlenecks = []
            
            for line in lines[5:25]:  # Skip header, get top 20
                if line.strip() and not line.startswith('---'):
                    bottlenecks.append(line.strip())
            
            return {
                "file": resolved_path,
                "profile_output": stats_output,
                "top_bottlenecks": bottlenecks,
                "total_calls": pr.total_calls
            }
            
        except Exception as e:
            return {"error": f"Profiling failed: {str(e)}"}
    
    return _run_tool("profile_code_performance", logic)


# ============================================================
# PHASE 2.2: PROJECT-LEVEL OPERATIONS
# ============================================================

@mcp.tool
def analyze_project_structure() -> Dict[str, Any]:
    """
    Map entire project structure:
    - File organization
    - Python modules
    - Entry points
    - Dependencies
    """
    def logic():
        workspace = get_server_state().workspace_root or os.getcwd()
        
        structure = {
            "root": workspace,
            "python_files": [],
            "directories": [],
            "entry_points": [],
            "config_files": [],
            "requirements": [],
            "total_lines": 0
        }
        
        for root, dirs, files in os.walk(workspace):
            # Skip common non-code directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
            
            rel_root = os.path.relpath(root, workspace)
            if rel_root != '.':
                structure["directories"].append(rel_root)
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, workspace)
                
                # Python files
                if file.endswith('.py'):
                    structure["python_files"].append(rel_path)
                    
                    # Check for entry points
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            structure["total_lines"] += len(content.split('\n'))
                            
                            if 'if __name__ == "__main__"' in content:
                                structure["entry_points"].append(rel_path)
                    except Exception:
                        pass
                
                # Config files
                elif file in {'setup.py', 'pyproject.toml', 'requirements.txt', 'Pipfile', 'poetry.lock', 'package.json'}:
                    structure["config_files"].append(rel_path)
                    
                    # Parse requirements
                    if file == 'requirements.txt':
                        try:
                            with open(file_path, 'r') as f:
                                structure["requirements"] = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                        except Exception:
                            pass
        
        structure["python_file_count"] = len(structure["python_files"])
        structure["directory_count"] = len(structure["directories"])
        
        return structure
    
    return _run_tool("analyze_project_structure", logic)


@mcp.tool
def detect_circular_dependencies() -> Dict[str, Any]:
    """
    Detect circular import dependencies in Python project
    """
    def logic():
        workspace = get_server_state().workspace_root or os.getcwd()
        
        # Build import graph
        import_graph: Dict[str, Set[str]] = {}
        module_files: Dict[str, str] = {}
        
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv'}]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, workspace)
                
                # Convert path to module name
                module_name = rel_path.replace(os.sep, '.').replace('.py', '')
                module_files[module_name] = rel_path
                
                # Parse imports
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        tree = ast.parse(f.read())
                    
                    imports = set()
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.add(alias.name.split('.')[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.add(node.module.split('.')[0])
                    
                    import_graph[module_name] = imports
                    
                except Exception:
                    continue
        
        # Detect cycles using DFS
        def find_cycles(module: str, path: List[str], visited: Set[str]) -> List[List[str]]:
            if module in path:
                cycle_start = path.index(module)
                return [path[cycle_start:] + [module]]
            
            if module in visited:
                return []
            
            visited.add(module)
            cycles = []
            
            for imported in import_graph.get(module, set()):
                if imported in import_graph:
                    cycles.extend(find_cycles(imported, path + [module], visited.copy()))
            
            return cycles
        
        all_cycles = []
        for module in import_graph:
            cycles = find_cycles(module, [], set())
            for cycle in cycles:
                if cycle not in all_cycles:
                    all_cycles.append(cycle)
        
        return {
            "circular_dependencies": all_cycles,
            "count": len(all_cycles),
            "modules_analyzed": len(import_graph),
            "import_graph": {k: list(v) for k, v in import_graph.items()}
        }
    
    return _run_tool("detect_circular_dependencies", logic)


@mcp.tool
def generate_dependency_graph() -> Dict[str, Any]:
    """
    Create visual dependency graph in DOT format (Graphviz)
    """
    def logic():
        workspace = get_server_state().workspace_root or os.getcwd()
        
        # Build import graph
        import_graph: Dict[str, Set[str]] = {}
        
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv'}]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, workspace)
                module_name = rel_path.replace(os.sep, '.').replace('.py', '')
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        tree = ast.parse(f.read())
                    
                    imports = set()
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.add(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.add(node.module)
                    
                    import_graph[module_name] = imports
                    
                except Exception:
                    continue
        
        # Generate DOT format
        dot_lines = ['digraph Dependencies {', '  rankdir=LR;', '  node [shape=box];', '']
        
        for module, imports in import_graph.items():
            clean_module = module.replace('.', '_')
            
            for imported in imports:
                clean_imported = imported.replace('.', '_')
                dot_lines.append(f'  "{clean_module}" -> "{clean_imported}";')
        
        dot_lines.append('}')
        
        dot_content = '\n'.join(dot_lines)
        
        # Save to file
        output_path = os.path.join(workspace, 'dependency_graph.dot')
        with open(output_path, 'w') as f:
            f.write(dot_content)
        
        return {
            "dot_content": dot_content,
            "output_file": output_path,
            "nodes": len(import_graph),
            "edges": sum(len(imports) for imports in import_graph.values()),
            "note": "Use 'dot -Tpng dependency_graph.dot -o graph.png' to generate image"
        }
    
    return _run_tool("generate_dependency_graph", logic)


# ============================================================
# PHASE 2.3: DEBUGGING TOOLS
# ============================================================

@mcp.tool
def trace_execution(file_path: str, breakpoints: List[int] = None) -> Dict[str, Any]:
    """
    Run code with pdb breakpoints and capture execution state
    NOTE: This is a simplified version - full interactive debugging requires a different approach
    """
    def logic():
        resolved_path = resolve_workspace_path(file_path)
        
        if not validate_workspace_path(resolved_path):
            return {"error": "Invalid path"}
        
        if not os.path.exists(resolved_path):
            return {"error": "File not found"}
        
        # For now, run with trace module to capture execution
        import trace
        import sys
        import io
        
        tracer = trace.Trace(count=True, trace=True)
        
        # Redirect stdout
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            with open(resolved_path, 'r') as f:
                code = f.read()
            
            tracer.run(compile(code, resolved_path, 'exec'))
            
            output = sys.stdout.getvalue()
            
            results = tracer.results()
            coverage = results.counts
            
            return {
                "file": resolved_path,
                "trace_output": output[:5000],  # Limit output
                "lines_executed": len(coverage),
                "coverage_data": {str(k): v for k, v in list(coverage.items())[:50]}
            }
            
        except Exception as e:
            return {"error": f"Execution trace failed: {str(e)}"}
        finally:
            sys.stdout = old_stdout
    
    return _run_tool("trace_execution", logic)


@mcp.tool
def analyze_error_logs(log_path: str, error_keywords: List[str] = None) -> Dict[str, Any]:
    """
    Parse log files, extract errors, and suggest fixes
    """
    def logic():
        keywords = error_keywords if error_keywords is not None else ["error", "exception", "traceback", "failed", "critical"]
        
        file_path = resolve_workspace_path(log_path)
        
        if not validate_workspace_path(file_path):
            return {"error": "Invalid path"}
        
        if not os.path.exists(file_path):
            return {"error": "File not found"}
        
        errors = []
        error_types = {}
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            for keyword in keywords:
                if keyword in line_lower:
                    # Extract error context (line before and after)
                    context_start = max(0, i - 1)
                    context_end = min(len(lines), i + 2)
                    context = ''.join(lines[context_start:context_end])
                    
                    error_entry = {
                        "line_number": i + 1,
                        "keyword": keyword,
                        "content": line.strip(),
                        "context": context
                    }
                    
                    errors.append(error_entry)
                    
                    # Count error types
                    error_types[keyword] = error_types.get(keyword, 0) + 1
                    
                    break
        
        # Generate suggestions based on common patterns
        suggestions = []
        for error in errors[:10]:  # Analyze top 10
            content = error["content"].lower()
            
            if "filenotfound" in content or "no such file" in content:
                suggestions.append("File path issue - check file existence and permissions")
            elif "connection" in content or "timeout" in content:
                suggestions.append("Network connectivity issue - verify URLs and network access")
            elif "import" in content or "module" in content:
                suggestions.append("Missing dependency - check requirements.txt and installed packages")
            elif "null" in content or "none" in content:
                suggestions.append("Null/None reference - add null checks before accessing objects")
            elif "index" in content or "key" in content:
                suggestions.append("Index/Key error - validate array/dict access with proper bounds checking")
        
        return {
            "file": file_path,
            "total_errors": len(errors),
            "error_types": error_types,
            "errors": errors[:50],  # Return top 50
            "suggestions": list(set(suggestions))
        }
    
    return _run_tool("analyze_error_logs", logic)


@mcp.tool
def compare_outputs(file1: str, file2: str) -> Dict[str, Any]:
    """
    Compare two files for regression testing and diff analysis
    """
    def logic():
        import difflib
        
        path1 = resolve_workspace_path(file1)
        path2 = resolve_workspace_path(file2)
        
        if not validate_workspace_path(path1) or not validate_workspace_path(path2):
            return {"error": "Invalid path"}
        
        if not os.path.exists(path1):
            return {"error": f"File not found: {file1}"}
        
        if not os.path.exists(path2):
            return {"error": f"File not found: {file2}"}
        
        with open(path1, 'r', encoding='utf-8', errors='ignore') as f:
            content1 = f.readlines()
        
        with open(path2, 'r', encoding='utf-8', errors='ignore') as f:
            content2 = f.readlines()
        
        # Generate unified diff
        diff = difflib.unified_diff(
            content1,
            content2,
            fromfile=file1,
            tofile=file2,
            lineterm=''
        )
        
        diff_lines = list(diff)
        
        # Count changes
        additions = len([line for line in diff_lines if line.startswith('+')])
        deletions = len([line for line in diff_lines if line.startswith('-')])
        
        # Calculate similarity
        matcher = difflib.SequenceMatcher(None, ''.join(content1), ''.join(content2))
        similarity = matcher.ratio()
        
        return {
            "file1": file1,
            "file2": file2,
            "identical": content1 == content2,
            "similarity_ratio": round(similarity, 3),
            "additions": additions,
            "deletions": deletions,
            "diff": ''.join(diff_lines[:1000])  # Limit diff output
        }
    
    return _run_tool("compare_outputs", logic)


# ============================================================
# PHASE 2.4: TESTING TOOLS
# ============================================================

@mcp.tool
def generate_unit_tests(file_path: str) -> Dict[str, Any]:
    """
    Auto-generate pytest test stubs for functions in a Python file
    """
    def logic():
        resolved_path = resolve_workspace_path(file_path)
        
        if not validate_workspace_path(resolved_path):
            return {"error": "Invalid path"}
        
        if not os.path.exists(resolved_path):
            return {"error": "File not found"}
        
        with open(resolved_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private functions and methods
                if not node.name.startswith('_'):
                    functions.append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "line": node.lineno
                    })
            elif isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "methods": [m.name for m in node.body if isinstance(m, ast.FunctionDef) and not m.name.startswith('_')]
                })
        
        # Generate test file
        test_lines = [
            "import pytest",
            f"from {Path(file_path).stem} import *",
            "",
            ""
        ]
        
        # Generate test functions
        for func in functions:
            test_lines.append(f"def test_{func['name']}():")
            test_lines.append(f"    # TODO: Test {func['name']}")
            
            if func['args']:
                test_lines.append(f"    # Arguments: {', '.join(func['args'])}")
            
            test_lines.append("    pass")
            test_lines.append("")
        
        # Generate test classes
        for cls in classes:
            test_lines.append(f"class Test{cls['name']}:")
            test_lines.append("")
            
            for method in cls['methods']:
                test_lines.append(f"    def test_{method}(self):")
                test_lines.append(f"        # TODO: Test {cls['name']}.{method}")
                test_lines.append("        pass")
                test_lines.append("")
        
        test_content = '\n'.join(test_lines)
        
        # Save test file
        test_file_path = resolved_path.replace('.py', '_test.py')
        
        with open(test_file_path, 'w') as f:
            f.write(test_content)
        
        return {
            "source_file": file_path,
            "test_file": test_file_path,
            "functions_found": len(functions),
            "classes_found": len(classes),
            "test_content": test_content
        }
    
    return _run_tool("generate_unit_tests", logic)


@mcp.tool
def run_tests_with_coverage(test_path: str = ".") -> Dict[str, Any]:
    """
    Run pytest with coverage report
    """
    def logic():
        resolved_path = resolve_workspace_path(test_path)
        
        if not validate_workspace_path(resolved_path):
            return {"error": "Invalid path"}
        
        try:
            # Run pytest with coverage
            result = subprocess.run(
                [sys.executable, "-m", "pytest", resolved_path, "--cov", "--cov-report=json", "-v"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            output = {
                "test_path": test_path,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "coverage": None
            }
            
            # Try to load coverage report
            coverage_file = os.path.join(os.getcwd(), 'coverage.json')
            if os.path.exists(coverage_file):
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                
                output["coverage"] = {
                    "total_statements": coverage_data.get("totals", {}).get("num_statements", 0),
                    "covered_statements": coverage_data.get("totals", {}).get("covered_lines", 0),
                    "percent_covered": coverage_data.get("totals", {}).get("percent_covered", 0),
                    "missing_lines": coverage_data.get("totals", {}).get("missing_lines", 0)
                }
            
            return output
            
        except subprocess.TimeoutExpired:
            return {"error": "Test execution timed out"}
        except FileNotFoundError:
            return {"error": "pytest not installed"}
    
    return _run_tool("run_tests_with_coverage", logic)


@mcp.tool
def detect_test_gaps(module_path: str) -> Dict[str, Any]:
    """
    Find untested functions and classes in a module
    """
    def logic():
        resolved_path = resolve_workspace_path(module_path)
        
        if not validate_workspace_path(resolved_path):
            return {"error": "Invalid path"}
        
        if not os.path.exists(resolved_path):
            return {"error": "File not found"}
        
        # Parse source file
        with open(resolved_path, 'r', encoding='utf-8') as f:
            source_tree = ast.parse(f.read())
        
        source_functions = set()
        source_classes = {}
        
        for node in ast.walk(source_tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                source_functions.add(node.name)
            elif isinstance(node, ast.ClassDef):
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef) and not m.name.startswith('_')]
                source_classes[node.name] = set(methods)
        
        # Find test file
        test_file = resolved_path.replace('.py', '_test.py')
        if not os.path.exists(test_file):
            # Try alternate naming
            dir_name = os.path.dirname(resolved_path)
            base_name = os.path.basename(resolved_path).replace('.py', '')
            test_file = os.path.join(dir_name, f"test_{base_name}.py")
        
        tested_functions = set()
        tested_classes = {}
        
        if os.path.exists(test_file):
            with open(test_file, 'r', encoding='utf-8') as f:
                test_tree = ast.parse(f.read())
            
            for node in ast.walk(test_tree):
                if isinstance(node, ast.FunctionDef):
                    # Extract tested function name from test_xxx pattern
                    if node.name.startswith('test_'):
                        tested_name = node.name.replace('test_', '', 1)
                        tested_functions.add(tested_name)
                elif isinstance(node, ast.ClassDef):
                    if node.name.startswith('Test'):
                        class_name = node.name.replace('Test', '', 1)
                        methods = set()
                        for m in node.body:
                            if isinstance(m, ast.FunctionDef) and m.name.startswith('test_'):
                                methods.add(m.name.replace('test_', '', 1))
                        tested_classes[class_name] = methods
        
        # Find gaps
        untested_functions = source_functions - tested_functions
        untested_methods = {}
        
        for class_name, methods in source_classes.items():
            if class_name in tested_classes:
                untested = methods - tested_classes[class_name]
                if untested:
                    untested_methods[class_name] = list(untested)
            else:
                untested_methods[class_name] = list(methods)
        
        coverage_percent = 0
        total_items = len(source_functions) + sum(len(m) for m in source_classes.values())
        tested_items = len(tested_functions) + sum(len(m) for m in tested_classes.values())
        
        if total_items > 0:
            coverage_percent = round((tested_items / total_items) * 100, 1)
        
        return {
            "module": module_path,
            "test_file": test_file if os.path.exists(test_file) else "Not found",
            "coverage_percent": coverage_percent,
            "untested_functions": list(untested_functions),
            "untested_methods": untested_methods,
            "summary": {
                "total_functions": len(source_functions),
                "tested_functions": len(tested_functions),
                "total_classes": len(source_classes),
                "tested_classes": len(tested_classes)
            }
        }
    
    return _run_tool("detect_test_gaps", logic)


# ============================================================
# TOOL REGISTRATION
# ============================================================

_TOOL_NAMES = [
    # Original tools
    "run_command",
    "interactive_command",
    "read_file",
    "write_file",
    "list_directory",
    "search_files",
    "replace_in_file",
    "list_processes",
    "kill_process",
    "get_env",
    "system_info",
    "git_status",
    "git_diff",
    "git_commit",
    "tail_file",
    "check_port",
    "docker_ps",
    "create_report_from_results",
    
    # Phase 2.1: Code Analysis
    "analyze_code_quality",
    "detect_security_issues",
    "profile_code_performance",
    
    # Phase 2.2: Project Operations
    "analyze_project_structure",
    "detect_circular_dependencies",
    "generate_dependency_graph",
    
    # Phase 2.3: Debugging
    "trace_execution",
    "analyze_error_logs",
    "compare_outputs",
    
    # Phase 2.4: Testing
    "generate_unit_tests",
    "run_tests_with_coverage",
    "detect_test_gaps",
]

for name in _TOOL_NAMES:
    get_server_state().register_tool(name)





# ============================================================
# PHASE 3.1: MULTI-FILE DEBUGGING SYSTEM
# ============================================================

@mcp.tool
def trace_error_origin(error_message: str, project_root: str = ".") -> Dict[str, Any]:
    """
    Find which file/line caused an error across entire project
    Traces error through call stack and file references
    """
    def logic():
        root = resolve_workspace_path(project_root)
        
        if not validate_workspace_path(root):
            return {"error": "Invalid project root path"}
        
        results = {
            "error_message": error_message,
            "project_root": root,
            "potential_sources": [],
            "file_references": [],
            "stack_trace_files": []
        }
        
        # Extract file paths from error message
        # Common patterns: "File \"path\", line X" or "at path:line"
        file_patterns = [
            r'File "([^"]+)", line (\d+)',
            r'File \'([^\']+)\', line (\d+)',
            r'at ([^:]+):(\d+)',
            r'in ([^:]+):(\d+)',
        ]
        
        for pattern in file_patterns:
            matches = re.finditer(pattern, error_message)
            for match in matches:
                file_path = match.group(1)
                line_num = int(match.group(2))
                
                # Resolve relative paths
                if not os.path.isabs(file_path):
                    full_path = os.path.join(root, file_path)
                else:
                    full_path = file_path
                
                if os.path.exists(full_path):
                    results["stack_trace_files"].append({
                        "file": file_path,
                        "line": line_num,
                        "full_path": full_path,
                        "exists": True
                    })
                else:
                    results["stack_trace_files"].append({
                        "file": file_path,
                        "line": line_num,
                        "full_path": full_path,
                        "exists": False
                    })
        
        # Extract error type (e.g., "NameError", "TypeError")
        error_type_match = re.search(r'(\w+Error|Exception):', error_message)
        error_type = error_type_match.group(1) if error_type_match else "Unknown"
        results["error_type"] = error_type
        
        # Search for similar error patterns in project files
        search_terms = []
        
        # Extract variable/function names from error
        if "NameError" in error_type or "not defined" in error_message:
            name_match = re.search(r"name '(\w+)' is not defined", error_message)
            if name_match:
                search_terms.append(name_match.group(1))
        
        # Search project files for these terms
        if search_terms:
            for search_term in search_terms:
                for root_dir, dirs, files in os.walk(root):
                    # Skip common non-code directories
                    dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
                    
                    for file in files:
                        if not file.endswith('.py'):
                            continue
                        
                        file_path = os.path.join(root_dir, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                for i, line in enumerate(f, 1):
                                    if search_term in line:
                                        results["file_references"].append({
                                            "file": os.path.relpath(file_path, root),
                                            "line": i,
                                            "content": line.strip(),
                                            "search_term": search_term
                                        })
                        except Exception:
                            continue
        
        # Rank potential sources by likelihood
        # Priority: stack trace files > file references
        for trace_file in results["stack_trace_files"]:
            if trace_file["exists"]:
                results["potential_sources"].append({
                    "file": trace_file["file"],
                    "line": trace_file["line"],
                    "confidence": "high",
                    "reason": "Found in stack trace"
                })
        
        for ref in results["file_references"][:10]:  # Top 10
            results["potential_sources"].append({
                "file": ref["file"],
                "line": ref["line"],
                "confidence": "medium",
                "reason": f"Contains '{ref['search_term']}'"
            })
        
        results["summary"] = {
            "total_stack_files": len(results["stack_trace_files"]),
            "total_references": len(results["file_references"]),
            "top_candidate": results["potential_sources"][0] if results["potential_sources"] else None
        }
        
        return results
    
    return _run_tool("trace_error_origin", logic)


@mcp.tool
def find_breaking_change(working_commit: str, broken_commit: str, test_command: str = None) -> Dict[str, Any]:
    """
    Git bisect automation to find bug-introducing commit
    Automatically tests each commit to identify the breaking change
    """
    def logic():
        workspace = get_server_state().workspace_root or os.getcwd()
        
        results = {
            "working_commit": working_commit,
            "broken_commit": broken_commit,
            "test_command": test_command,
            "bisect_log": [],
            "breaking_commit": None,
            "commits_tested": 0
        }
        
        # Verify git repository
        git_check = execute_command("git rev-parse --git-dir", cwd=workspace)
        if not git_check.get("success"):
            return {"error": "Not a git repository"}
        
        # Verify commits exist
        for commit in [working_commit, broken_commit]:
            check = execute_command(f"git rev-parse {commit}", cwd=workspace)
            if not check.get("success"):
                return {"error": f"Commit not found: {commit}"}
        
        # Start git bisect
        execute_command("git bisect reset", cwd=workspace)  # Clean up any previous bisect
        
        start_result = execute_command(f"git bisect start {broken_commit} {working_commit}", cwd=workspace)
        results["bisect_log"].append({
            "step": "start",
            "output": start_result.get("output", "")
        })
        
        if not start_result.get("success"):
            return {"error": "Failed to start git bisect"}
        
        # If test command provided, automate bisect
        if test_command:
            # Automated bisect
            bisect_cmd = f'git bisect run sh -c "{test_command}"'
            bisect_result = execute_command(bisect_cmd, cwd=workspace, timeout=300)
            
            results["bisect_log"].append({
                "step": "automated_run",
                "output": bisect_result.get("output", "")
            })
            
            # Parse result to find breaking commit
            output = bisect_result.get("output", "")
            commit_match = re.search(r'([a-f0-9]{7,40}) is the first bad commit', output)
            
            if commit_match:
                results["breaking_commit"] = commit_match.group(1)
                
                # Get commit details
                show_result = execute_command(f"git show --stat {results['breaking_commit']}", cwd=workspace)
                results["commit_details"] = show_result.get("output", "")
        
        else:
            # Manual bisect - just get the commit range
            log_result = execute_command(
                f"git log --oneline {working_commit}..{broken_commit}",
                cwd=workspace
            )
            
            results["commit_range"] = log_result.get("output", "").split('\n')
            results["commits_tested"] = len(results["commit_range"])
            results["bisect_log"].append({
                "step": "manual_mode",
                "message": "Use 'git bisect good' or 'git bisect bad' to continue manually"
            })
        
        # Reset bisect
        execute_command("git bisect reset", cwd=workspace)
        
        return results
    
    return _run_tool("find_breaking_change", logic)


@mcp.tool
def refactor_function_name(old_name: str, new_name: str, scope: str = ".") -> Dict[str, Any]:
    """
    Safely rename function across all files, update imports and references
    """
    def logic():
        root = resolve_workspace_path(scope)
        
        if not validate_workspace_path(root):
            return {"error": "Invalid scope path"}
        
        results = {
            "old_name": old_name,
            "new_name": new_name,
            "scope": root,
            "files_modified": [],
            "changes": [],
            "dry_run": True  # Always dry run first for safety
        }
        
        # Patterns to match
        patterns = [
            # Function definitions
            (rf'def {old_name}\s*\(', f'def {new_name}('),
            # Function calls
            (rf'\b{old_name}\s*\(', f'{new_name}('),
            # Imports
            (rf'from .+ import .*\b{old_name}\b', lambda m: m.group(0).replace(old_name, new_name)),
            (rf'import .+\b{old_name}\b', lambda m: m.group(0).replace(old_name, new_name)),
        ]
        
        # Scan files
        for root_dir, dirs, files in os.walk(root):
            # Skip common non-code directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root_dir, file)
                rel_path = os.path.relpath(file_path, root)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                    
                    modified_content = original_content
                    file_changes = []
                    
                    # Apply patterns
                    for pattern, replacement in patterns:
                        matches = list(re.finditer(pattern, modified_content))
                        
                        for match in matches:
                            line_num = modified_content[:match.start()].count('\n') + 1
                            
                            if callable(replacement):
                                new_text = replacement(match)
                            else:
                                new_text = re.sub(pattern, replacement, match.group(0))
                            
                            file_changes.append({
                                "line": line_num,
                                "old": match.group(0),
                                "new": new_text
                            })
                        
                        if callable(replacement):
                            # Need to handle callable replacements differently
                            modified_content = re.sub(pattern, replacement, modified_content)
                        else:
                            modified_content = re.sub(pattern, replacement, modified_content)
                    
                    if file_changes:
                        results["files_modified"].append(rel_path)
                        results["changes"].extend([
                            {
                                "file": rel_path,
                                **change
                            }
                            for change in file_changes
                        ])
                
                except Exception as e:
                    results.setdefault("errors", []).append({
                        "file": rel_path,
                        "error": str(e)
                    })
        
        results["summary"] = {
            "files_affected": len(results["files_modified"]),
            "total_changes": len(results["changes"]),
            "note": "This is a dry run. Use apply_refactoring() to actually modify files."
        }
        
        return results
    
    return _run_tool("refactor_function_name", logic)


# ============================================================
# PHASE 3.2: RUNTIME ANALYSIS
# ============================================================

@mcp.tool
def inspect_running_process(pid: int) -> Dict[str, Any]:
    """
    Attach debugger to running Python process, extract locals
    NOTE: This requires the process to be Python and debuggable
    """
    def logic():
        import psutil
        
        results = {
            "pid": pid,
            "process_info": {},
            "threads": [],
            "memory": {},
            "open_files": []
        }
        
        try:
            process = psutil.Process(pid)
            
            # Basic process info
            results["process_info"] = {
                "name": process.name(),
                "exe": process.exe(),
                "cwd": process.cwd(),
                "status": process.status(),
                "create_time": process.create_time(),
                "cmdline": process.cmdline()
            }
            
            # Memory info
            mem_info = process.memory_info()
            results["memory"] = {
                "rss_mb": mem_info.rss / (1024 * 1024),  # Resident Set Size
                "vms_mb": mem_info.vms / (1024 * 1024),  # Virtual Memory Size
                "percent": process.memory_percent()
            }
            
            # CPU info
            results["cpu"] = {
                "percent": process.cpu_percent(interval=0.1),
                "num_threads": process.num_threads()
            }
            
            # Threads
            try:
                for thread in process.threads():
                    results["threads"].append({
                        "id": thread.id,
                        "user_time": thread.user_time,
                        "system_time": thread.system_time
                    })
            except Exception:
                pass
            
            # Open files
            try:
                for file in process.open_files():
                    results["open_files"].append({
                        "path": file.path,
                        "fd": file.fd
                    })
            except Exception:
                pass
            
            # Environment variables
            try:
                results["environment"] = dict(process.environ())
            except Exception:
                results["environment"] = {"error": "Cannot access environment"}
            
            # Connections (network)
            try:
                connections = []
                for conn in process.connections():
                    connections.append({
                        "fd": conn.fd,
                        "family": str(conn.family),
                        "type": str(conn.type),
                        "local_addr": str(conn.laddr) if conn.laddr else None,
                        "remote_addr": str(conn.raddr) if conn.raddr else None,
                        "status": conn.status
                    })
                results["connections"] = connections
            except Exception:
                pass
            
            return results
            
        except psutil.NoSuchProcess:
            return {"error": f"Process {pid} not found"}
        except psutil.AccessDenied:
            return {"error": f"Access denied to process {pid}"}
    
    return _run_tool("inspect_running_process", logic)


@mcp.tool
def detect_memory_leaks(script_path: str, duration_seconds: int = 10) -> Dict[str, Any]:
    """
    Run script with memory_profiler to identify memory leaks
    Monitors memory usage over time to detect growing allocations
    """
    def logic():
        file_path = resolve_workspace_path(script_path)
        
        if not validate_workspace_path(file_path):
            return {"error": "Invalid script path"}
        
        if not os.path.exists(file_path):
            return {"error": "Script not found"}
        
        results = {
            "script": script_path,
            "duration": duration_seconds,
            "memory_profile": [],
            "leak_detected": False,
            "leak_rate_mb_per_sec": 0
        }
        
        # Check if memory_profiler is available
        try:
            import memory_profiler
        except ImportError:
            return {
                "error": "memory_profiler not installed",
                "install_command": "pip install memory-profiler --break-system-packages"
            }
        
        # Create a monitoring script
        monitor_script = f"""
import sys
import time
import psutil
import subprocess

# Start the script as subprocess
proc = subprocess.Popen([sys.executable, '{file_path}'], 
                       stdout=subprocess.PIPE, 
                       stderr=subprocess.PIPE)

measurements = []
start_time = time.time()

try:
    process = psutil.Process(proc.pid)
    
    while time.time() - start_time < {duration_seconds}:
        try:
            mem_info = process.memory_info()
            measurements.append({{
                'timestamp': time.time() - start_time,
                'rss_mb': mem_info.rss / (1024 * 1024),
                'vms_mb': mem_info.vms / (1024 * 1024)
            }})
            time.sleep(0.5)
        except psutil.NoSuchProcess:
            break
    
    proc.terminate()
    proc.wait(timeout=5)
    
except Exception as e:
    proc.kill()
    raise e

# Output results as JSON
import json
print(json.dumps(measurements))
"""
        
        # Write monitor script
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            monitor_path = f.name
            f.write(monitor_script)
        
        try:
            # Run monitor
            result = execute_command(
                f"{sys.executable} {monitor_path}",
                timeout=duration_seconds + 10
            )
            
            if result.get("success"):
                try:
                    measurements = json.loads(result.get("output", "[]"))
                    results["memory_profile"] = measurements
                    
                    # Analyze for leaks
                    if len(measurements) >= 3:
                        # Calculate memory growth rate
                        first_mem = measurements[0]["rss_mb"]
                        last_mem = measurements[-1]["rss_mb"]
                        time_diff = measurements[-1]["timestamp"] - measurements[0]["timestamp"]
                        
                        if time_diff > 0:
                            growth_rate = (last_mem - first_mem) / time_diff
                            results["leak_rate_mb_per_sec"] = round(growth_rate, 4)
                            
                            # Threshold: > 0.1 MB/sec growth is suspicious
                            if growth_rate > 0.1:
                                results["leak_detected"] = True
                                results["warning"] = f"Memory growing at {growth_rate:.3f} MB/sec"
                        
                        results["summary"] = {
                            "initial_memory_mb": round(first_mem, 2),
                            "final_memory_mb": round(last_mem, 2),
                            "growth_mb": round(last_mem - first_mem, 2),
                            "duration_seconds": round(time_diff, 2)
                        }
                
                except json.JSONDecodeError:
                    results["error"] = "Failed to parse monitoring output"
            else:
                results["error"] = result.get("error", "Monitoring failed")
        
        finally:
            # Cleanup
            try:
                os.remove(monitor_path)
            except:
                pass
        
        return results
    
    return _run_tool("detect_memory_leaks", logic)


# ============================================================
# TOOL REGISTRATION
# ============================================================

_PHASE3_TOOL_NAMES = [
    # Multi-File Debugging
    "trace_error_origin",
    "find_breaking_change",
    "refactor_function_name",
    
    # Runtime Analysis
    "inspect_running_process",
    "detect_memory_leaks",
]

for name in _PHASE3_TOOL_NAMES:
    get_server_state().register_tool(name)



class UndoManager:
    """
    Global undo/redo system for file operations
    Tracks changes and allows rollback
    """
    
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.max_history = 50
        self.backup_dir = ".mcp_backups"
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def record_action(self, action_type: str, target: str, before_state: Any = None):
        """Record an action for potential undo"""
        action = {
            "id": hashlib.md5(f"{time.time()}{target}".encode()).hexdigest()[:8],
            "timestamp": time.time(),
            "type": action_type,
            "target": target,
            "before_state": before_state
        }
        
        self.history.append(action)
        
        # Limit history size
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        return action["id"]
    
    def get_last_action(self) -> Optional[Dict[str, Any]]:
        """Get the most recent action"""
        return self.history[-1] if self.history else None
    
    def undo_file_write(self, file_path: str, backup_content: str) -> bool:
        """Undo a file write operation"""
        try:
            if backup_content is not None:
                # Restore from backup
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
            else:
                # File was created, delete it
                if os.path.exists(file_path):
                    os.remove(file_path)
            return True
        except Exception:
            return False
    
    def undo_file_delete(self, file_path: str, backup_path: str) -> bool:
        """Undo a file delete operation"""
        try:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
                return True
            return False
        except Exception:
            return False


# Global undo manager
_undo_manager = UndoManager()


@mcp.tool
def undo_last_action() -> Dict[str, Any]:
    """
    Rollback the last file operation
    Supports undoing: write_file, delete_file, replace_in_file
    """
    last_action = _undo_manager.get_last_action()
    
    if not last_action:
        return {
            "success": False,
            "error": "No actions to undo"
        }
    
    action_type = last_action["type"]
    target = last_action["target"]
    
    try:
        if action_type == "write_file":
            success = _undo_manager.undo_file_write(
                target,
                last_action["before_state"]
            )
        elif action_type == "delete_file":
            success = _undo_manager.undo_file_delete(
                target,
                last_action["before_state"]
            )
        else:
            return {
                "success": False,
                "error": f"Undo not supported for action type: {action_type}"
            }
        
        if success:
            _undo_manager.history.pop()  # Remove from history
            return {
                "success": True,
                "action_undone": action_type,
                "target": target,
                "timestamp": last_action["timestamp"]
            }
        else:
            return {
                "success": False,
                "error": "Failed to undo action"
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool
def run_command_sandboxed(command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Run command in isolated environment with safety checks
    Creates temporary directory for execution
    """

    dangerous_patterns = [
        "rm -rf /",
        "mkfs",
        "dd if=/dev/zero",
        "> /dev/sda",
        "chmod 777 /",
        "shutdown",
        "reboot"
    ]

    for pattern in dangerous_patterns:
        if pattern in command.lower():
            return {
                "success": False,
                "error": f"Dangerous command blocked: contains '{pattern}'"
            }

    # Create sandbox on same drive as workspace (Windows-safe)
    workspace_dir = os.getcwd()
    workspace_drive = os.path.splitdrive(workspace_dir)[0]

    sandbox_base = os.path.join(workspace_drive + "\\", "mcp_sandbox")
    os.makedirs(sandbox_base, exist_ok=True)

    temp_dir = tempfile.mkdtemp(prefix="mcp_sandbox_", dir=sandbox_base)

    try:
        result = execute_command(
            command,
            cwd=temp_dir,
            timeout=timeout
        )

        created_files = os.listdir(temp_dir)

        return {
            "success":  result.get("return_code", 1) == 0,
            "output": result.get("output", ""),
            "return_code": result.get("return_code", -1),
            "created_files": created_files,
            "sandbox_dir": temp_dir
        }


    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@mcp.tool
def backup_before_operation(file_path: str) -> Dict[str, Any]:
    """
    Create backup before potentially destructive operation
    Automatically called by enhanced write/delete operations
    """
    full_path = resolve_workspace_path(file_path)
    
    if not validate_workspace_path(full_path):
        return {"success": False, "error": "Invalid path"}
    
    if not os.path.exists(full_path):
        return {"success": False, "error": "File not found"}
    
    # Create backup
    backup_dir = ".mcp_backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{os.path.basename(file_path)}.{timestamp}.backup"
    backup_path = os.path.join(backup_dir, backup_name)
    
    try:
        shutil.copy2(full_path, backup_path)
        
        return {
            "success": True,
            "backup_path": backup_path,
            "original_size": os.path.getsize(full_path),
            "timestamp": timestamp
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# PHASE 5.2: OBSERVABILITY - STRUCTURED LOGGING
# ============================================================

class StructuredLogger:
    """
    JSON-based structured logging with trace IDs
    """
    
    def __init__(self, log_file: str = "mcp_operations.jsonl"):
        self.log_file = log_file
        self.current_trace_id = None
    
    def start_trace(self) -> str:
        """Start a new trace for a sequence of operations"""
        self.current_trace_id = hashlib.md5(
            f"{time.time()}{os.getpid()}".encode()
        ).hexdigest()[:16]
        return self.current_trace_id
    
    def log(self, level: str, message: str, **kwargs):
        """Log a structured message"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "trace_id": self.current_trace_id,
            **kwargs
        }
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception:
            pass  # Don't fail operations due to logging
    
    def log_tool_execution(self, tool_name: str, duration: float, 
                          success: bool, **kwargs):
        """Log tool execution metrics"""
        self.log(
            "INFO" if success else "ERROR",
            f"Tool execution: {tool_name}",
            tool=tool_name,
            duration_ms=round(duration * 1000, 2),
            success=success,
            **kwargs
        )


# Global logger
_logger = StructuredLogger()


class ToolMetrics:
    """
    Track performance metrics for all tools
    """
    
    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_duration_ms": 0,
            "min_duration_ms": float('inf'),
            "max_duration_ms": 0,
            "last_called": None,
            "errors": []
        })
    
    def record_execution(self, tool_name: str, duration: float, 
                        success: bool, error: Optional[str] = None):
        """Record a tool execution"""
        metrics = self.metrics[tool_name]
        
        metrics["total_calls"] += 1
        if success:
            metrics["successful_calls"] += 1
        else:
            metrics["failed_calls"] += 1
            if error:
                metrics["errors"].append({
                    "timestamp": time.time(),
                    "error": error
                })
                # Keep only last 10 errors
                metrics["errors"] = metrics["errors"][-10:]
        
        duration_ms = duration * 1000
        metrics["total_duration_ms"] += duration_ms
        metrics["min_duration_ms"] = min(metrics["min_duration_ms"], duration_ms)
        metrics["max_duration_ms"] = max(metrics["max_duration_ms"], duration_ms)
        metrics["last_called"] = time.time()
    
    def get_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for a tool or all tools"""
        if tool_name:
            if tool_name not in self.metrics:
                return {"error": "Tool not found"}
            
            metrics = self.metrics[tool_name]
            return {
                "tool": tool_name,
                **self._calculate_stats(metrics)
            }
        else:
            return {
                tool: self._calculate_stats(metrics)
                for tool, metrics in self.metrics.items()
            }
    
    def _calculate_stats(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived statistics"""
        total = metrics["total_calls"]
        if total == 0:
            avg_duration = 0
            success_rate = 0
        else:
            avg_duration = metrics["total_duration_ms"] / total
            success_rate = (metrics["successful_calls"] / total) * 100
        
        return {
            "total_calls": total,
            "successful_calls": metrics["successful_calls"],
            "failed_calls": metrics["failed_calls"],
            "success_rate": round(success_rate, 2),
            "avg_duration_ms": round(avg_duration, 2),
            "min_duration_ms": round(metrics["min_duration_ms"], 2) if metrics["min_duration_ms"] != float('inf') else 0,
            "max_duration_ms": round(metrics["max_duration_ms"], 2),
            "last_called": metrics["last_called"],
            "recent_errors": metrics["errors"][-5:]  # Last 5 errors
        }


# Global metrics tracker
_tool_metrics = ToolMetrics()


# ============================================================
# PHASE 5.3: CACHING & OPTIMIZATION
# ============================================================

class LRUCache:
    """
    Least Recently Used cache with size limits
    """
    
    def __init__(self, max_size: int = 100, max_memory_mb: int = 50):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]["value"]
        return None
    
    def put(self, key: str, value: Any, ttl: int = 300):
        """Put item in cache with TTL"""
        # Calculate approximate size
        size = len(json.dumps(value, default=str).encode())
        
        # Remove expired entries
        self._evict_expired()
        
        # Evict if necessary
        while (len(self.cache) >= self.max_size or 
               self.current_memory + size > self.max_memory_bytes):
            if not self.cache:
                break
            self._evict_oldest()
        
        self.cache[key] = {
            "value": value,
            "size": size,
            "expires_at": time.time() + ttl
        }
        self.cache.move_to_end(key)
        self.current_memory += size
    
    def invalidate(self, key: str):
        """Remove item from cache"""
        if key in self.cache:
            self.current_memory -= self.cache[key]["size"]
            del self.cache[key]
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        keys_to_remove = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_remove:
            self.invalidate(key)
    
    def _evict_oldest(self):
        """Evict least recently used item"""
        if self.cache:
            key, value = self.cache.popitem(last=False)
            self.current_memory -= value["size"]
    
    def _evict_expired(self):
        """Remove expired entries"""
        now = time.time()
        expired = [k for k, v in self.cache.items() if v["expires_at"] < now]
        for key in expired:
            self.invalidate(key)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        self._evict_expired()
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "memory_mb": round(self.current_memory / (1024 * 1024), 2),
            "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
            "hit_rate": "N/A"  # Would need hit/miss tracking
        }


# Global cache
_resource_cache = LRUCache(max_size=100, max_memory_mb=50)


@mcp.tool
def clear_cache(pattern: Optional[str] = None) -> Dict[str, Any]:
    """
    Clear resource cache
    If pattern provided, only clear matching entries
    """
    if pattern:
        _resource_cache.invalidate_pattern(pattern)
        return {
            "success": True,
            "message": f"Cleared cache entries matching: {pattern}"
        }
    else:
        # Clear all
        before_size = len(_resource_cache.cache)
        _resource_cache.cache.clear()
        _resource_cache.current_memory = 0
        
        return {
            "success": True,
            "message": f"Cleared {before_size} cache entries"
        }




# ============================================================
# INCREMENTAL ANALYSIS
# ============================================================

class IncrementalAnalyzer:
    """
    Track file changes and only re-analyze modified files
    """
    
    def __init__(self):
        self.file_hashes: Dict[str, str] = {}
        self.analysis_cache: Dict[str, Any] = {}
    
    def file_changed(self, file_path: str) -> bool:
        """Check if file has changed since last analysis"""
        if not os.path.exists(file_path):
            return True
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        old_hash = self.file_hashes.get(file_path)
        changed = old_hash != file_hash
        
        if changed:
            self.file_hashes[file_path] = file_hash
        
        return changed
    
    def get_cached_analysis(self, file_path: str) -> Optional[Any]:
        """Get cached analysis if file hasn't changed"""
        if not self.file_changed(file_path):
            return self.analysis_cache.get(file_path)
        return None
    
    def cache_analysis(self, file_path: str, analysis: Any):
        """Cache analysis result"""
        self.analysis_cache[file_path] = analysis


# Global incremental analyzer
_incremental_analyzer = IncrementalAnalyzer()


# ============================================================
# TOOL REGISTRATION
# ============================================================

_PHASE5_TOOL_NAMES = [
    # Safety
    "undo_last_action",
    "run_command_sandboxed",
    "backup_before_operation",
    
    # Caching
    "clear_cache",
]

for name in _PHASE5_TOOL_NAMES:
    get_server_state().register_tool(name)



# ============================================================
# HELPER: Wrap tool execution with metrics
# ============================================================

def track_tool_execution(func):
    """Decorator to track tool execution metrics"""
    def wrapper(*args, **kwargs):
        tool_name = func.__name__
        trace_id = _logger.start_trace()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            success = result.get("success", True) if isinstance(result, dict) else True
            
            _tool_metrics.record_execution(tool_name, duration, success)
            _logger.log_tool_execution(
                tool_name,
                duration,
                success,
                trace_id=trace_id
            )
            
            return result
        
        except Exception as e:
            duration = time.time() - start_time
            _tool_metrics.record_execution(tool_name, duration, False, str(e))
            _logger.log_tool_execution(
                tool_name,
                duration,
                False,
                error=str(e),
                trace_id=trace_id
            )
            raise
    
    return wrapper


# Export for use in other modules
__all__ = [
    'UndoManager',
    'StructuredLogger',
    'ToolMetrics',
    'LRUCache',
    'IncrementalAnalyzer',
    'track_tool_execution',
    '_undo_manager',
    '_logger',
    '_tool_metrics',
    '_resource_cache',
    '_incremental_analyzer'
]



@mcp.tool
def ai_code_review(file_path: str, check_security: bool = True,
                   check_style: bool = True) -> Dict[str, Any]:
    """
    Comprehensive AI-powered code review
    Combines multiple analysis tools for complete review
    """
    full_path = resolve_workspace_path(file_path)
    
    if not validate_workspace_path(full_path):
        return {"success": False, "error": "Invalid path"}
    
    if not os.path.exists(full_path):
        return {"success": False, "error": "File not found"}
    
    review_results = {
        "file": file_path,
        "timestamp": datetime.now().isoformat(),
        "overall_score": 0,
        "issues": [],
        "suggestions": [],
        "metrics": {}
    }
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
        
        # Code Quality Analysis
        quality_issues = []
        
        # Check 1: Function complexity
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = _calculate_complexity(node)
                if complexity > 10:
                    quality_issues.append({
                        "type": "high_complexity",
                        "severity": "medium",
                        "line": node.lineno,
                        "function": node.name,
                        "message": f"High cyclomatic complexity: {complexity}",
                        "suggestion": "Consider breaking down into smaller functions"
                    })
        
        # Check 2: Long functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                lines = node.end_lineno - node.lineno
                if lines > 50:
                    quality_issues.append({
                        "type": "long_function",
                        "severity": "low",
                        "line": node.lineno,
                        "function": node.name,
                        "message": f"Function is {lines} lines long",
                        "suggestion": "Consider splitting into multiple functions"
                    })
        
        # Check 3: Too many parameters
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                param_count = len(node.args.args)
                if param_count > 5:
                    quality_issues.append({
                        "type": "too_many_parameters",
                        "severity": "low",
                        "line": node.lineno,
                        "function": node.name,
                        "message": f"Function has {param_count} parameters",
                        "suggestion": "Consider using a config object or dataclass"
                    })
        
        # Check 4: Missing docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    quality_issues.append({
                        "type": "missing_docstring",
                        "severity": "low",
                        "line": node.lineno,
                        "name": node.name,
                        "message": f"Missing docstring for {type(node).__name__}",
                        "suggestion": "Add docstring describing purpose and parameters"
                    })
        
        # Security Analysis (if enabled)
        security_issues = []
        if check_security:
            # Check for common security issues
            for node in ast.walk(tree):
                # Dangerous exec/eval usage
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ['exec', 'eval']:
                            security_issues.append({
                                "type": "dangerous_function",
                                "severity": "high",
                                "line": node.lineno,
                                "message": f"Use of {node.func.id}() detected",
                                "suggestion": "Avoid exec/eval - use safer alternatives"
                            })
                
                # SQL injection risk
                if isinstance(node, ast.JoinedStr):  # f-string
                    security_issues.append({
                        "type": "potential_sql_injection",
                        "severity": "medium",
                        "line": node.lineno,
                        "message": "F-string in SQL query may be vulnerable",
                        "suggestion": "Use parameterized queries"
                    })
        
        # Style Analysis
        style_issues = []
        if check_style:
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Line too long
                if len(line) > 100:
                    style_issues.append({
                        "type": "line_too_long",
                        "severity": "low",
                        "line": i,
                        "message": f"Line length: {len(line)} chars",
                        "suggestion": "Keep lines under 100 characters"
                    })
                
                # Trailing whitespace
                if line.rstrip() != line and line.strip():
                    style_issues.append({
                        "type": "trailing_whitespace",
                        "severity": "low",
                        "line": i,
                        "message": "Trailing whitespace",
                        "suggestion": "Remove trailing spaces"
                    })
        
        # Combine all issues
        all_issues = quality_issues + security_issues + style_issues
        review_results["issues"] = all_issues
        
        # Calculate overall score (0-100)
        high_severity = len([i for i in all_issues if i.get("severity") == "high"])
        medium_severity = len([i for i in all_issues if i.get("severity") == "medium"])
        low_severity = len([i for i in all_issues if i.get("severity") == "low"])
        
        score = 100
        score -= high_severity * 10
        score -= medium_severity * 5
        score -= low_severity * 2
        review_results["overall_score"] = max(0, score)
        
        # Generate suggestions
        if high_severity > 0:
            review_results["suggestions"].append("🔴 Critical issues found - address high severity items first")
        if medium_severity > 5:
            review_results["suggestions"].append("🟡 Multiple medium severity issues - consider refactoring")
        if low_severity > 10:
            review_results["suggestions"].append("ℹ️ Many style issues - run formatter")
        if review_results["overall_score"] > 90:
            review_results["suggestions"].append("✅ Great job! Code quality is excellent")
        
        # Metrics
        review_results["metrics"] = {
            "total_issues": len(all_issues),
            "high_severity": high_severity,
            "medium_severity": medium_severity,
            "low_severity": low_severity,
            "total_lines": len(lines),
            "functions_analyzed": len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
        }
        
        return {
            "success": True,
            "result": review_results
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _calculate_complexity(node):
    """Calculate cyclomatic complexity"""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    return complexity


# ============================================================
# PHASE 7.2: AUTO-DOCUMENTATION GENERATOR
# ============================================================

@mcp.tool
def generate_docs(project_root: str = ".", output_dir: str = "docs") -> Dict[str, Any]:
    """
    Auto-generate comprehensive project documentation
    Creates README, API docs, architecture diagrams, examples
    """
    workspace = resolve_workspace_path(project_root)
    
    if not validate_workspace_path(workspace):
        return {"success": False, "error": "Invalid path"}
    
    docs_dir = os.path.join(workspace, output_dir)
    os.makedirs(docs_dir, exist_ok=True)
    
    generated_files = []
    
    try:
        # 1. Generate README.md
        readme_content = _generate_readme(workspace)
        readme_path = os.path.join(workspace, "README.md")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        generated_files.append("README.md")
        
        # 2. Generate API Documentation
        api_docs = _generate_api_docs(workspace)
        api_path = os.path.join(docs_dir, "API.md")
        with open(api_path, 'w', encoding='utf-8') as f:
            f.write(api_docs)
        generated_files.append(f"{output_dir}/API.md")
        
        # 3. Generate Architecture Overview
        arch_docs = _generate_architecture_docs(workspace)
        arch_path = os.path.join(docs_dir, "ARCHITECTURE.md")
        with open(arch_path, 'w', encoding='utf-8') as f:
            f.write(arch_docs)
        generated_files.append(f"{output_dir}/ARCHITECTURE.md")
        
        # 4. Generate Usage Examples
        examples = _generate_examples(workspace)
        examples_path = os.path.join(docs_dir, "EXAMPLES.md")
        with open(examples_path, 'w', encoding='utf-8') as f:
            f.write(examples)
        generated_files.append(f"{output_dir}/EXAMPLES.md")
        
        return {
            "success": True,
            "generated_files": generated_files,
            "output_directory": docs_dir
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "generated_files": generated_files
        }


def _generate_readme(workspace: str) -> str:
    """Generate README.md content"""
    project_name = os.path.basename(workspace)
    
    # Analyze project structure
    python_files = []
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv'}]
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.relpath(os.path.join(root, file), workspace))
    
    # Check for requirements
    req_file = os.path.join(workspace, "requirements.txt")
    has_requirements = os.path.exists(req_file)
    
    readme = f"""# {project_name}

## Overview

This project contains {len(python_files)} Python files.

## Installation

"""
    
    if has_requirements:
        readme += """```bash
pip install -r requirements.txt
```
"""
    else:
        readme += """```bash
# Install dependencies (requirements.txt not found)
pip install -r requirements.txt
```
"""
    
    readme += """
## Usage

```python
# Add usage examples here
```

## Project Structure

"""
    
    for py_file in python_files[:10]:  # First 10 files
        readme += f"- `{py_file}`\n"
    
    if len(python_files) > 10:
        readme += f"\n...and {len(python_files) - 10} more files\n"
    
    readme += f"""
## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Add license information]

---
*Generated automatically by MCP Terminal Agent*
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    return readme


def _generate_api_docs(workspace: str) -> str:
    """Generate API documentation"""
    docs = "# API Documentation\n\n"
    
    # Find all public functions and classes
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv'}]
        
        for file in files:
            if not file.endswith('.py'):
                continue
            
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, workspace)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                # Extract functions and classes
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                        docstring = ast.get_docstring(node) or "No description"
                        docs += f"\n## `{node.name}()`\n\n"
                        docs += f"**File**: `{rel_path}` (line {node.lineno})\n\n"
                        docs += f"{docstring}\n\n"
                    
                    elif isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
                        docstring = ast.get_docstring(node) or "No description"
                        docs += f"\n## Class: `{node.name}`\n\n"
                        docs += f"**File**: `{rel_path}` (line {node.lineno})\n\n"
                        docs += f"{docstring}\n\n"
            
            except Exception:
                continue
    
    return docs


def _generate_architecture_docs(workspace: str) -> str:
    """Generate architecture documentation"""
    docs = "# Architecture Overview\n\n"
    
    docs += "## Project Structure\n\n"
    docs += "```\n"
    
    # Create tree structure
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv'}]
        
        level = root.replace(workspace, '').count(os.sep)
        indent = ' ' * 2 * level
        docs += f"{indent}{os.path.basename(root)}/\n"
        
        sub_indent = ' ' * 2 * (level + 1)
        for file in files:
            if not file.startswith('.'):
                docs += f"{sub_indent}{file}\n"
    
    docs += "```\n\n"
    
    docs += "## Dependencies\n\n"
    docs += "See `requirements.txt` for full dependency list.\n\n"
    
    return docs


def _generate_examples(workspace: str) -> str:
    """Generate usage examples"""
    examples = "# Usage Examples\n\n"
    
    examples += "## Basic Usage\n\n"
    examples += "```python\n"
    examples += "# Example code here\n"
    examples += "```\n\n"
    
    return examples


# ============================================================
# PHASE 7.3: SEMANTIC CODE SEARCH
# ============================================================

@mcp.tool
def semantic_code_search(query: str, scope: str = ".") -> Dict[str, Any]:
    """
    Search code using natural language queries
    Examples:
    - "Find functions that call database without exception handling"
    - "Show files modified last week importing pandas"
    - "Which file has highest complexity?"
    """
    workspace = resolve_workspace_path(scope)
    
    if not validate_workspace_path(workspace):
        return {"success": False, "error": "Invalid path"}
    
    results = {
        "query": query,
        "matches": [],
        "total_files_searched": 0
    }
    
    # Parse query intent
    query_lower = query.lower()
    
    # Pattern 1: Find functions with specific properties
    if "function" in query_lower:
        results["matches"].extend(_search_functions(workspace, query_lower))
    
    # Pattern 2: Find files by modification time
    if "modified" in query_lower or "changed" in query_lower:
        results["matches"].extend(_search_by_modification(workspace, query_lower))
    
    # Pattern 3: Find by imports
    if "import" in query_lower:
        results["matches"].extend(_search_by_imports(workspace, query_lower))
    
    # Pattern 4: Find by complexity
    if "complexity" in query_lower:
        results["matches"].extend(_search_by_complexity(workspace, query_lower))
    
    # Pattern 5: General text search
    if not results["matches"]:
        results["matches"].extend(_text_search(workspace, query))
    
    return {
        "success": True,
        "result": results
    }


def _search_functions(workspace: str, query: str) -> List[Dict[str, Any]]:
    """Search for functions matching criteria"""
    matches = []
    
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv'}]
        
        for file in files:
            if not file.endswith('.py'):
                continue
            
            file_path = os.path.join(root, file)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Check for exception handling
                        if "exception" in query or "error" in query:
                            has_try = any(isinstance(n, ast.Try) for n in ast.walk(node))
                            
                            if "without" in query or "don't" in query:
                                if not has_try:
                                    matches.append({
                                        "file": os.path.relpath(file_path, workspace),
                                        "function": node.name,
                                        "line": node.lineno,
                                        "reason": "No exception handling"
                                    })
            except Exception:
                continue
    
    return matches


def _search_by_modification(workspace: str, query: str) -> List[Dict[str, Any]]:
    """Search files by modification time"""
    matches = []
    
    # Parse time period
    if "last week" in query:
        threshold = datetime.now() - timedelta(days=7)
    elif "yesterday" in query:
        threshold = datetime.now() - timedelta(days=1)
    elif "today" in query:
        threshold = datetime.now() - timedelta(hours=24)
    else:
        threshold = datetime.now() - timedelta(days=7)  # Default
    
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv'}]
        
        for file in files:
            file_path = os.path.join(root, file)
            
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if mtime > threshold:
                    matches.append({
                        "file": os.path.relpath(file_path, workspace),
                        "modified": mtime.isoformat(),
                        "days_ago": (datetime.now() - mtime).days
                    })
            except Exception:
                continue
    
    return matches


def _search_by_imports(workspace: str, query: str) -> List[Dict[str, Any]]:
    """Search files by imports"""
    matches = []
    
    # Extract module name from query
    words = query.split()
    import_target = None
    for i, word in enumerate(words):
        if word == "import" and i + 1 < len(words):
            import_target = words[i + 1]
            break
    
    if not import_target:
        return matches
    
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv'}]
        
        for file in files:
            if not file.endswith('.py'):
                continue
            
            file_path = os.path.join(root, file)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if import_target in alias.name:
                                matches.append({
                                    "file": os.path.relpath(file_path, workspace),
                                    "line": node.lineno,
                                    "import": alias.name
                                })
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and import_target in node.module:
                            matches.append({
                                "file": os.path.relpath(file_path, workspace),
                                "line": node.lineno,
                                "import": node.module
                            })
            except Exception:
                continue
    
    return matches


def _search_by_complexity(workspace: str, query: str) -> List[Dict[str, Any]]:
    """Search by code complexity"""
    matches = []
    
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv'}]
        
        for file in files:
            if not file.endswith('.py'):
                continue
            
            file_path = os.path.join(root, file)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                max_complexity = 0
                max_function = None
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        complexity = _calculate_complexity(node)
                        if complexity > max_complexity:
                            max_complexity = complexity
                            max_function = node.name
                
                if max_complexity > 0:
                    matches.append({
                        "file": os.path.relpath(file_path, workspace),
                        "max_complexity": max_complexity,
                        "function": max_function
                    })
            except Exception:
                continue
    
    # Sort by complexity
    matches.sort(key=lambda x: x["max_complexity"], reverse=True)
    
    return matches[:10]  # Top 10


def _text_search(workspace: str, query: str) -> List[Dict[str, Any]]:
    """Fallback: Simple text search"""
    matches = []
    
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv'}]
        
        for file in files:
            if not file.endswith('.py'):
                continue
            
            file_path = os.path.join(root, file)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines, 1):
                    if query.lower() in line.lower():
                        matches.append({
                            "file": os.path.relpath(file_path, workspace),
                            "line": i,
                            "content": line.strip()
                        })
            except Exception:
                continue
    
    return matches[:20]  # Top 20


# ============================================================
# TOOL REGISTRATION
# ============================================================

_PHASE7_TOOL_NAMES = [
    "ai_code_review",
    "generate_docs",
    "semantic_code_search",
]

for name in _PHASE7_TOOL_NAMES:
    get_server_state().register_tool(name)
