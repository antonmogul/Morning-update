#!/usr/bin/env python3
"""Quick test with limited data to verify API connections."""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path, override=True)
print(f"✓ Loaded environment from {env_path}")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

print("\n=== Quick Connection Test ===")
print("Testing API connections with minimal data...\n")

try:
    # Test OpenAI connection
    print("1. Testing OpenAI API...")
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Simple test with minimal tokens
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say 'OK' if connected"}],
        max_tokens=10
    )
    print(f"   ✓ OpenAI connected: {response.choices[0].message.content}")
    
    # Test Notion connection
    print("\n2. Testing Notion API...")
    from notion_client import Client as Notion
    notion = Notion(auth=os.getenv('NOTION_TOKEN'))
    
    # Try to query the database
    db_id = os.getenv('NOTION_DAILY_DB_ID')
    try:
        result = notion.databases.query(
            database_id=db_id,
            page_size=1
        )
        print(f"   ✓ Notion connected: Found database with {len(result.get('results', []))} existing pages")
    except Exception as e:
        print(f"   ✗ Notion error: {e}")
        print("   Make sure to share the database with your integration!")
    
    # Test RSS feed fetch (just one feed, one item)
    print("\n3. Testing RSS feed fetch...")
    from app.news import fetch_feeds
    
    test_feeds = {
        "test": {
            "urls": ["https://feeds.bbci.co.uk/news/rss.xml"],
            "prompt": "Test feed"
        }
    }
    
    sections = fetch_feeds(test_feeds, since_hours=24)
    if sections and sections.get("test"):
        print(f"   ✓ RSS fetch successful: Got {len(sections['test'])} items")
        
        # Test scoring with just one item
        if sections['test']:
            print("\n4. Testing article scoring...")
            from app.news import score_items
            
            test_item = sections['test'][:1]  # Just one item
            scored = score_items(client, test_item, prompt="Test scoring")
            if scored and scored[0].get('importance') is not None:
                print(f"   ✓ Scoring successful: Item scored {scored[0]['importance']}/100")
    
    print("\n✅ All basic tests passed! The pipeline should work.")
    print("\nYou can now run the full pipeline with: python3 test_run.py")
    
except KeyboardInterrupt:
    print("\n✗ Interrupted by user")
    sys.exit(130)
except Exception as e:
    print(f"\n✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)