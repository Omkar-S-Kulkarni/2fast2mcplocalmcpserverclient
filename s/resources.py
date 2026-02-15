"""
Phase 4: Advanced Resources - Resources Module (FIXED)
Project Intelligence & Real-Time Monitoring

Add these resources to your resources.py file.
"""

from __future__ import annotations

import os
import sys
import time
import json
import ast
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime  # FIXED: Added missing import

from mcp_instance import mcp
from state import get_server_state
from helper import resolve_workspace_path
from tools import _tool_metrics,_resource_cache
# Import psutil with error handling
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


# ============================================================
# PHASE 4.1: PROJECT INTELLIGENCE RESOURCES
# ============================================================

@mcp.resource("project://complexity")
def project_complexity():
    """
    Analyze cyclomatic complexity, code smells, and technical debt
    Returns comprehensive code quality metrics
    """
    state = get_server_state()
    workspace = state.workspace_root or os.getcwd()
    
    results = {
        "workspace": workspace,
        "analyzed_at": datetime.now().isoformat(),
        "files": [],
        "summary": {
            "total_files": 0,
            "total_functions": 0,
            "avg_complexity": 0,
            "high_complexity_functions": [],
            "code_smells": []
        }
    }
    
    def calculate_complexity(node):
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Each decision point adds 1
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def detect_code_smells(tree, file_path):
        """Detect common code smells"""
        smells = []
        
        for node in ast.walk(tree):
            # Long function (> 50 lines)
            if isinstance(node, ast.FunctionDef):
                func_lines = node.end_lineno - node.lineno
                if func_lines > 50:
                    smells.append({
                        "type": "long_function",
                        "file": file_path,
                        "function": node.name,
                        "lines": func_lines,
                        "severity": "medium"
                    })
            
            # Too many parameters (> 5)
            if isinstance(node, ast.FunctionDef):
                num_params = len(node.args.args)
                if num_params > 5:
                    smells.append({
                        "type": "too_many_parameters",
                        "file": file_path,
                        "function": node.name,
                        "parameters": num_params,
                        "severity": "low"
                    })
            
            # Deep nesting (> 4 levels) - simplified check
            if isinstance(node, (ast.If, ast.While, ast.For)):
                # Count nesting by checking line indentation
                pass  # Simplified for now
        
        return smells
    
    # Analyze all Python files
    total_complexity = 0
    function_count = 0
    
    for root, dirs, files in os.walk(workspace):
        # Skip common non-code directories
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
        
        for file in files:
            if not file.endswith('.py'):
                continue
            
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, workspace)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                
                file_info = {
                    "path": rel_path,
                    "functions": [],
                    "complexity": 0
                }
                
                # Analyze functions
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        complexity = calculate_complexity(node)
                        
                        file_info["functions"].append({
                            "name": node.name,
                            "line": node.lineno,
                            "complexity": complexity,
                            "parameters": len(node.args.args),
                            "lines": node.end_lineno - node.lineno
                        })
                        
                        total_complexity += complexity
                        function_count += 1
                        
                        # Track high complexity functions
                        if complexity > 10:
                            results["summary"]["high_complexity_functions"].append({
                                "file": rel_path,
                                "function": node.name,
                                "complexity": complexity,
                                "line": node.lineno
                            })
                
                file_info["complexity"] = sum(f["complexity"] for f in file_info["functions"])
                
                # Detect code smells
                smells = detect_code_smells(tree, rel_path)
                results["summary"]["code_smells"].extend(smells)
                
                results["files"].append(file_info)
                results["summary"]["total_files"] += 1
                
            except Exception as e:
                continue
    
    results["summary"]["total_functions"] = function_count
    results["summary"]["avg_complexity"] = round(total_complexity / max(function_count, 1), 2)
    
    # Calculate tech debt score (0-100, higher = more debt)
    tech_debt_score = 0
    tech_debt_score += min(len(results["summary"]["high_complexity_functions"]) * 5, 30)
    tech_debt_score += min(len(results["summary"]["code_smells"]) * 2, 40)
    tech_debt_score += min(int(results["summary"]["avg_complexity"] * 3), 30)
    
    results["summary"]["tech_debt_score"] = min(tech_debt_score, 100)
    
    return results


@mcp.resource("project://dependencies")
def project_dependencies():
    """
    Analyze all imports, external packages, and version conflicts
    Returns comprehensive dependency information
    """
    state = get_server_state()
    workspace = state.workspace_root or os.getcwd()
    
    results = {
        "workspace": workspace,
        "analyzed_at": datetime.now().isoformat(),
        "imports": {},
        "external_packages": set(),
        "stdlib_modules": set(),
        "local_modules": set(),
        "dependency_graph": {},
        "version_info": {}
    }
    
    # Get list of stdlib modules
    stdlib_modules = set(sys.builtin_module_names)
    # Add common stdlib modules
    stdlib_modules.update([
        'os', 'sys', 're', 'json', 'time', 'datetime', 'pathlib',
        'typing', 'collections', 'itertools', 'functools', 'operator',
        'math', 'random', 'string', 'io', 'subprocess', 'threading',
        'multiprocessing', 'asyncio', 'urllib', 'http', 'socket'
    ])
    
    # Analyze all Python files
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
        
        for file in files:
            if not file.endswith('.py'):
                continue
            
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, workspace)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                file_imports = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module = alias.name.split('.')[0]
                            file_imports.append(module)
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module.split('.')[0]
                            file_imports.append(module)
                
                results["imports"][rel_path] = file_imports
                
                # Categorize imports
                for module in file_imports:
                    if module in stdlib_modules:
                        results["stdlib_modules"].add(module)
                    elif module.startswith('.') or any(module.startswith(d) for d in ['src', 'app', 'lib']):
                        results["local_modules"].add(module)
                    else:
                        results["external_packages"].add(module)
            
            except Exception:
                continue
    
    # Convert sets to sorted lists
    results["external_packages"] = sorted(list(results["external_packages"]))
    results["stdlib_modules"] = sorted(list(results["stdlib_modules"]))
    results["local_modules"] = sorted(list(results["local_modules"]))
    
    # Try to get version information from installed packages
    try:
        import pkg_resources
        
        for package in results["external_packages"]:
            try:
                version = pkg_resources.get_distribution(package).version
                results["version_info"][package] = version
            except:
                results["version_info"][package] = "unknown"
    except ImportError:
        pass
    
    # Check for requirements.txt
    req_file = os.path.join(workspace, "requirements.txt")
    if os.path.exists(req_file):
        with open(req_file, 'r') as f:
            results["requirements_txt"] = [
                line.strip() for line in f 
                if line.strip() and not line.startswith('#')
            ]
    
    # Build dependency graph (which files import which)
    for file, imports in results["imports"].items():
        results["dependency_graph"][file] = {
            "imports": imports,
            "imported_by": []
        }
    
    # Find reverse dependencies
    for file, imports in results["imports"].items():
        for imported in imports:
            for other_file in results["imports"]:
                if other_file != file:
                    module_name = os.path.splitext(os.path.basename(file))[0]
                    if module_name in results["imports"][other_file]:
                        results["dependency_graph"][file]["imported_by"].append(other_file)
    
    results["summary"] = {
        "total_files": len(results["imports"]),
        "total_imports": sum(len(imports) for imports in results["imports"].values()),
        "external_packages": len(results["external_packages"]),
        "stdlib_modules": len(results["stdlib_modules"]),
        "local_modules": len(results["local_modules"])
    }
    
    return results


@mcp.resource("project://test-coverage")
def test_coverage_report():
    """
    Generate line-by-line coverage report, identify untested functions
    Requires coverage.py to be installed and .coverage file to exist
    """
    state = get_server_state()
    workspace = state.workspace_root or os.getcwd()
    
    results = {
        "workspace": workspace,
        "analyzed_at": datetime.now().isoformat(),
        "coverage_exists": False,
        "summary": {},
        "files": []
    }
    
    coverage_file = os.path.join(workspace, ".coverage")
    
    if not os.path.exists(coverage_file):
        results["message"] = "No .coverage file found. Run tests with coverage first: pytest --cov"
        return results
    
    results["coverage_exists"] = True
    
    try:
        import coverage
        
        # Load coverage data
        cov = coverage.Coverage(data_file=coverage_file)
        cov.load()
        
        # Get overall stats
        total_statements = 0
        covered_statements = 0
        
        # Analyze each file
        for filename in cov.get_data().measured_files():
            if not filename.endswith('.py'):
                continue
            
            rel_path = os.path.relpath(filename, workspace)
            
            # Get coverage data for file
            analysis = cov.analysis2(filename)
            
            file_info = {
                "path": rel_path,
                "statements": len(analysis[1]),
                "missing": len(analysis[3]),
                "covered": len(analysis[1]) - len(analysis[3]),
                "coverage_percent": 0,
                "missing_lines": sorted(list(analysis[3])),
                "untested_functions": []
            }
            
            if file_info["statements"] > 0:
                file_info["coverage_percent"] = round(
                    (file_info["covered"] / file_info["statements"]) * 100, 
                    1
                )
            
            total_statements += file_info["statements"]
            covered_statements += file_info["covered"]
            
            # Find untested functions
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_lines = set(range(node.lineno, node.end_lineno + 1))
                        missing_lines = set(analysis[3])
                        
                        # If all lines of function are missing, it's untested
                        if func_lines.issubset(missing_lines):
                            file_info["untested_functions"].append({
                                "name": node.name,
                                "line": node.lineno,
                                "lines": node.end_lineno - node.lineno
                            })
            except:
                pass
            
            results["files"].append(file_info)
        
        # Calculate overall coverage
        if total_statements > 0:
            overall_coverage = round((covered_statements / total_statements) * 100, 1)
        else:
            overall_coverage = 0
        
        results["summary"] = {
            "total_statements": total_statements,
            "covered_statements": covered_statements,
            "missing_statements": total_statements - covered_statements,
            "coverage_percent": overall_coverage,
            "total_files": len(results["files"]),
            "fully_covered_files": sum(1 for f in results["files"] if f["coverage_percent"] == 100),
            "untested_files": sum(1 for f in results["files"] if f["coverage_percent"] == 0)
        }
        
    except ImportError:
        results["error"] = "coverage.py not installed"
        results["install_command"] = "pip install coverage --break-system-packages"
    except Exception as e:
        results["error"] = str(e)
    
    return results


# ============================================================
# PHASE 4.2: REAL-TIME MONITORING RESOURCES
# ============================================================

@mcp.resource("monitor://cpu")
def cpu_usage_stream():
    """
    Get live CPU usage for running processes
    Returns current CPU metrics
    """
    if not PSUTIL_AVAILABLE:
        return {
            "error": "psutil not installed",
            "install_command": "pip install psutil --break-system-packages"
        }
    
    state = get_server_state()
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "cpu_count": psutil.cpu_count(),
            "cpu_per_core": psutil.cpu_percent(interval=0.1, percpu=True)
        },
        "server_process": {},
        "managed_processes": []
    }
    
    # Get current process (MCP server) CPU usage
    try:
        current_process = psutil.Process()
        results["server_process"] = {
            "pid": current_process.pid,
            "name": current_process.name(),
            "cpu_percent": current_process.cpu_percent(interval=0.1),
            "memory_mb": current_process.memory_info().rss / (1024 * 1024),
            "threads": current_process.num_threads()
        }
    except Exception as e:
        results["server_process"]["error"] = str(e)
    
    # Get CPU usage for managed processes
    for proc_id, proc_info in state.running_processes.items():
        try:
            pid = proc_info.get("pid")
            if pid:
                process = psutil.Process(pid)
                results["managed_processes"].append({
                    "process_id": proc_id,
                    "pid": pid,
                    "command": proc_info.get("command", []),
                    "cpu_percent": process.cpu_percent(interval=0.1),
                    "memory_mb": process.memory_info().rss / (1024 * 1024),
                    "status": process.status()
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # Top CPU consumers
    results["top_processes"] = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            info = proc.info
            if info['cpu_percent'] and info['cpu_percent'] > 1.0:  # Only processes using > 1% CPU
                results["top_processes"].append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu_percent": info['cpu_percent']
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # Sort by CPU usage
    results["top_processes"].sort(key=lambda x: x['cpu_percent'], reverse=True)
    results["top_processes"] = results["top_processes"][:10]  # Top 10
    
    return results


@mcp.resource("monitor://memory")
def memory_usage_stream():
    """
    Get live memory usage for system and processes
    """
    if not PSUTIL_AVAILABLE:
        return {
            "error": "psutil not installed",
            "install_command": "pip install psutil --break-system-packages"
        }
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "system": {},
        "server_process": {},
        "managed_processes": []
    }
    
    # System memory
    mem = psutil.virtual_memory()
    results["system"] = {
        "total_gb": round(mem.total / (1024**3), 2),
        "available_gb": round(mem.available / (1024**3), 2),
        "used_gb": round(mem.used / (1024**3), 2),
        "percent": mem.percent
    }
    
    # Swap memory
    swap = psutil.swap_memory()
    results["swap"] = {
        "total_gb": round(swap.total / (1024**3), 2),
        "used_gb": round(swap.used / (1024**3), 2),
        "percent": swap.percent
    }
    
    # Current process
    try:
        current_process = psutil.Process()
        mem_info = current_process.memory_info()
        results["server_process"] = {
            "pid": current_process.pid,
            "rss_mb": round(mem_info.rss / (1024**2), 2),
            "vms_mb": round(mem_info.vms / (1024**2), 2),
            "percent": round(current_process.memory_percent(), 2)
        }
    except Exception:
        pass
    
    # Managed processes
    state = get_server_state()
    for proc_id, proc_info in state.running_processes.items():
        try:
            pid = proc_info.get("pid")
            if pid:
                process = psutil.Process(pid)
                mem_info = process.memory_info()
                results["managed_processes"].append({
                    "process_id": proc_id,
                    "pid": pid,
                    "rss_mb": round(mem_info.rss / (1024**2), 2),
                    "percent": round(process.memory_percent(), 2)
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return results


@mcp.resource("monitor://file-changes")
def file_watcher():
    """
    Watch directory for file modifications
    Returns recently modified files
    """
    state = get_server_state()
    workspace = state.workspace_root or os.getcwd()
    
    results = {
        "workspace": workspace,
        "timestamp": datetime.now().isoformat(),
        "recent_changes": [],
        "watching": True
    }
    
    # Get files modified in last 60 seconds
    current_time = time.time()
    threshold = current_time - 60  # Last minute
    
    for root, dirs, files in os.walk(workspace):
        # Skip common directories
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
        
        for file in files:
            file_path = os.path.join(root, file)
            
            try:
                stat = os.stat(file_path)
                
                if stat.st_mtime > threshold:
                    results["recent_changes"].append({
                        "path": os.path.relpath(file_path, workspace),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "size_bytes": stat.st_size,
                        "seconds_ago": int(current_time - stat.st_mtime)
                    })
            except Exception:
                continue
    
    # Sort by most recent
    results["recent_changes"].sort(key=lambda x: x["seconds_ago"])
    
    results["summary"] = {
        "total_changes": len(results["recent_changes"]),
        "most_recent": results["recent_changes"][0] if results["recent_changes"] else None
    }
    
    return results


@mcp.resource("monitor://disk")
def disk_usage_monitor():
    """
    Monitor disk usage and I/O statistics
    """
    if not PSUTIL_AVAILABLE:
        return {
            "error": "psutil not installed",
            "install_command": "pip install psutil --break-system-packages"
        }
    
    state = get_server_state()
    workspace = state.workspace_root or os.getcwd()
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "partitions": [],
        "workspace": {}
    }
    
    # Get all disk partitions
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            results["partitions"].append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent
            })
        except Exception:
            continue
    
    # Workspace disk usage
    try:
        usage = psutil.disk_usage(workspace)
        results["workspace"] = {
            "path": workspace,
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent": usage.percent
        }
    except Exception:
        pass
    
    # Disk I/O statistics
    try:
        io_counters = psutil.disk_io_counters()
        results["io_stats"] = {
            "read_bytes": io_counters.read_bytes,
            "write_bytes": io_counters.write_bytes,
            "read_count": io_counters.read_count,
            "write_count": io_counters.write_count
        }
    except Exception:
        pass
    
    return results


# ============================================================
# RESOURCE REGISTRATION
# ============================================================

_PHASE4_RESOURCE_NAMES = [
    # Project Intelligence
    "project_complexity",
    "project_dependencies",
    "test_coverage_report",
    
    # Real-Time Monitoring
    "cpu_usage_stream",
    "memory_usage_stream",
    "file_watcher",
    "disk_usage_monitor",
]

for name in _PHASE4_RESOURCE_NAMES:
    get_server_state().register_resource(name)




@mcp.resource("metrics://tool-performance")
def tool_performance_stats():
    """
    Get performance statistics for all tools
    Returns execution times, success rates, error counts
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "metrics": _tool_metrics.get_stats()
    }


@mcp.resource("metrics://tool/{tool_name}")
def specific_tool_metrics(tool_name: str):
    """Get metrics for a specific tool"""
    return {
        "timestamp": datetime.now().isoformat(),
        **_tool_metrics.get_stats(tool_name)
    }

@mcp.resource("cache://stats")
def cache_statistics():
    """Get cache performance statistics"""
    return {
        "timestamp": datetime.now().isoformat(),
        **_resource_cache.stats()
    }




_PHASE5_RESOURCE_NAMES = [
    # Observability
    "tool_performance_stats",
    
    # Caching
    "cache_statistics",
    "specific_tool_metrics",
    "cache_statistics"
]

for name in _PHASE5_RESOURCE_NAMES:
    get_server_state().register_resource(name)

