import os
import logging
import sys
from io import BytesIO
from openai import OpenAI
from notion_client import Client as Notion
from pydub import AudioSegment

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from app.news import (
    DEFAULT_FEEDS,
    fetch_feeds,
    score_items,
    summarize_items,
    tts_to_mp3_bytes,
    generate_morning_intro,
)
from app.notion_utils import (
    find_or_create_daily_page,
    append_markdown,
    append_audio_section,
    add_comment,
)
from app.utils import today_str, ensure_dir, repo_raw_url


def save_bytes(path: str, data: bytes):
    """Save bytes to file with error handling.
    
    Args:
        path: File path to save to
        data: Bytes to write
        
    Raises:
        IOError: If file cannot be written
    """
    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "wb") as f:
            f.write(data)
        
        # Change to INFO level for visibility and verify file was created
        file_size = os.path.getsize(path)
        logger.info(f"Saved {len(data)} bytes to {path} (verified size: {file_size} bytes)")
        
        if not os.path.exists(path):
            raise IOError(f"File was not created at {path}")
            
    except Exception as e:
        logger.error(f"Failed to save file {path}: {e}")
        raise IOError(f"Cannot write to {path}: {e}")


def mp3_to_ogg_bytes(mp3_bytes: bytes) -> bytes:
    """Convert MP3 bytes to OGG format.
    
    Args:
        mp3_bytes: MP3 audio data
        
    Returns:
        OGG audio data
        
    Raises:
        Exception: If conversion fails
    """
    try:
        mp3seg = AudioSegment.from_file(BytesIO(mp3_bytes), format="mp3")
        out = BytesIO()
        mp3seg.export(out, format="ogg", codec="libopus", bitrate="48k")
        return out.getvalue()
    except Exception as e:
        logger.error(f"Failed to convert MP3 to OGG: {e}")
        raise


def validate_environment() -> dict:
    """Validate and return required environment variables.
    
    Returns:
        Dictionary of validated environment variables
        
    Raises:
        ValueError: If required environment variables are missing
    """
    required_vars = {
        'NOTION_TOKEN': os.getenv('NOTION_TOKEN'),
        'NOTION_DAILY_DB_ID': os.getenv('NOTION_DAILY_DB_ID'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
    }
    
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        raise ValueError(f"Missing required environment variables: {missing}")
    
    # Optional variables with defaults
    config = required_vars.copy()
    config['TZ'] = os.getenv('TZ', 'America/Toronto')
    config['OUTPUT_DIR'] = os.getenv('OUTPUT_DIR', 'public/daily')
    config['GITHUB_REPO'] = os.getenv('GITHUB_REPO')
    config['GITHUB_REF_NAME'] = os.getenv('GITHUB_REF_NAME', 'main')
    
    # Parse and validate threshold
    threshold_str = os.getenv('NEWS_IMPORTANCE_THRESHOLD', '70')
    try:
        config['NEWS_IMPORTANCE_THRESHOLD'] = int(threshold_str)
        if not 0 <= config['NEWS_IMPORTANCE_THRESHOLD'] <= 100:
            logger.warning(f"Importance threshold {config['NEWS_IMPORTANCE_THRESHOLD']} outside 0-100 range")
    except ValueError:
        logger.error(f"Invalid NEWS_IMPORTANCE_THRESHOLD: {threshold_str}")
        config['NEWS_IMPORTANCE_THRESHOLD'] = 70
    
    return config


def main():
    logger.info("Starting Morning Update pipeline")
    
    try:
        # Validate environment
        config = validate_environment()
        
        tz = config['TZ']
        date_str = today_str(tz)
        output_dir = config['OUTPUT_DIR']
        repo = config['GITHUB_REPO']
        branch = config['GITHUB_REF_NAME']
        importance_threshold = config['NEWS_IMPORTANCE_THRESHOLD']
        notion_token = config['NOTION_TOKEN']
        daily_db_id = config['NOTION_DAILY_DB_ID']
        
        logger.info(f"Processing news for {date_str} with threshold {importance_threshold}")
    except ValueError as e:
        logger.error(f"Environment validation failed: {e}")
        sys.exit(1)

    # Initialize clients
    try:
        notion = Notion(auth=notion_token)
        client = OpenAI(api_key=config['OPENAI_API_KEY'])
        logger.info("Initialized Notion and OpenAI clients")
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        sys.exit(1)

    # 1) Fetch & score news (last 24h)
    try:
        logger.info("Fetching news feeds")
        sections = fetch_feeds(DEFAULT_FEEDS, since_hours=24)
        
        scored_sections = {}
        for section, items in sections.items():
            prompt = DEFAULT_FEEDS[section].get("prompt", "")
            logger.info(f"Scoring {len(items)} items for section '{section}'")
            scored_sections[section] = score_items(client, items, prompt=prompt)
            
        logger.info(f"Processed {len(scored_sections)} sections")
        
    except Exception as e:
        logger.error(f"Failed to fetch/score news: {e}")
        sys.exit(1)

    # 2) Summaries + audio per section
    day_dir = f"{output_dir}/{date_str}"
    
    try:
        ensure_dir(day_dir)
        logger.info(f"Created output directory: {day_dir}")
    except Exception as e:
        logger.error(f"Failed to create directory {day_dir}: {e}")
        sys.exit(1)
    
    markdown_sections = []
    section_audio_urls = {}

    for section, scored in scored_sections.items():
        try:
            prompt = DEFAULT_FEEDS[section].get("prompt", "")
            summary_md = summarize_items(client, section, scored, max_items=5, prompt=prompt, name="Anton")
            markdown_sections.append(summary_md)

            # TTS
            logger.info(f"Generating audio for section '{section}'")
            # Use different voice for each section
            mp3_bytes = tts_to_mp3_bytes(client, summary_md)
            mp3_path = f"{day_dir}/{section}.mp3"
            ogg_path = f"{day_dir}/{section}.ogg"
            
            save_bytes(mp3_path, mp3_bytes)
            
            # Use MP3 format for Notion compatibility (OGG may not be supported)
            section_audio_urls[section] = repo_raw_url(repo, branch, mp3_path)
            
            # Still create OGG for potential future use
            try:
                ogg_bytes = mp3_to_ogg_bytes(mp3_bytes)
                save_bytes(ogg_path, ogg_bytes)
            except Exception as e:
                logger.warning(f"OGG conversion failed for {section}: {e}")
            logger.info(f"Generated audio for section '{section}'")
            
        except Exception as e:
            logger.error(f"Failed to process section '{section}': {e}")
            # Continue with other sections rather than failing entirely
            markdown_sections.append(f"## {section.title()}\n_Processing failed for this section._")

    # 3) Generate Morning Intro instead of Roundup
    # Count articles per section for the intro
    sections_summary = {}
    for section, items in scored_sections.items():
        # Count items that meet threshold
        important_count = sum(1 for item in items if item.get("importance", 0) >= importance_threshold)
        sections_summary[section] = min(important_count, 5)  # Max 5 per section
    
    # Generate personalized morning intro
    try:
        logger.info("Generating personalized morning intro")
        intro_text = generate_morning_intro(client, sections_summary, name="Anton", location="Montreal")
        
        # Create intro audio with a calm voice
        intro_mp3 = tts_to_mp3_bytes(client, intro_text, voice="nova")  # Nova is a calm, pleasant voice
        intro_mp3_path = f"{day_dir}/morning_intro.mp3"
        intro_ogg_path = f"{day_dir}/morning_intro.ogg"
        save_bytes(intro_mp3_path, intro_mp3)
        
        # Use MP3 format for Notion compatibility
        intro_audio_url = repo_raw_url(repo, branch, intro_mp3_path)
        
        # Still create OGG for potential future use
        try:
            intro_ogg = mp3_to_ogg_bytes(intro_mp3)
            save_bytes(intro_ogg_path, intro_ogg)
        except Exception as e:
            logger.warning(f"OGG conversion failed for intro: {e}")
        
        logger.info("Generated morning intro audio")
        
        # Add intro to markdown
        intro_md = f"## Morning Briefing\n\n{intro_text}"
        markdown_sections.insert(0, intro_md)
        
    except Exception as e:
        logger.error(f"Failed to generate morning intro: {e}")
        intro_audio_url = None
        # Fallback to simple roundup summary
        intro_md = "## Morning Briefing\n_Good morning! Here's your news for today._"
        markdown_sections.insert(0, intro_md)

    # 4) Upsert Notion page & append content
    try:
        logger.info(f"Creating/updating Notion page for {date_str}")
        page = find_or_create_daily_page(notion, daily_db_id, date_str)
        page_id = page["page_id"]
        logger.info(f"Using Notion page: {page_id}")

        # Prepare all audio blocks for the top section
        audio_blocks = []
        if intro_audio_url:
            audio_blocks.append(("🌅 Morning Intro - Personal Briefing", intro_audio_url))
        
        for section, url in section_audio_urls.items():
            title = f"{section.replace('_',' ').title()} – Section Audio"
            audio_blocks.append((title, url))

        # Add audio section at the top first
        append_audio_section(notion, page_id, audio_blocks)
        
        # Then add the markdown content
        full_md = "\n\n".join(markdown_sections)
        append_markdown(notion, page_id, full_md)

        # 5) Notify via Notion comment
        add_comment(notion, page_id, "✅ Good morning Anton! Your personalized news brief is ready with intro + section audios.")
        
        logger.info(f"Successfully updated Notion page: {page.get('url', page_id)}")
        
    except Exception as e:
        logger.error(f"Failed to update Notion: {e}")
        sys.exit(1)
    
    logger.info("Morning Update pipeline completed successfully")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        sys.exit(1)
