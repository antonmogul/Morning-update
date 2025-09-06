import os
import logging
from typing import Dict, Any
from notion_client import Client as Notion

# Set up logging
logger = logging.getLogger(__name__)


def get_title_prop_name() -> str:
    return os.getenv("NOTION_DAILY_TITLE_PROP", "Name")


def find_or_create_daily_page(notion: Notion, db_id: str, title: str) -> Dict[str, Any]:
    """Find existing daily page or create new one in Notion database.
    
    Args:
        notion: Notion client instance
        db_id: Notion database ID
        title: Page title to search for or create
        
    Returns:
        Dictionary with page_id and url
        
    Raises:
        Exception: If Notion API calls fail
    """
    try:
        # Find by title
        logger.info(f"Searching for existing page with title: {title}")
        resp = notion.databases.query(
            **{
                "database_id": db_id,
                "filter": {
                    "property": get_title_prop_name(),
                    "title": {"equals": title},
                },
                "page_size": 1,
            }
        )
        
        if resp["results"]:
            page = resp["results"][0]
            logger.info(f"Found existing page: {page['id']}")
            return {"page_id": page["id"], "url": page["url"]}

        # Create new page
        logger.info(f"Creating new page with title: {title}")
        newp = notion.pages.create(
            parent={"database_id": db_id},
            properties={
                get_title_prop_name(): {
                    "title": [{"text": {"content": title}}],
                }
            },
        )
        logger.info(f"Created new page: {newp['id']}")
        return {"page_id": newp["id"], "url": newp["url"]}
        
    except Exception as e:
        logger.error(f"Failed to find/create Notion page '{title}': {e}")
        raise


def append_markdown(notion: Notion, page_id: str, md_text: str):
    """Convert markdown to Notion blocks and append to page.
    
    Converts:
    - "## " → heading_2
    - "- "  → bulleted_list_item  
    - other non-empty lines → paragraph
    
    Args:
        notion: Notion client instance
        page_id: Target page ID
        md_text: Markdown text to convert
    """
    try:
        blocks = []
        lines_processed = 0
        
        for line in md_text.splitlines():
            if line.startswith("## "):
                content = line[3:].strip()
                blocks.append({
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": content}}]},
                })
                lines_processed += 1
            elif line.startswith("- "):
                content = line[2:].strip()
                blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": content}}]},
                })
                lines_processed += 1
            else:
                if line.strip() == "":
                    continue
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]},
                })
                lines_processed += 1
        
        if blocks:
            notion.blocks.children.append(block_id=page_id, children=blocks)
            logger.info(f"Appended {len(blocks)} blocks ({lines_processed} lines) to Notion page")
        else:
            logger.warning("No blocks to append to Notion page")
            
    except Exception as e:
        logger.error(f"Failed to append markdown to Notion page: {e}")
        raise


def append_audio(notion: Notion, page_id: str, heading: str, audio_url: str):
    """Append audio block with heading to Notion page.
    
    Args:
        notion: Notion client instance
        page_id: Target page ID
        heading: Heading text for the audio section
        audio_url: URL to audio file
    """
    try:
        if not audio_url:
            logger.warning(f"Skipping audio block '{heading}' - no URL provided")
            return
            
        blocks = [
            {
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": heading}}]
                },
            },
            {"type": "audio", "audio": {"type": "external", "external": {"url": audio_url}}},
        ]
        
        notion.blocks.children.append(block_id=page_id, children=blocks)
        logger.info(f"Added audio block '{heading}' with URL: {audio_url}")
        
    except Exception as e:
        logger.error(f"Failed to append audio block '{heading}': {e}")
        raise


def add_comment(notion: Notion, page_id: str, text: str):
    """Add comment to Notion page.
    
    Args:
        notion: Notion client instance
        page_id: Target page ID
        text: Comment text
    """
    try:
        notion.comments.create(
            parent={"page_id": page_id},
            rich_text=[{"type": "text", "text": {"content": text}}],
        )
        logger.info(f"Added comment to Notion page: {text[:50]}...")
        
    except Exception as e:
        logger.error(f"Failed to add comment to Notion page: {e}")
        raise
