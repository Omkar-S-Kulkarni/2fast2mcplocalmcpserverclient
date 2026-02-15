from __future__ import annotations

import threading
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Set


# ============================================================
# SERVER LIFECYCLE ENUMS
# ============================================================

class ServerLifecycle(Enum):
    NOT_STARTED = "not_started"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    CRASHED = "crashed"


class ServerHealth(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"


# ============================================================
# REQUEST STATE
# ============================================================

@dataclass
class RequestState:
    request_id: str
    session_id: str
    tool_name: Optional[str]
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"  # running | success | failed | cancelled
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finish(self, status: str, error: Optional[str] = None) -> None:
        self.status = status
        self.error = error
        self.end_time = time.time()

    def duration_ms(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000


# ============================================================
# SESSION STATE
# ============================================================

@dataclass
class SessionState:
    session_id: str
    created_at: float
    last_active_at: float

    # Workspace
    workspace_root: Optional[str] = None
    active_project: Optional[str] = None

    # Execution tracking
    active_requests: Set[str] = field(default_factory=set)
    completed_requests: List[str] = field(default_factory=list)

    # Tool usage stats
    tools_called: Dict[str, int] = field(default_factory=dict)

    # Command history (per session)
    command_history: List[Dict[str, Any]] = field(default_factory=list)

    # Running services (FastAPI, Streamlit, etc.)
    active_services: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Cached resources for efficiency
    resource_cache: Dict[str, Any] = field(default_factory=dict)

    # Session metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        self.last_active_at = time.time()

    def log_command(self, command: str, status: str, output: Optional[str] = None) -> None:
        self.command_history.append({
            "time": time.time(),
            "command": command,
            "status": status,
            "output": output[:1000] if output else None,
        })
        # keep last 100 commands only
        if len(self.command_history) > 100:
            self.command_history.pop(0)


# ============================================================
# COMPLETE SERVER STATE (SINGLE OBJECT)
# ============================================================

class MCPServerState:
    """
    COMPLETE MCP SERVER STATE
    --------------------------------
    Central runtime state for tools, resources, execution,
    services, and diagnostics.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

        # -----------------------------
        # Lifecycle & health
        # -----------------------------
        self.lifecycle: ServerLifecycle = ServerLifecycle.NOT_STARTED
        self.health: ServerHealth = ServerHealth.HEALTHY
        self.started_at: Optional[float] = None
        self.stopped_at: Optional[float] = None
        self.last_error: Optional[str] = None

        # -----------------------------
        # Capability registry
        # -----------------------------
        self.registered_tools: Set[str] = set()
        self.registered_resources: Set[str] = set()
        self.registered_prompts: Set[str] = set()

        # -----------------------------
        # Session & request tracking
        # -----------------------------
        self.sessions: Dict[str, SessionState] = {}
        self.requests: Dict[str, RequestState] = {}

        # -----------------------------
        # Global execution tracking
        # -----------------------------
        self.active_session_count: int = 0
        self.active_request_count: int = 0
        self.max_parallel_requests_seen: int = 0

        # Global command history
        self.global_command_history: List[Dict[str, Any]] = []

        # Running processes started by server
        self.running_processes: Dict[str, Dict[str, Any]] = {}

        # -----------------------------
        # Resource cache (global)
        # -----------------------------
        self.global_resource_cache: Dict[str, Any] = {}
        self.resource_cache_time: Dict[str, float] = {}

        # -----------------------------
        # Security / limits
        # -----------------------------
        self.allowed_commands: Set[str] = set()
        self.restricted_paths: Set[str] = set()
        self.workspace_root: Optional[str] = None
        self.max_command_timeout: int = 600
        self.max_file_size_mb: int = 50

        # -----------------------------
        # Error tracking
        # -----------------------------
        self.total_errors: int = 0
        self.error_log: List[str] = []

        # -----------------------------
        # Shutdown / crash flags
        # -----------------------------
        self.shutdown_requested: bool = False
        self.crashed: bool = False

    # ========================================================
    # LIFECYCLE CONTROL
    # ========================================================

    def mark_starting(self) -> None:
        with self._lock:
            self.lifecycle = ServerLifecycle.STARTING

    def mark_running(self) -> None:
        with self._lock:
            self.lifecycle = ServerLifecycle.RUNNING
            self.started_at = time.time()

    def mark_degraded(self, reason: str) -> None:
        with self._lock:
            self.lifecycle = ServerLifecycle.DEGRADED
            self.health = ServerHealth.WARNING
            self.last_error = reason
            self.error_log.append(reason)

    def mark_stopping(self) -> None:
        with self._lock:
            self.lifecycle = ServerLifecycle.STOPPING
            self.shutdown_requested = True

    def mark_stopped(self) -> None:
        with self._lock:
            self.lifecycle = ServerLifecycle.STOPPED
            self.stopped_at = time.time()

    def mark_crashed(self, reason: str) -> None:
        with self._lock:
            self.lifecycle = ServerLifecycle.CRASHED
            self.health = ServerHealth.UNHEALTHY
            self.crashed = True
            self.last_error = reason
            self.error_log.append(reason)

    # ========================================================
    # REGISTRATION
    # ========================================================

    def register_tool(self, name: str) -> None:
        with self._lock:
            self.registered_tools.add(name)

    def register_resource(self, name: str) -> None:
        with self._lock:
            self.registered_resources.add(name)

    def register_prompt(self, name: str) -> None:
        with self._lock:
            self.registered_prompts.add(name)

    # ========================================================
    # SESSION MANAGEMENT
    # ========================================================

    def create_session(self) -> SessionState:
        with self._lock:
            session_id = str(uuid.uuid4())
            now = time.time()

            session = SessionState(
                session_id=session_id,
                created_at=now,
                last_active_at=now,
                workspace_root=self.workspace_root,
            )

            self.sessions[session_id] = session
            self.active_session_count += 1
            return session

    def close_session(self, session_id: str) -> None:
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                self.active_session_count -= 1

    # ========================================================
    # REQUEST MANAGEMENT
    # ========================================================

    def start_request(self, session_id: str, tool_name: Optional[str]) -> RequestState:
        with self._lock:
            request_id = str(uuid.uuid4())
            now = time.time()

            req = RequestState(
                request_id=request_id,
                session_id=session_id,
                tool_name=tool_name,
                start_time=now,
            )

            self.requests[request_id] = req
            self.active_request_count += 1
            self.max_parallel_requests_seen = max(
                self.max_parallel_requests_seen,
                self.active_request_count,
            )

            session = self.sessions.get(session_id)
            if session:
                session.active_requests.add(request_id)
                if tool_name:
                    session.tools_called[tool_name] = session.tools_called.get(tool_name, 0) + 1
                session.touch()

            return req

    def finish_request(self, request_id: str, status: str, error: Optional[str] = None) -> None:
        with self._lock:
            req = self.requests.get(request_id)
            if not req:
                return

            req.finish(status=status, error=error)
            self.active_request_count -= 1

            session = self.sessions.get(req.session_id)
            if session:
                session.active_requests.discard(request_id)
                session.completed_requests.append(request_id)
                session.touch()

            if status != "success":
                self.total_errors += 1
                if error:
                    self.error_log.append(error)

    # ========================================================
    # COMMAND / PROCESS TRACKING
    # ========================================================

    def log_global_command(self, command: str, status: str, output: Optional[str] = None) -> None:
        entry = {
            "time": time.time(),
            "command": command,
            "status": status,
            "output": output[:1000] if output else None,
        }
        with self._lock:
            self.global_command_history.append(entry)
            if len(self.global_command_history) > 500:
                self.global_command_history.pop(0)

    def register_process(self, pid: str, info: Dict[str, Any]) -> None:
        with self._lock:
            self.running_processes[pid] = info

    def remove_process(self, pid: str) -> None:
        with self._lock:
            self.running_processes.pop(pid, None)

    # ========================================================
    # RESOURCE CACHE
    # ========================================================

    def cache_resource(self, name: str, value: Any) -> None:
        with self._lock:
            self.global_resource_cache[name] = value
            self.resource_cache_time[name] = time.time()

    def get_cached_resource(self, name: str, max_age: int = 30) -> Optional[Any]:
        with self._lock:
            if name not in self.global_resource_cache:
                return None
            if time.time() - self.resource_cache_time.get(name, 0) > max_age:
                return None
            return self.global_resource_cache[name]

    # ========================================================
    # DIAGNOSTICS
    # ========================================================

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "lifecycle": self.lifecycle.value,
                "health": self.health.value,
                "started_at": self.started_at,
                "uptime": self.uptime_seconds(),
                "active_sessions": self.active_session_count,
                "active_requests": self.active_request_count,
                "registered_tools": sorted(self.registered_tools),
                "registered_resources": sorted(self.registered_resources),
                "registered_prompts": sorted(self.registered_prompts),
                "running_processes": len(self.running_processes),
                "total_errors": self.total_errors,
                "crashed": self.crashed,
                "shutdown_requested": self.shutdown_requested,
            }

    def uptime_seconds(self) -> Optional[float]:
        if not self.started_at:
            return None
        return time.time() - self.started_at


# ============================================================
# SINGLETON ACCESSOR
# ============================================================

_server_state: Optional[MCPServerState] = None
_state_lock = threading.Lock()


def get_server_state() -> MCPServerState:
    global _server_state
    if _server_state is None:
        with _state_lock:
            if _server_state is None:
                _server_state = MCPServerState()
    return _server_state
