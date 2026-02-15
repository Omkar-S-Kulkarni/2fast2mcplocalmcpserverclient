# test_advanced.py
"""
Test script for advanced agent features
"""

import asyncio
from client import MCPAppClient
from agent import TerminalAgent


async def run_all_tests():
    """Run all tests in a single client session"""
    
    async with MCPAppClient() as client:
        agent = TerminalAgent(client, debug_mode=True)
        
        print("=" * 60)
        print("TEST 1: Multi-step Planning")
        print("=" * 60)
        
        # Complex task requiring multiple steps
        response1 = await agent.answer(
            "Find all Python files in the current directory, "
            "check which ones import 'os', and create a report"
        )
        
        print("\n" + "=" * 60)
        print("RESPONSE:")
        print(response1)
        print("=" * 60)
        
        # Wait a bit between tests
        await asyncio.sleep(2)
        
        print("\n\n" + "=" * 60)
        print("TEST 2: Self-Correction")
        print("=" * 60)
        
        # Task likely to fail first time (file doesn't exist)
        response2 = await agent.answer(
            "Read the file 'nonexistent.txt' and if it doesn't exist, "
            "create it with sample content"
        )
        
        print("\n" + "=" * 60)
        print("RESPONSE:")
        print(response2)
        print("=" * 60)
        
        # Wait a bit between tests
        await asyncio.sleep(2)
        
        print("\n\n" + "=" * 60)
        print("TEST 3: Context Management")
        print("=" * 60)
        
        # Multiple related queries
        await agent.answer("List files in current directory")
        await asyncio.sleep(1)
        
        await agent.answer("What is the system OS?")
        await asyncio.sleep(1)
        
        await agent.answer("What files did I just list?")  # Should use context
        
        # Check session state
        print("\n" + "=" * 60)
        print("SESSION STATE:")
        print(f"Context items: {len(agent.session_manager.context_items)}")
        
        # Save checkpoint
        checkpoint = agent.session_manager.save_checkpoint("test_session")
        print(f"Checkpoint saved: {checkpoint}")
        print("=" * 60)


if __name__ == "__main__":
    print("Testing Advanced Agent Features\n")
    asyncio.run(run_all_tests())