from __future__ import annotations

import os
import socket
import platform
from typing import Dict, Any

from mcp_instance import mcp
from state import get_server_state

from helper import (
    execute_command,
    resolve_workspace_path,
    validate_workspace_path,
    truncate_output,
    kill_process as kill_registered_process,
)
def _run_tool(name, logic):
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
# TERMINAL
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


# ============================================================
# FILESYSTEM
# ============================================================

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
        # DO NOT overwrite 'path'
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


# ============================================================
# PROCESS
# ============================================================

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


# ============================================================
# ENVIRONMENT
# ============================================================

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


# ============================================================
# GIT
# ============================================================

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


# ============================================================
# LOGS
# ============================================================

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


# ============================================================
# NETWORK
# ============================================================

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


# ============================================================
# DOCKER
# ============================================================

@mcp.tool
def docker_ps() -> Dict[str, Any]:
    def logic():
        return execute_command("docker ps")

    return _run_tool("docker_ps", logic)






_TOOL_NAMES = [
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
]

for name in _TOOL_NAMES:
    get_server_state().register_tool(name)




@mcp.tool
def create_report_from_results(title: str, results_summary: str, output_path: str = "report.txt") -> Dict[str, Any]:
    """
    Create a formatted report from task execution results
    
    Args:
        title: Report title
        results_summary: Summary of what was found/done
        output_path: Where to save the report
    """
    def logic():
        import time
        from datetime import datetime
        
        file_path = resolve_workspace_path(output_path)
        
        if not validate_workspace_path(file_path):
            return {"success": False, "error": "Invalid path"}
        
        # Build formatted report
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


# Register the new tool
_TOOL_NAMES.append("create_report_from_results")
get_server_state().register_tool("create_report_from_results")

