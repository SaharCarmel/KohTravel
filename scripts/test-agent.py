#!/usr/bin/env python3
"""
Test script for agent infrastructure
"""
import asyncio
import sys
import os
from uuid import uuid4

# Add integrations to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../integrations/kohtravel/src"))

from services.agent_client import AgentClient


async def test_agent_health():
    """Test agent service health"""
    print("🏥 Testing agent health...")
    
    async with AgentClient() as client:
        health = await client.health_check()
        
        if health.get("status") == "healthy":
            print("✅ Agent service is healthy")
            return True
        else:
            print(f"❌ Agent service unhealthy: {health}")
            return False


async def test_simple_chat():
    """Test simple chat interaction"""
    print("\n💬 Testing simple chat...")
    
    session_id = str(uuid4())
    user_id = "test-user-123"
    
    async with AgentClient() as client:
        # Send a simple message
        response = await client.send_message(
            session_id=session_id,
            message="Hello, I'm testing the agent. Can you help me?",
            user_id=user_id
        )
        
        print(f"Agent response: {response.get('message', 'No response')}")
        
        if response.get("status") == "success":
            print("✅ Simple chat test passed")
            return True
        else:
            print(f"❌ Simple chat test failed: {response}")
            return False


async def test_streaming_chat():
    """Test streaming chat"""
    print("\n🌊 Testing streaming chat...")
    
    session_id = str(uuid4())
    user_id = "test-user-123"
    
    async with AgentClient() as client:
        print("Streaming response:")
        content_parts = []
        
        async for chunk in client.stream_message(
            session_id=session_id,
            message="Tell me about travel document organization in a few sentences.",
            user_id=user_id
        ):
            if chunk.get("type") == "content":
                content = chunk.get("data", {}).get("content", "")
                print(content, end="", flush=True)
                content_parts.append(content)
            elif chunk.get("type") == "error":
                print(f"\n❌ Streaming error: {chunk}")
                return False
        
        print("\n")  # New line after streaming
        
        if content_parts:
            print("✅ Streaming chat test passed")
            return True
        else:
            print("❌ No content received in streaming")
            return False


async def test_tools_list():
    """Test tools listing"""
    print("\n🔧 Testing tools list...")
    
    async with AgentClient() as client:
        tools = await client.list_tools()
        
        if "tools" in tools and len(tools["tools"]) > 0:
            print(f"✅ Found {len(tools['tools'])} tools:")
            for tool in tools["tools"]:
                print(f"  - {tool.get('name')}: {tool.get('description')}")
            return True
        else:
            print(f"❌ No tools found: {tools}")
            return False


async def test_document_search():
    """Test document search functionality"""
    print("\n🔍 Testing external tools integration...")
    
    session_id = str(uuid4())
    user_id = "test-user-123"
    
    async with AgentClient() as client:
        response = await client.send_message(
            session_id=session_id,
            message="Can you help me understand what travel documents I have? Give me a summary.",
            user_id=user_id,
            project="kohtravel"  # This will load external KohTravel tools
        )
        
        print(f"External tool response: {response.get('message', 'No response')[:200]}...")
        
        if response.get("status") == "success":
            print("✅ External tools integration test completed")
            return True
        else:
            print(f"❌ External tools test failed: {response}")
            return False


async def run_all_tests():
    """Run all tests"""
    print("🧪 Running Agent Infrastructure Tests\n")
    
    tests = [
        ("Health Check", test_agent_health),
        ("Simple Chat", test_simple_chat), 
        ("Streaming Chat", test_streaming_chat),
        ("Tools List", test_tools_list),
        ("External Tools Integration", test_document_search)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if await test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} threw exception: {e}")
            failed += 1
    
    print(f"\n📊 Test Results:")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    return failed == 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test agent infrastructure")
    parser.add_argument("--test", choices=["health", "chat", "stream", "tools", "search"], 
                       help="Run specific test")
    args = parser.parse_args()
    
    if args.test == "health":
        success = asyncio.run(test_agent_health())
    elif args.test == "chat":
        success = asyncio.run(test_simple_chat())
    elif args.test == "stream":
        success = asyncio.run(test_streaming_chat())
    elif args.test == "tools":
        success = asyncio.run(test_tools_list())
    elif args.test == "search":
        success = asyncio.run(test_document_search())
    else:
        success = asyncio.run(run_all_tests())
    
    sys.exit(0 if success else 1)