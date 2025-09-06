# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated daily news brief pipeline that fetches RSS feeds, scores news items for importance using OpenAI, generates audio summaries with TTS, and posts results to a Notion database. Runs daily via GitHub Actions at 07:30 Montreal time.

## Commands

### Local Development
```bash
# Setup virtual environment and install dependencies
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the pipeline locally (requires all environment variables)
python -m app.main
```

### Testing
No formal test suite exists. Testing is done manually by running the pipeline and verifying:
- Audio files are generated in `public/daily/YYYY-MM-DD/`
- Notion page is created/updated with content and audio blocks
- GitHub Actions workflow completes successfully

### Production Deployment
The pipeline runs automatically via GitHub Actions (`.github/workflows/daily-brief.yml`). Manual triggers available through GitHub Actions interface.

## Architecture

### Core Components

1. **News Pipeline** (`app/news.py`):
   - Fetches RSS feeds from multiple sources (Guardian, BBC, Montreal Gazette, AI news)
   - Scores articles 0-100 for importance using GPT-4o-mini
   - Filters to last 24 hours and deduplicates by title+URL
   - Generates text summaries and converts to MP3/OGG audio

2. **Notion Integration** (`app/notion_utils.py`):
   - Finds or creates daily pages in Notion database
   - Converts markdown to Notion blocks (headings, bullets, paragraphs)
   - Embeds audio blocks with GitHub raw URLs
   - Posts completion notifications as comments

3. **Main Orchestrator** (`app/main.py`):
   - Coordinates the entire pipeline flow
   - Creates "Roundup" section with high-importance items only (threshold configurable)
   - Saves audio files to `public/daily/YYYY-MM-DD/` directory structure
   - Commits generated files back to repository

### Data Flow

1. Fetch → Score → Filter (importance threshold) → Summarize → Generate Audio
2. Create/update Notion page with markdown content + audio embeds  
3. Commit audio files to repo for GitHub raw URLs
4. Notify via Notion comment

## Configuration

### Required Environment Variables (GitHub Secrets)
- `OPENAI_API_KEY`: OpenAI API key for scoring, summarization, and TTS
- `NOTION_TOKEN`: Notion integration token  
- `NOTION_DAILY_DB_ID`: Target Notion database ID (32 characters)

### Optional Environment Variables
- `NOTION_DAILY_TITLE_PROP`: Notion title property name (default: "Name")
- `NEWS_IMPORTANCE_THRESHOLD`: Minimum score for Roundup inclusion (default: 70)
- `TZ`: Timezone for date calculations (default: "America/Toronto")

## Feed Configuration

News sources are configured in `app/news.py` as `DEFAULT_FEEDS`. Each feed has:
- `urls`: List of RSS feed URLs
- `prompt`: Context for AI scoring/summarization

Current sections: guardian, bbc, montreal_gazette, ai

## Audio Generation

- Uses OpenAI TTS (gpt-4o-mini-tts, alloy voice)
- Generates MP3 then converts to OGG for web compatibility
- Audio files hosted via GitHub raw URLs for Notion embedding
- Separate audio for roundup + each news section

## Notion Page Structure

Daily pages (YYYY-MM-DD format) contain:
1. **Roundup** section (high-importance items across all sources)
2. Individual sections per news source with bullet summaries
3. Audio blocks for roundup + each section
4. Completion notification comment

## GitHub Actions Workflow

- Scheduled for weekdays 07:30 Montreal time (handles DST with dual cron)
- Installs Python 3.11, ffmpeg, and dependencies
- Commits generated audio files back to repository
- Uses `github-actions[bot]` for commits