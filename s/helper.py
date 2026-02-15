from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import threading
import time
import uuid
from typing import Optional, Tuple, Dict, Any, List

from state import get_server_state


# ============================================================
# CONFIG / DEFAULTS
# ============================================================

DEFAULT_TIMEOUT = 300
MAX_OUTPUT_SIZE = 10000  # characters


# ============================================================
# PATH & WORKSPACE SAFETY
# ============================================================

def get_workspace_root() -> str:
    state = get_server_state()
    if not state.workspace_root:
        return os.getcwd()
    return os.path.abspath(state.workspace_root)


def resolve_workspace_path(path: str) -> str:
    """
    Resolve path relative to workspace root.
    """
    root = get_workspace_root()
    abs_path = os.path.abspath(os.path.join(root, path))
    return abs_path


def validate_workspace_path(path: str) -> bool:
    """
    Ensure path stays inside workspace.
    """
    root = get_workspace_root()
    path = os.path.abspath(path)
    return os.path.commonpath([root]) == os.path.commonpath([root, path])


# ============================================================
# COMMAND VALIDATION
# ============================================================

def normalize_command(command: str | List[str]) -> List[str]:
    if isinstance(command, str):
        return shlex.split(command)
    return command


def validate_command(command: List[str]) -> Tuple[bool, str]:
    """
    Check against allowed command whitelist.
    """
    state = get_server_state()

    if not command:
        return False, "Empty command"

    base_cmd = command[0]

    # If whitelist exists, enforce it
    if state.allowed_commands:
        if base_cmd not in state.allowed_commands:
            return False, f"Command not allowed: {base_cmd}"

    # Basic dangerous patterns
    dangerous = {"rm", "shutdown", "reboot", "mkfs", "dd"}
    if base_cmd in dangerous:
        return False, f"Dangerous command blocked: {base_cmd}"

    return True, ""


# ============================================================
# OUTPUT HANDLING
# ============================================================

def truncate_output(text: str, max_size: int = MAX_OUTPUT_SIZE) -> str:
    if len(text) <= max_size:
        return text
    return text[:max_size] + "\n... (truncated)"


# ============================================================
# PROCESS MANAGEMENT
# ============================================================

def register_process(pid: int, command: List[str]) -> str:
    """
    Register running process in server state.
    """
    state = get_server_state()
    process_id = str(uuid.uuid4())

    state.register_process(process_id, {
        "pid": pid,
        "command": command,
        "start_time": time.time(),
    })

    return process_id


def remove_process(process_id: str) -> None:
    state = get_server_state()
    state.remove_process(process_id)


def kill_process(process_id: str) -> bool:
    state = get_server_state()
    proc = state.running_processes.get(process_id)

    if not proc:
        return False

    try:
        os.kill(proc["pid"], 9)
        state.remove_process(process_id)
        return True
    except Exception:
        return False


# ============================================================
# COMMAND EXECUTION CORE
# ============================================================

def execute_command(
    command: str | List[str],
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,

) -> Dict[str, Any]:
    """
    Core execution engine used by all terminal tools.
    """

    state = get_server_state()
    print(f"[DEBUG] state.max_command_timeout = {state.max_command_timeout}")


    cmd_list = normalize_command(command)

    valid, reason = validate_command(cmd_list)
    if not valid:
        return {
            "success": False,
            "error": reason,
            "output": "",
        }

    cwd = resolve_workspace_path(cwd or ".")
    if not validate_workspace_path(cwd):
        return {
            "success": False,
            "error": "Invalid working directory",
            "output": "",
        }

    # -------- TIMEOUT FIX --------
    if timeout is None:
        timeout = state.max_command_timeout

    if timeout is None or timeout <= 0:
        timeout = DEFAULT_TIMEOUT
    # -----------------------------

    try:
        process = subprocess.Popen(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
            text=True,
        )



        process_id = register_process(process.pid, cmd_list)

        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            remove_process(process_id)

            output = (stdout or "") + (stderr or "")
            output = truncate_output(output)

            return {
                "success": False,
                "error": f"Command timed out after {timeout}s",
                "output": output,
            }


        remove_process(process_id)

        output = (stdout or "") + (stderr or "")
        output = truncate_output(output)

        success = process.returncode == 0

        # Log history
        state.log_global_command(
            command=" ".join(cmd_list),
            status="success" if success else "failed",
            output=output,
        )

        return {
            "success": success,
            "return_code": process.returncode,
            "output": output,
        }

    except Exception as e:
        state.log_global_command(
            command=" ".join(cmd_list),
            status="failed",
            output=str(e),
        )
        return {
            "success": False,
            "error": str(e),
            "output": "",
        }


# ============================================================
# PYTHON EXECUTION HELPERS
# ============================================================

def run_python_file(file_path: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Execute a Python file safely.
    """
    path = resolve_workspace_path(file_path)

    if not validate_workspace_path(path):
        return {"success": False, "error": "Invalid path"}

    import sys
    command = [sys.executable, path]

    if args:
        command.extend(args)

    return execute_command(command)


def run_python_code(code: str) -> Dict[str, Any]:
    """
    Execute inline Python safely using a temp file.
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        dir=get_workspace_root(),
    ) as f:
        f.write(code)
        temp_path = f.name

    result = run_python_file(temp_path)

    try:
        os.remove(temp_path)
    except Exception:
        pass

    return result


# ============================================================
# SHELL SCRIPT HELPERS
# ============================================================

def run_shell_script(script_path: str) -> Dict[str, Any]:
    path = resolve_workspace_path(script_path)

    if not validate_workspace_path(path):
        return {"success": False, "error": "Invalid path"}

    if os.name == "nt":
        command = ["cmd", "/c", path]
    else:
        command = ["bash", path]

    return execute_command(command)


# ============================================================
# HISTORY HELPERS
# ============================================================

def get_command_history(limit: int = 50) -> List[Dict[str, Any]]:
    state = get_server_state()
    return state.global_command_history[-limit:]


def clear_command_history() -> None:
    state = get_server_state()
    state.global_command_history.clear()


# ============================================================
# SYSTEM INFO FOR TERMINAL TOOLS
# ============================================================

def get_last_command_output() -> Optional[str]:
    state = get_server_state()
    if not state.global_command_history:
        return None
    return state.global_command_history[-1].get("output")
