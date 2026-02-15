"""
MAIN MCP SERVER ENTRY POINT
Offline AI Workspace MCP Server
"""

# =========================
# Imports
# =========================

import os
from state import get_server_state

# IMPORTANT:
# MCP must be imported BEFORE tools/resources/prompts
from mcp_instance import mcp


# =========================
# Server Metadata
# =========================

SERVER_NAME = "mcp-offline-ai-workspace"
SERVER_VERSION = "1.0.0"


# =========================
# Initialize Server State
# =========================

server_state = get_server_state()


# =========================
# Register MCP Components
# (Imports trigger decorators)
# =========================

# Order does not matter, but all must be imported
import resources
import tools
import prompts


# =========================
# Optional: Print Registered Items (Debug)
# =========================

def print_registration_summary():
    print("\n=== MCP REGISTRATION SUMMARY ===")
    print("Server State:", server_state.lifecycle)
    print("Registered Tools:", server_state.registered_tools)
    print("Registered Resources:", server_state.registered_resources)
    print("Registered Prompts:", server_state.registered_prompts)
    print("================================\n")


# =========================
# Server Lifecycle
# =========================

def main():
    server_state.mark_starting()

    try:
        server_state.mark_running()

        print("SERVER MCP ID:", id(mcp))
        print_registration_summary()

        # Start MCP server
        mcp.run()

    except Exception as e:
        server_state.mark_crashed(str(e))
        raise

    finally:
        server_state.mark_stopped()


# =========================
# Entry Point
# =========================

if __name__ == "__main__":
    main()
