#!/usr/bin/env python3
"""Test with limited feeds to avoid hanging Montreal Gazette feed."""

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

print("\n=== Running Limited Test (Guardian + BBC only) ===\n")

# Temporarily override feed configuration
import app.news as news

# Save original feeds
original_feeds = news.DEFAULT_FEEDS.copy()

# Use only Guardian and BBC (skip Montreal and AI feeds)
news.DEFAULT_FEEDS = {
    "guardian": original_feeds["guardian"],
    "bbc": original_feeds["bbc"]
}

try:
    from app.main import main
    main()
except KeyboardInterrupt:
    print("\n✗ Interrupted by user")
    sys.exit(130)
except Exception as e:
    print(f"\n✗ Pipeline failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Restore original feeds
    news.DEFAULT_FEEDS = original_feeds