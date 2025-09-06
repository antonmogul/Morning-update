#!/usr/bin/env python3
"""
Interactive RSS Feed Testing Script

Test individual news feeds, see what articles are retrieved, 
how they're scored, and what summaries are generated.
Perfect for tweaking prompts and understanding feed behavior.
"""

import os
import sys
from datetime import datetime
from openai import OpenAI

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.news import DEFAULT_FEEDS, fetch_feeds, score_items, summarize_items
from app.utils import today_str

def load_environment():
    """Load environment variables from .env if available."""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

def print_header(title):
    """Print a nice header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_section(title):
    """Print a section header."""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")

def show_feed_options():
    """Display available feeds and get user selection."""
    print("\nAvailable feeds:")
    feeds = list(DEFAULT_FEEDS.keys())
    for i, feed in enumerate(feeds, 1):
        prompt = DEFAULT_FEEDS[feed]['prompt']
        print(f"  {i}. {feed.replace('_', ' ').title()}")
        print(f"     URLs: {len(DEFAULT_FEEDS[feed]['urls'])} sources")
        print(f"     Focus: {prompt}")
        print()
    
    while True:
        try:
            choice = input(f"Select feed (1-{len(feeds)}) or 'all' for all feeds: ").strip().lower()
            if choice == 'all':
                return feeds
            elif choice.isdigit() and 1 <= int(choice) <= len(feeds):
                return [feeds[int(choice) - 1]]
            else:
                print("Invalid choice. Please try again.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)

def show_test_options():
    """Display test options and get user selection."""
    options = [
        ("Fetch articles only", "Just retrieve and show articles from RSS feeds"),
        ("Fetch + Score articles", "Retrieve articles and score them 0-100 for importance"),
        ("Full pipeline", "Retrieve, score, and generate summaries"),
    ]
    
    print("\nTest options:")
    for i, (name, desc) in enumerate(options, 1):
        print(f"  {i}. {name}")
        print(f"     {desc}")
        print()
    
    while True:
        try:
            choice = input(f"Select test (1-{len(options)}): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                return int(choice)
            else:
                print("Invalid choice. Please try again.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)

def display_articles(section, articles, show_scores=False, show_full=False):
    """Display articles in a nice format."""
    if not articles:
        print(f"No articles found for {section}")
        return
    
    print_section(f"{section.replace('_', ' ').title()} - {len(articles)} articles")
    
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article['title']}")
        print(f"   URL: {article['url']}")
        print(f"   Published: {article.get('published', 'Unknown')}")
        print(f"   Source: {article.get('source', 'Unknown')}")
        
        if show_scores and 'importance' in article:
            score = article['importance']
            reason = article.get('importance_reason', 'No reason provided')
            print(f"   Score: {score}/100")
            print(f"   Reason: {reason}")
        
        if show_full:
            summary = article.get('summary', '')
            if summary:
                # Truncate very long summaries
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                print(f"   Summary: {summary}")
        
        print()

def test_feeds():
    """Main interactive feed testing function."""
    print_header("RSS Feed Testing Tool")
    print("Test individual news feeds to understand their behavior")
    print("Perfect for tweaking prompts and scoring criteria")
    
    # Load environment
    load_environment()
    
    # Check for OpenAI API key if needed for scoring/summarizing
    openai_key = os.getenv('OPENAI_API_KEY')
    
    while True:
        try:
            # Get feed selection
            selected_feeds = show_feed_options()
            test_type = show_test_options()
            
            # Set up feed configuration
            if selected_feeds == list(DEFAULT_FEEDS.keys()):
                feeds_to_test = DEFAULT_FEEDS
                print_header("Testing ALL feeds")
            else:
                feeds_to_test = {feed: DEFAULT_FEEDS[feed] for feed in selected_feeds}
                print_header(f"Testing: {', '.join(f.replace('_', ' ').title() for f in selected_feeds)}")
            
            # Fetch articles
            print("\n🔄 Fetching RSS feeds...")
            all_articles = fetch_feeds(feeds_to_test, since_hours=24)
            
            for section, articles in all_articles.items():
                if test_type >= 1:  # Fetch articles only
                    display_articles(section, articles, show_full=True)
                
                if test_type >= 2 and openai_key:  # Fetch + Score
                    print(f"\n🧠 Scoring articles for {section}...")
                    client = OpenAI(api_key=openai_key)
                    prompt = feeds_to_test[section].get('prompt', '')
                    scored_articles = score_items(client, articles, prompt=prompt)
                    display_articles(section, scored_articles, show_scores=True)
                
                if test_type >= 3 and openai_key:  # Full pipeline
                    print(f"\n✍️  Generating summary for {section}...")
                    summary = summarize_items(client, section, scored_articles, max_items=5, prompt=prompt, name="Anton")
                    print_section(f"{section.replace('_', ' ').title()} Summary")
                    print(summary)
            
            # Ask if user wants to continue
            print("\n" + "="*60)
            continue_choice = input("\nTest another feed? (y/n): ").strip().lower()
            if continue_choice != 'y':
                break
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            continue_choice = input("\nContinue despite error? (y/n): ").strip().lower()
            if continue_choice != 'y':
                break
    
    print("\n👋 Thanks for testing! Use these insights to improve your feed prompts.")

if __name__ == "__main__":
    test_feeds()