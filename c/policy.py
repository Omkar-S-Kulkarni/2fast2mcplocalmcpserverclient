# policy.py


class PolicyDecision:
    ALLOW = "allow"
    DENY = "deny"
    DRY_RUN = "dry_run"


class PolicyEngine:
    """
    Central policy engine for terminal MCP client + agent

    Responsibilities:
    - Enforce safety rules for terminal operations
    - Block dangerous commands
    - Support dry-run mode
    - Act as a single decision point
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        
        # Dangerous commands that should always be blocked
        self.blocked_commands = {
            "rm -rf /",
            "shutdown",
            "reboot",
            "mkfs",
            "dd if=/dev/zero",
            "chmod 777 /",
            "chown -R",
        }
        
        # Dangerous patterns in commands
        self.dangerous_patterns = [
            "rm -rf",
            "/dev/sda",
            "/dev/null",
            ">/dev/sda",
        ]

    def evaluate(self, action_type: str, payload: dict) -> str:
        """
        Decide what to do with an action

        action_type:
            - "resource"
            - "tool"
            - "prompt"

        payload:
            Depends on action type
        """

        # =====================================================
        # ❌ HARD DENY RULES (NON-NEGOTIABLE)
        # =====================================================

        # Block dangerous terminal commands
        if action_type == "tool":
            tool_name = payload.get("name")

            # Check run_command and interactive_command for dangerous patterns
            if tool_name in {"run_command", "interactive_command"}:
                args = payload.get("arguments", {})
                command = args.get("command", "")
                
                # Check for blocked commands
                for blocked in self.blocked_commands:
                    if blocked in command.lower():
                        return PolicyDecision.DENY
                
                # Check for dangerous patterns
                for pattern in self.dangerous_patterns:
                    if pattern in command.lower():
                        return PolicyDecision.DENY

            # Block git operations that force push or delete
            if tool_name == "git_commit":
                args = payload.get("arguments", {})
                message = args.get("message", "")
                if "--force" in message or "-f" in message:
                    return PolicyDecision.DENY

        # Never allow writing outside workspace
        if action_type == "tool" and payload.get("name") == "write_file":
            args = payload.get("arguments", {})
            path = args.get("path", "")

            # Block absolute paths outside workspace
            if path.startswith("/") and not path.startswith("/home"):
                return PolicyDecision.DENY
            
            # Block parent directory traversal
            if ".." in path:
                return PolicyDecision.DENY
            
            # Block writing to system directories
            if any(path.startswith(p) for p in ["/etc/", "/sys/", "/proc/", "/boot/"]):
                return PolicyDecision.DENY

        # Block process killing of system processes
        if action_type == "tool" and payload.get("name") == "kill_process":
            args = payload.get("arguments", {})
            process_id = args.get("process_id", "")
            
            # Block if trying to kill PID 1 or other critical processes
            # (actual PID checking would need server-side validation)
            if not process_id or process_id == "1":
                return PolicyDecision.DENY

        # =====================================================
        # 🧪 DRY-RUN MODE
        # =====================================================

        # Dry-run applies ONLY to mutating actions
        if self.dry_run:
            if action_type == "tool":
                tool_name = payload.get("name")
                
                # These tools modify state
                mutating_tools = {
                    "run_command",
                    "interactive_command",
                    "write_file",
                    "replace_in_file",
                    "kill_process",
                    "git_commit",
                }
                
                if tool_name in mutating_tools:
                    return PolicyDecision.DRY_RUN

        # =====================================================
        # ⚠️ SOFT SAFETY RULES (ALLOW BUT OBSERVE)
        # =====================================================

        # Large file operations → allow, but could add size checks
        if action_type == "tool" and payload.get("name") == "read_file":
            args = payload.get("arguments", {})
            path = args.get("path", "")
            
            # Could add size checks here if needed
            # For now, rely on server-side truncation
            pass

        # Docker operations → allow, but user should be aware
        if action_type == "tool" and payload.get("name") == "docker_ps":
            # Could add restrictions here
            pass

        # =====================================================
        # ✅ DEFAULT ALLOW
        # =====================================================

        return PolicyDecision.ALLOW
