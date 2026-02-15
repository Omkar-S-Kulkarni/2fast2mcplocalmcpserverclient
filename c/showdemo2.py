# run.py
"""
Minimal Terminal MCP Client (Production Mode)

Commands:
    chat   -> interactive chat mode (tool-aware)
    exit   -> quit

Any normal input is treated as a tool-aware query.
All requests go through agent.answer() so the model
has access to:
    - Tools
    - Resources
    - Prompts
    - Memory
    - System context
"""

import asyncio
import sys

from client import MCPAppClient
from agent_verbose import TerminalAgent


async def main():
    print("=" * 60)
    print("Terminal MCP Client (Production Mode)")
    print("=" * 60)

    async with MCPAppClient() as mcp_client:
        print("✓ Connected to MCP server")
        print(f"Tools     : {len(mcp_client._tools)}")
        print(f"Resources : {len(mcp_client._resources)}")
        print(f"Prompts   : {len(mcp_client._prompts)}")
        print()

        agent = TerminalAgent(mcp_client)

        print("Commands:")
        print("  chat  -> interactive chat mode")
        print("  exit  -> quit")
        print("-" * 60)

        while True:
            try:
                user_input = input("🖥️  > ").strip()

                # Exit
                if user_input.lower() in ["exit", "quit"]:
                    print("👋 Closing client...")
                    break

                # =========================
                # Interactive Chat Mode
                # =========================
                if user_input.lower() == "chat":
                    print("\n💬 Chat mode (tools enabled)")
                    print("Type 'exit' to enter\n")

                    whil True:
                        msg = input("💬 > ").strip()

                        if msg.lower() in ["exit", "quit"]:
                            print("Leaving chat mode...\n")
                            break

                        if not msg:
                            continu

                        try:
                            print("\n🤖 Thinking...\n")
                            response = await agent.answer(msg)
                            print(response)
                            print()
                        except Exception as e:
                            print(f"Error: {e}")

                    continue

                # =========================
                # Default Mode
                # Every input → tool-aware agent
                # =========================
                if not user_input:
                    continue

                print("\n🤖 Processing...\n")

                try:
                    response = await agent.answer(user_input)
                    print(response)
                    print()
                except Exception as e:
                    print(f"Error: {e}\n")

            except :
                print("\n\n👋 Interrupted. Closing client...")
                break
            except EOFError:
                print("\n\n👋 EOF received. Closing client...")
                break


# Entry Point
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
     Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)