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
    """Convert markdown to rich Notion blocks with emojis and toggles.
    
    Converts:
    - "## " → toggle with emoji heading
    - "- "  → bulleted_list_item with enhanced formatting
    - Bold text with **text**
    - other non-empty lines → paragraph
    
    Args:
        notion: Notion client instance
        page_id: Target page ID
        md_text: Markdown text to convert
    """
    try:
        blocks = []
        lines_processed = 0
        current_toggle = None
        current_toggle_content = []
        
        # Add section emojis
        section_emojis = {
            "Morning Briefing": "🌅",
            "Guardian": "🏛️", 
            "BBC": "📺",
            "Montreal News": "🍁",
            "AI": "🤖"
        }
        
        def parse_rich_text(text: str) -> list:
            """Parse markdown formatting in text."""
            rich_text = []
            current_pos = 0
            
            # Handle bold text **text**
            import re
            bold_pattern = r'\*\*([^*]+)\*\*'
            
            for match in re.finditer(bold_pattern, text):
                # Add text before bold
                if match.start() > current_pos:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": text[current_pos:match.start()]}
                    })
                
                # Add bold text
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group(1)},
                    "annotations": {"bold": True}
                })
                
                current_pos = match.end()
            
            # Add remaining text
            if current_pos < len(text):
                rich_text.append({
                    "type": "text",
                    "text": {"content": text[current_pos:]}
                })
            
            return rich_text if rich_text else [{"type": "text", "text": {"content": text}}]
        
        def finalize_toggle():
            """Add current toggle to blocks if it exists."""
            if current_toggle and current_toggle_content:
                current_toggle["toggle"]["children"] = current_toggle_content
                blocks.append(current_toggle)
        
        for line in md_text.splitlines():
            if line.startswith("## "):
                # Finalize previous toggle
                finalize_toggle()
                
                # Create new toggle with emoji
                title = line[3:].strip()
                emoji = ""
                for section, section_emoji in section_emojis.items():
                    if section in title:
                        emoji = section_emoji + " "
                        break
                
                current_toggle = {
                    "type": "toggle",
                    "toggle": {
                        "rich_text": parse_rich_text(f"{emoji}{title}"),
                        "children": []
                    }
                }
                current_toggle_content = []
                lines_processed += 1
                
            elif line.startswith("- "):
                content = line[2:].strip()
                # Add emojis to bullet points
                if "Why it matters" in content:
                    content = "💡 " + content
                elif "Date:" in content:
                    content = "📅 " + content
                elif "Breaking:" in content or "BREAKING:" in content:
                    content = "🚨 " + content
                elif "Scotland" in content:
                    content = "🏴󠁧󠁢󠁳󠁣󠁴󠁿 " + content
                elif "Montreal" in content:
                    content = "🍁 " + content
                elif "AI" in content or "Tech" in content:
                    content = "🤖 " + content
                elif "Climate" in content or "Environment" in content:
                    content = "🌍 " + content
                elif "Culture" in content or "Art" in content:
                    content = "🎨 " + content
                
                bullet_block = {
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": parse_rich_text(content)}
                }
                
                if current_toggle:
                    current_toggle_content.append(bullet_block)
                else:
                    blocks.append(bullet_block)
                lines_processed += 1
                
            else:
                if line.strip() == "":
                    continue
                
                # Add emojis to regular paragraphs
                content = line
                if "Good morning" in content:
                    content = "☀️ " + content
                elif "weather" in content.lower():
                    content = "🌤️ " + content
                elif "zen" in content.lower() or "calm" in content.lower():
                    content = "🧘 " + content
                elif "count" in content.lower() and any(num in content for num in ["1", "2", "3"]):
                    content = "🔢 " + content
                
                para_block = {
                    "type": "paragraph",
                    "paragraph": {"rich_text": parse_rich_text(content)}
                }
                
                if current_toggle:
                    current_toggle_content.append(para_block)
                else:
                    blocks.append(para_block)
                lines_processed += 1
        
        # Finalize last toggle
        finalize_toggle()
        
        if blocks:
            notion.blocks.children.append(block_id=page_id, children=blocks)
            logger.info(f"Appended {len(blocks)} blocks ({lines_processed} lines) to Notion page")
        else:
            logger.warning("No blocks to append to Notion page")
            
    except Exception as e:
        logger.error(f"Failed to append markdown to Notion page: {e}")
        raise


def append_audio_section(notion: Notion, page_id: str, audio_blocks: list):
    """Add all audio blocks at the top with beautiful formatting.
    
    Args:
        notion: Notion client instance
        page_id: Target page ID
        audio_blocks: List of (heading, audio_url) tuples
    """
    try:
        if not audio_blocks:
            logger.warning("No audio blocks to add")
            return
            
        blocks = [
            {
                "type": "heading_2", 
                "heading_2": {
                    "rich_text": [{
                        "type": "text", 
                        "text": {"content": "🎧 Your Daily Audio Briefing"}
                    }]
                }
            },
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": "Listen to your personalized morning update! 🌅"}
                    }]
                }
            }
        ]
        
        # Add each audio block with nice formatting
        for heading, audio_url in audio_blocks:
            if audio_url:
                blocks.extend([
                    {
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{
                                "type": "text", 
                                "text": {"content": heading},
                                "annotations": {"color": "blue"}
                            }]
                        },
                    },
                    {
                        "type": "audio", 
                        "audio": {"type": "external", "external": {"url": audio_url}}
                    }
                ])
        
        # Add divider
        blocks.append({
            "type": "divider",
            "divider": {}
        })
        
        notion.blocks.children.append(block_id=page_id, children=blocks)
        logger.info(f"Added {len(audio_blocks)} audio blocks to top of page")
        
    except Exception as e:
        logger.error(f"Failed to append audio blocks: {e}")
        raise


def add_comment(notion: Notion, page_id: str, text: str):
    """Add comment to Notion page.
    
    Args:
        notion: Notion client instance
        page_id: Target page ID
        text: Comment text
    """
    try:
        # Add emojis to the comment
        enhanced_text = f"🎉 {text}"
        
        notion.comments.create(
            parent={"page_id": page_id},
            rich_text=[{"type": "text", "text": {"content": enhanced_text}}],
        )
        logger.info(f"Added comment to Notion page: {enhanced_text[:50]}...")
        
    except Exception as e:
        logger.error(f"Failed to add comment to Notion page: {e}")
        raise
