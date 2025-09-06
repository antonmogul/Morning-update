#!/usr/bin/env python3
"""Debug Notion database properties."""

import os
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client as Notion

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path, override=True)

try:
    notion = Notion(auth=os.getenv('NOTION_TOKEN'))
    db_id = os.getenv('NOTION_DAILY_DB_ID')
    
    print("Retrieving database schema...")
    db = notion.databases.retrieve(database_id=db_id)
    
    print(f"\nDatabase: {db.get('title', [{}])[0].get('plain_text', 'Unknown')}")
    print("\nAvailable properties:")
    for prop_name, prop_info in db['properties'].items():
        prop_type = prop_info['type']
        print(f"  - {prop_name} ({prop_type})")
        
    print(f"\nDefault title property should be one of the above.")
    print("Add this to your .env file:")
    
    # Find the title property
    title_prop = None
    for prop_name, prop_info in db['properties'].items():
        if prop_info['type'] == 'title':
            title_prop = prop_name
            break
    
    if title_prop:
        print(f"NOTION_DAILY_TITLE_PROP={title_prop}")
    else:
        print("No title property found! You need to add a title property to your database.")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()