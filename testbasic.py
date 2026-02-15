# test_basic.py
"""
Test basic tool calling to verify MCP response extraction
"""

import asyncio
from c.client import MCPAppClient


async def test_basic_tool():
    """Test basic tool calling"""
    print("=" * 60)
    print("Testing Basic Tool Call")
    print("=" * 60)
    
    async with MCPAppClient() as client:
        print(f"✓ Connected to MCP server")
        print(f"Available tools: {[t.name for t in client._tools]}")
        
        # Test 1: list_directory
        print("\n[TEST 1] Calling list_directory...")
        try:
            raw_result = await client.call_tool(
                server="terminal",
                name="list_directory",
                arguments={"path": "."}
            )
            
            print(f"Raw result type: {type(raw_result)}")
            print(f"Raw result: {raw_result}")
            
            # Extract using the same logic as agentic_loop
            if hasattr(raw_result, 'content'):
                content = raw_result.content
                print(f"Content type: {type(content)}")
                print(f"Content: {content}")
                
                if isinstance(content, list) and len(content) > 0:
                    first_item = content[0]
                    print(f"First item type: {type(first_item)}")
                    
                    if hasattr(first_item, 'text'):
                        text = first_item.text
                        print(f"Text: {text}")
                        
                        import json
                        try:
                            parsed = json.loads(text)
                            print(f"✓ Parsed result: {parsed}")
                        except Exception as e:
                            print(f"✗ JSON parse failed: {e}")
                    else:
                        print(f"✗ No 'text' attribute on first item")
                else:
                    print(f"✗ Content is not a list or is empty")
            else:
                print(f"✗ No 'content' attribute on result")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 2: system_info
        print("\n\n[TEST 2] Calling system_info...")
        try:
            raw_result = await client.call_tool(
                server="terminal",
                name="system_info",
                arguments={}
            )
            
            print(f"Raw result type: {type(raw_result)}")
            
            if hasattr(raw_result, 'content'):
                content = raw_result.content
                if isinstance(content, list) and len(content) > 0:
                    first_item = content[0]
                    if hasattr(first_item, 'text'):
                        import json
                        parsed = json.loads(first_item.text)
                        print(f"✓ System info: {parsed}")
                        
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_basic_tool())