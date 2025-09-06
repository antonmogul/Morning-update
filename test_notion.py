#!/usr/bin/env python3
"""Quick test for Notion integration with mock data."""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path, override=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

print("\n=== Testing Notion Integration ===\n")

try:
    # Test Notion connection and page creation
    from notion_client import Client as Notion
    from app.notion_utils import find_or_create_daily_page, append_markdown, append_audio, add_comment
    from app.news import generate_morning_intro, tts_to_mp3_bytes
    from app.utils import today_str
    from openai import OpenAI
    
    print("1. Testing Notion connection...")
    notion = Notion(auth=os.getenv('NOTION_TOKEN'))
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    db_id = os.getenv('NOTION_DAILY_DB_ID')
    
    # Test database access
    result = notion.databases.query(database_id=db_id, page_size=1)
    print(f"   ✓ Connected to database with {len(result.get('results', []))} existing pages")
    
    print("\n2. Testing page creation...")
    date_str = today_str("America/Toronto")
    test_page_title = f"TEST-{date_str}"
    
    page = find_or_create_daily_page(notion, db_id, test_page_title)
    page_id = page["page_id"]
    print(f"   ✓ Created/found test page: {page_id}")
    
    print("\n3. Testing morning intro generation...")
    # Mock sections summary
    sections_summary = {
        "guardian": 3,
        "bbc": 2,
        "montreal_news": 1
    }
    
    intro_text = generate_morning_intro(client, sections_summary, name="Anton", location="Montreal")
    print(f"   ✓ Generated intro: {intro_text[:100]}...")
    
    print("\n4. Testing TTS generation...")
    intro_audio = tts_to_mp3_bytes(client, intro_text, voice="nova")
    print(f"   ✓ Generated {len(intro_audio)} bytes of intro audio")
    
    print("\n5. Testing Notion content update...")
    # Mock content
    mock_content = f"""## Morning Briefing

{intro_text}

## Guardian
Hey Anton! News from Guardian - we have 3 articles for you.

• Breaking: Major climate summit reaches historic agreement
• Culture: New British museum exhibition draws record crowds  
• Lifestyle: Study reveals surprising benefits of morning routines

## BBC
Hey Anton! News from BBC - we have 2 articles for you.

• Technology: AI breakthrough promises faster drug discovery
• Scotland: Edinburgh festival breaks attendance records"""

    append_markdown(notion, page_id, mock_content)
    print("   ✓ Added markdown content to Notion page")
    
    print("\n6. Testing audio block (mock URL)...")
    mock_audio_url = "https://raw.githubusercontent.com/antonmogul/Morning-update/main/public/daily/2025-09-05/morning_intro.ogg"
    append_audio(notion, page_id, "🌅 Morning Intro - Personal Briefing", mock_audio_url)
    print("   ✓ Added mock audio block")
    
    print("\n7. Adding completion comment...")
    add_comment(notion, page_id, "✅ Good morning Anton! Your personalized news brief test is complete!")
    print("   ✓ Added completion comment")
    
    print(f"\n🎉 Notion integration test successful!")
    print(f"Check your Notion database for the test page: {test_page_title}")
    if page.get('url'):
        print(f"Direct link: {page['url']}")
    
except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)