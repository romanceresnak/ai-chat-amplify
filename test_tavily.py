#!/usr/bin/env python3
"""
Test Tavily integration locally
"""
import os
import sys

# Add the orchestrator directory to the path
sys.path.append('application/backend/orchestrator')

# Load environment variables
import env_loader
env_loader.load_env_file()

# Test Tavily import
try:
    from tavily import TavilyClient
    print("✅ Tavily import successful")
    
    # Test API key
    api_key = os.environ.get('TAVILY_API_KEY', '')
    if api_key and api_key != 'tvly-xxxxx':
        print(f"✅ API key configured: {api_key[:10]}...")
        
        # Test search
        client = TavilyClient(api_key=api_key)
        result = client.search(
            query="latest AI news today",
            max_results=3,
            include_answer=True
        )
        
        print(f"✅ Search successful! Found {len(result.get('results', []))} results")
        if result.get('answer'):
            print(f"📍 Answer: {result['answer'][:100]}...")
        
        for idx, item in enumerate(result.get('results', [])[:2]):
            print(f"\n{idx + 1}. {item.get('title', 'No title')}")
            print(f"   URL: {item.get('url', '')}")
            print(f"   Summary: {item.get('content', '')[:100]}...")
    else:
        print("❌ No valid API key found")
        
except ImportError as e:
    print(f"❌ Tavily import failed: {e}")
except Exception as e:
    print(f"❌ Error testing Tavily: {e}")

# Test simple orchestrator
try:
    from simple_langchain_orchestrator import SimpleOrchestrator
    
    print("\n🔄 Testing Simple Orchestrator...")
    orchestrator = SimpleOrchestrator()
    
    # Test web search detection
    test_queries = [
        "latest AI news",
        "current weather in London", 
        "what is machine learning",
        "create a presentation about AI"
    ]
    
    for query in test_queries:
        is_web_search = orchestrator._is_web_search_query(query)
        is_presentation = orchestrator._is_presentation_request(query)
        print(f"Query: '{query}' -> Web Search: {is_web_search}, Presentation: {is_presentation}")
    
    print("✅ Simple Orchestrator working correctly")
    
except Exception as e:
    print(f"❌ Error testing Simple Orchestrator: {e}")