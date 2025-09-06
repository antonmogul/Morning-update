# Test Scripts Usage Guide

Two interactive test scripts to help you iterate and improve your Morning Update pipeline.

## 1. RSS Feed Testing (`test_feeds.py`)

**Purpose:** Test individual RSS feeds to see what articles are retrieved, how they're scored (0-100), and what summaries are generated.

**Usage:**
```bash
python3 tests/test_feeds.py
```

**Features:**
- Choose specific feeds (Guardian, BBC, Montreal News, AI) or test all
- Three test modes:
  1. **Fetch articles only** - See what RSS items are retrieved
  2. **Fetch + Score articles** - See importance scores (0-100) with reasoning
  3. **Full pipeline** - See complete flow including AI summaries
- Interactive menu system
- Perfect for tweaking feed prompts and scoring criteria

**Example Session:**
```
Available feeds:
  1. Guardian
     URLs: 3 sources
     Focus: Mix of world, culture, and lifestyle stories.

  2. BBC
     URLs: 2 sources  
     Focus: Prioritize Scotland and broader UK coverage...

Select feed (1-4) or 'all' for all feeds: 1

Test options:
  1. Fetch articles only
  2. Fetch + Score articles  
  3. Full pipeline

Select test (1-3): 3
```

**Requirements:** 
- For scoring/summarizing: `OPENAI_API_KEY` in environment
- The script will load from `.env` file if present

---

## 2. Notion Formatting Testing (`test_notion.py`)

**Purpose:** Test different Notion formatting templates to see how they render visually. Create and modify templates, then send them to Notion for verification.

**Usage:**
```bash
python3 tests/test_notion.py
```

**Features:**
- 3 pre-built templates:
  - **Simple** - Basic formatting, minimal emojis
  - **Rich Formatting** - Heavy emoji use, colorful content
  - **Toggle Heavy** - Comprehensive layout with all features
- **Custom template** - Enter your own markdown
- **Edit existing** - Modify templates on the fly
- Creates test pages with timestamps (e.g., `test-2025-09-06-143022`)
- Includes sample audio blocks to test complete layout
- Interactive feedback loop for iterating

**Example Session:**
```
Available templates:
  1. Simple
     ## Morning Briefing
     Good morning Anton! Here's your zen moment...

  2. Rich Formatting  
     ## Morning Briefing
     ☀️ Good morning Anton! Here's your personalized...

Select template (1-5): 2

Template preview:
----------------------------------------
## Morning Briefing

☀️ Good morning Anton! Here's your personalized morning update...
🧘 Today's wisdom: "In the midst of winter, I found there was...
...

Send this template to Notion? (y/n): y

🔄 Creating test page: test-2025-09-06-143022
✅ Created page: abc123...
🔗 View your page: https://notion.so/...

Go check the Notion page and see how it looks!
How did it look? (good/bad/needs work): good
```

**Requirements:** 
- `NOTION_TOKEN` and `NOTION_DAILY_DB_ID` in environment
- The script will load from `.env` file if present

---

## Workflow Recommendations

### For RSS Feed Tuning:
1. Run `python3 tests/test_feeds.py`
2. Test individual feeds with "Fetch + Score articles" mode
3. Look at scores and reasoning - adjust prompts in `app/news.py` 
4. Test "Full pipeline" to see if summaries match your preferences
5. Iterate until you're happy with content and scoring

### For Notion Layout:
1. Run `python3 tests/test_notion.py` 
2. Start with "Rich Formatting" template
3. Send to Notion and check visual appeal
4. Use "Edit existing template" to modify formatting
5. Test custom layouts for specific needs
6. Once satisfied, integrate changes into `app/notion_utils.py`

### Integration:
- After testing, update the main code with your preferred:
  - Feed prompts in `DEFAULT_FEEDS` (`app/news.py`)
  - Formatting logic in `append_markdown()` (`app/notion_utils.py`)
  - Emoji mappings and text processing

Both scripts create a nice feedback loop for perfecting your morning briefing system!