#!/usr/bin/env python3
"""
Interactive Notion Formatting Test Script

Test different Notion formatting templates to see how they render.
Create and modify templates, then send them to Notion for visual verification.
Perfect for iterating on layout, emojis, and formatting.
"""

import os
import sys
from datetime import datetime
from notion_client import Client as Notion

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.notion_utils import find_or_create_daily_page, append_markdown, append_audio_section
from app.utils import today_str

# Predefined templates for testing different layouts
TEMPLATES = {
    "simple": """## Morning Briefing

Good morning Anton! Here's your zen moment: "The journey of a thousand miles begins with one step."

One... Two... Three... Four... Five... Six... Seven... Eight... Nine... Ten...

Today's overview: 3 articles from Guardian, 2 from BBC, 1 from Montreal News.

## Guardian

Hey Anton! News from Guardian - we have 2 articles for you.

- **Scotland prepares for independence referendum** (Date: 2025-09-06)
- Why it matters: Could significantly impact immigration policies for current work visa holders
- **Climate change reshapes UK agriculture** - farmers adapt to new conditions (Date: 2025-09-06)
- Why it matters: Shows broader environmental trends affecting policy

## BBC

Hey Anton! News from BBC - we have 1 article for you.

- **Major AI breakthrough announced** by leading tech companies (Date: 2025-09-06)
- Why it matters: Relevant for startup opportunities and tech career development""",

    "rich_formatting": """## Morning Briefing

☀️ Good morning Anton! Here's your personalized morning update with a touch of zen.

🧘 Today's wisdom: "In the midst of winter, I found there was, within me, an invincible summer."

🔢 Let's center ourselves: One... Two... Three... Four... Five... Six... Seven... Eight... Nine... Ten...

📊 Today's news overview: 4 interesting articles from Guardian, 2 from BBC, 1 from Montreal News.

## Guardian

🏛️ Hey Anton! News from Guardian - we have 3 articles for you.

- 🚨 **BREAKING: Scotland independence vote scheduled** for next year amid rising support (Date: 2025-09-06)
- 💡 Why it matters: Direct impact on immigration policies - crucial for your PR application timeline
- 🌍 **Climate protesters block London traffic** in major demonstration (Date: 2025-09-06)
- 💡 Why it matters: Shows growing environmental activism affecting policy discussions
- 🎨 **Edinburgh Festival showcases Montreal artists** in cultural exchange (Date: 2025-09-06)
- 💡 Why it matters: Connection between your two home cities - Scotland and Montreal

## BBC

📺 Hey Anton! News from BBC - we have 2 articles for you.

- 🤖 **AI startup funding reaches record highs** as investors pour billions into sector (Date: 2025-09-06)
- 💡 Why it matters: Massive opportunities in your field - perfect timing for career moves
- 🏴󠁧󠁢󠁳󠁣󠁴󠁿 **Scotland's tech sector growth** outpaces rest of UK for third quarter (Date: 2025-09-06)
- 💡 Why it matters: Your homeland leading in tech - potential opportunities post-PR

## Montreal News

🍁 Hey Anton! News from Montreal News - we have 1 article for you.

- 📅 **Montreal immigration processing times** reduced by 30% following policy changes (Date: 2025-09-06)
- 💡 Why it matters: Excellent news for your PR application - faster processing expected""",

    "toggle_heavy": """## Morning Briefing

🌅 Good morning Anton! Let's start your day with intention and awareness.

🧘‍♂️ Zen moment: "The present moment is the only moment available to us, and it is the door to all moments."

🎯 Mindful counting: One... Two... Three... Four... Five... Six... Seven... Eight... Nine... Ten...

📈 Today's curated news: 3 articles from Guardian, 2 from BBC, 2 from Montreal News, 1 from AI sources.

## Guardian

🏛️ Hey Anton! News from Guardian - we have 3 compelling articles for you.

- 🏴󠁧󠁢󠁳󠁣󠁴󠁿 **Scotland's independence momentum builds** as new polls show majority support (Date: 2025-09-06)
- 💡 Why it matters: Constitutional changes could reshape immigration laws - monitor closely for PR implications
- 🌍 **Montreal leads North American climate initiatives** in new international study (Date: 2025-09-06)
- 💡 Why it matters: Your adopted city gaining recognition - positive for long-term residence value
- 🏛️ **UK tech visa program expansion** announced to attract global talent (Date: 2025-09-06)
- 💡 Why it matters: Beneficial policy shift for skilled immigrants like yourself

## BBC

📺 Hey Anton! News from BBC - we have 2 articles for you.

- 🚀 **AI revolution accelerates** as ChatGPT competitor launches with advanced features (Date: 2025-09-06)
- 💡 Why it matters: Stay ahead of AI trends - crucial for your tech career trajectory
- 🎓 **Scottish universities partner with Montreal institutions** in new exchange program (Date: 2025-09-06)
- 💡 Why it matters: Bridging your two homes - potential networking opportunities

## Montreal News

🍁 Hey Anton! News from Montreal News - we have 2 local updates for you.

- 📋 **Express Entry draws increase frequency** - more invitations expected this month (Date: 2025-09-06)
- 💡 Why it matters: Excellent timing for your PR application - higher chances of selection
- 🏙️ **Montreal tech sector hiring surge** continues as companies expand teams (Date: 2025-09-06)
- 💡 Why it matters: Strong job market supports your career stability and PR application

## AI

🤖 Hey Anton! News from AI - we have 1 article for you.

- 🚀 **Startup funding in AI hits $50B milestone** across North America this quarter (Date: 2025-09-06)
- 💡 Why it matters: Unprecedented opportunity in your expertise area - perfect timing for career moves"""
}

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

def show_template_options():
    """Display available templates."""
    print("\nAvailable templates:")
    templates = list(TEMPLATES.keys())
    
    for i, template in enumerate(templates, 1):
        print(f"  {i}. {template.replace('_', ' ').title()}")
        
        # Show preview of template
        preview = TEMPLATES[template].split('\n')[0:3]
        for line in preview:
            if line.strip():
                print(f"     {line[:60]}{'...' if len(line) > 60 else ''}")
        print()
    
    print(f"  {len(templates) + 1}. Custom template (enter your own)")
    print(f"  {len(templates) + 2}. Edit existing template")
    
    return templates

def get_template_choice(templates):
    """Get user's template choice."""
    while True:
        try:
            choice = input(f"Select template (1-{len(templates) + 2}): ").strip()
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(templates):
                    return templates[choice_num - 1], TEMPLATES[templates[choice_num - 1]]
                elif choice_num == len(templates) + 1:
                    return "custom", get_custom_template()
                elif choice_num == len(templates) + 2:
                    return edit_template(templates)
                else:
                    print("Invalid choice. Please try again.")
            else:
                print("Invalid choice. Please try again.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)

def get_custom_template():
    """Get custom template from user."""
    print("\nEnter your custom template (end with a line containing just 'END'):")
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == 'END':
                break
            lines.append(line)
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
    
    return '\n'.join(lines)

def edit_template(templates):
    """Edit an existing template."""
    print("\nSelect template to edit:")
    for i, template in enumerate(templates, 1):
        print(f"  {i}. {template.replace('_', ' ').title()}")
    
    while True:
        try:
            choice = input(f"Select template to edit (1-{len(templates)}): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(templates):
                template_name = templates[int(choice) - 1]
                break
            else:
                print("Invalid choice. Please try again.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
    
    print(f"\nCurrent {template_name} template:")
    print("-" * 40)
    print(TEMPLATES[template_name])
    print("-" * 40)
    
    print("\nEnter modified template (end with a line containing just 'END'):")
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == 'END':
                break
            lines.append(line)
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
    
    modified_content = '\n'.join(lines)
    return f"{template_name}_modified", modified_content

def test_notion_formatting():
    """Main interactive Notion testing function."""
    print_header("Notion Formatting Test Tool")
    print("Test different templates and see how they render in Notion")
    print("Perfect for iterating on layout, emojis, and visual appeal")
    
    # Load environment
    load_environment()
    
    # Check for required environment variables
    notion_token = os.getenv('NOTION_TOKEN')
    notion_db_id = os.getenv('NOTION_DAILY_DB_ID')
    
    if not notion_token or not notion_db_id:
        print("❌ Missing required environment variables:")
        if not notion_token:
            print("   - NOTION_TOKEN")
        if not notion_db_id:
            print("   - NOTION_DAILY_DB_ID")
        print("\nMake sure your .env file is set up correctly.")
        return
    
    # Initialize Notion client
    try:
        notion = Notion(auth=notion_token)
        print("✅ Notion client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Notion client: {e}")
        return
    
    while True:
        try:
            # Show template options
            templates = show_template_options()
            template_name, template_content = get_template_choice(templates)
            
            print_header(f"Testing Template: {template_name.replace('_', ' ').title()}")
            
            # Show preview
            print("Template preview:")
            print("-" * 40)
            preview_lines = template_content.split('\n')[:15]
            for line in preview_lines:
                print(line)
            if len(template_content.split('\n')) > 15:
                print("... (truncated)")
            print("-" * 40)
            
            # Confirm before sending to Notion
            confirm = input(f"\nSend this template to Notion? (y/n): ").strip().lower()
            if confirm != 'y':
                continue
            
            # Create test page
            test_date = f"test-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}"
            print(f"\n🔄 Creating test page: {test_date}")
            
            page = find_or_create_daily_page(notion, notion_db_id, test_date)
            page_id = page["page_id"]
            page_url = page["url"]
            
            print(f"✅ Created page: {page_id}")
            
            # Test with sample audio blocks first
            sample_audio_blocks = [
                ("🌅 Morning Intro - Personal Briefing", "https://example.com/morning.ogg"),
                ("Guardian – Section Audio", "https://example.com/guardian.ogg"),
                ("BBC – Section Audio", "https://example.com/bbc.ogg"),
            ]
            
            print("🔄 Adding audio section at top...")
            append_audio_section(notion, page_id, sample_audio_blocks)
            
            # Add the template content
            print("🔄 Adding template content...")
            append_markdown(notion, page_id, template_content)
            
            print(f"\n✅ Template sent to Notion successfully!")
            print(f"🔗 View your page: {page_url}")
            
            # Ask for feedback
            print(f"\n{'='*60}")
            print("Go check the Notion page and see how it looks!")
            feedback = input("How did it look? (good/bad/needs work): ").strip().lower()
            
            if feedback in ['bad', 'needs work', 'needs_work']:
                edit_choice = input("Want to edit this template and try again? (y/n): ").strip().lower()
                if edit_choice == 'y':
                    # Save the modified template for next iteration
                    TEMPLATES[f"{template_name}_v2"] = template_content
                    continue
            
            # Ask if user wants to continue
            continue_choice = input("\nTest another template? (y/n): ").strip().lower()
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
    
    print(f"\n👋 Thanks for testing! Your final templates are ready to integrate into the main code.")
    
    # Show final templates
    if len(TEMPLATES) > 3:  # If user created custom templates
        print(f"\nCustom templates created during this session:")
        for name, content in TEMPLATES.items():
            if '_v2' in name or name == 'custom':
                print(f"\n--- {name} ---")
                print(content[:200] + "..." if len(content) > 200 else content)

if __name__ == "__main__":
    test_notion_formatting()