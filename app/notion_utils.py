import os
from typing import Dict, Any
from notion_client import Client as Notion


def get_title_prop_name() -> str:
    return os.getenv("NOTION_DAILY_TITLE_PROP", "Name")


def find_or_create_daily_page(notion: Notion, db_id: str, title: str) -> Dict[str, Any]:
    # Find by title
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
        return {"page_id": page["id"], "url": page["url"]}

    # Create
    newp = notion.pages.create(
        parent={"database_id": db_id},
        properties={
            get_title_prop_name(): {
                "title": [{"text": {"content": title}}],
            }
        },
    )
    return {"page_id": newp["id"], "url": newp["url"]}


def append_markdown(notion: Notion, page_id: str, md_text: str):
    """
    Minimal Markdown-ish to Notion blocks:
    - "## " → heading_2
    - "- "  → bulleted_list_item
    - other non-empty lines → paragraph
    """
    blocks = []
    for line in md_text.splitlines():
        if line.startswith("## "):
            content = line[3:].strip()
            blocks.append({
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": content}}]},
            })
        elif line.startswith("- "):
            content = line[2:].strip()
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": content}}]},
            })
        else:
            if line.strip() == "":
                continue
            blocks.append({
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]},
            })
    if blocks:
        notion.blocks.children.append(block_id=page_id, children=blocks)


def append_audio(notion: Notion, page_id: str, heading: str, audio_url: str):
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


def add_comment(notion: Notion, page_id: str, text: str):
    notion.comments.create(
        parent={"page_id": page_id},
        rich_text=[{"type": "text", "text": {"content": text}}],
    )
