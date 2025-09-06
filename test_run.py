#!/usr/bin/env python3
"""Test script to run the pipeline with .env file and verbose logging."""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path, override=True)
print(f"✓ Loaded environment from {env_path}")

# Set up very verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Verify environment variables are loaded
print("\n=== Environment Check ===")
env_vars = ['OPENAI_API_KEY', 'NOTION_TOKEN', 'NOTION_DAILY_DB_ID']
for var in env_vars:
    value = os.getenv(var)
    if value:
        # Mask sensitive data
        if 'KEY' in var or 'TOKEN' in var:
            masked = value[:10] + '...' + value[-4:] if len(value) > 14 else '***'
            print(f"✓ {var}: {masked}")
        else:
            print(f"✓ {var}: {value}")
    else:
        print(f"✗ {var}: NOT SET")

print("\n=== Starting Pipeline ===")
print("This will:")
print("1. Fetch RSS feeds from news sources")
print("2. Score articles for importance using OpenAI")
print("3. Generate summaries and audio")
print("4. Create/update a Notion page")
print("\n" + "="*50 + "\n")

# Import and run main
try:
    from app.main import main
    main()
except KeyboardInterrupt:
    print("\n\n✗ Interrupted by user")
    sys.exit(130)
except Exception as e:
    print(f"\n\n✗ Pipeline failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)