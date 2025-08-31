import os
from io import BytesIO
from openai import OpenAI
from notion_client import Client as Notion
from pydub import AudioSegment

from app.news import (
    DEFAULT_FEEDS,
    fetch_feeds,
    score_items,
    summarize_items,
    tts_to_mp3_bytes,
)
from app.notion_utils import (
    find_or_create_daily_page,
    append_markdown,
    append_audio,
    add_comment,
)
from app.utils import today_str, ensure_dir, repo_raw_url


def save_bytes(path: str, data: bytes):
    with open(path, "wb") as f:
        f.write(data)


def mp3_to_ogg_bytes(mp3_bytes: bytes) -> bytes:
    mp3seg = AudioSegment.from_file(BytesIO(mp3_bytes), format="mp3")
    out = BytesIO()
    mp3seg.export(out, format="ogg", codec="libopus", bitrate="48k")
    return out.getvalue()


def main():
    tz = os.getenv("TZ", "America/Toronto")
    date_str = today_str(tz)
    output_dir = os.getenv("OUTPUT_DIR", "public/daily")
    repo = os.getenv("GITHUB_REPO")  # owner/repo
    branch = os.getenv("GITHUB_REF_NAME", "main")

    importance_threshold = int(os.getenv("NEWS_IMPORTANCE_THRESHOLD", "70"))
    notion_token = os.environ["NOTION_TOKEN"]
    daily_db_id = os.environ["NOTION_DAILY_DB_ID"]

    notion = Notion(auth=notion_token)
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # 1) Fetch & score news (last 24h)
    sections = fetch_feeds(DEFAULT_FEEDS, since_hours=24)
    scored_sections = {}
    for section, items in sections.items():
        prompt = DEFAULT_FEEDS[section].get("prompt", "")
        scored_sections[section] = score_items(client, items, prompt=prompt)

    # 2) Summaries + audio per section
    day_dir = f"{output_dir}/{date_str}"
    ensure_dir(day_dir)
    markdown_sections = []
    section_audio_urls = {}

    for section, scored in scored_sections.items():
        prompt = DEFAULT_FEEDS[section].get("prompt", "")
        summary_md = summarize_items(client, section, scored, max_items=5, prompt=prompt)
        markdown_sections.append(summary_md)

        # TTS
        mp3_bytes = tts_to_mp3_bytes(client, summary_md)
        mp3_path = f"{day_dir}/{section}.mp3"
        ogg_path = f"{day_dir}/{section}.ogg"
        save_bytes(mp3_path, mp3_bytes)
        ogg_bytes = mp3_to_ogg_bytes(mp3_bytes)
        save_bytes(ogg_path, ogg_bytes)

        section_audio_urls[section] = repo_raw_url(repo, branch, ogg_path)

    # 3) Roundup (importance-filtered across sections)
    # Flatten + filter
    flat = []
    for sec, items in scored_sections.items():
        for it in items:
            if it.get("importance", 0) >= importance_threshold:
                flat.append((sec, it))
    flat.sort(key=lambda t: t[1]["importance"], reverse=True)

    if flat:
        lines = ["## Roundup"]
        for sec, it in flat[:6]:
            date_s = it.get("published", "")[:10]
            lines.append(
                f"- **[{sec.title()}] {it['title']}** (Date: {date_s}, Score: {it['importance']})\n  {it['url']}"
            )
        roundup_md = "\n".join(lines)
    else:
        roundup_md = "## Roundup\n_No items met the importance threshold today._"

    # Put Roundup first in markdown
    markdown_sections.insert(0, roundup_md)

    # Roundup audio
    roundup_mp3 = tts_to_mp3_bytes(client, roundup_md)
    roundup_mp3_path = f"{day_dir}/roundup.mp3"
    roundup_ogg_path = f"{day_dir}/roundup.ogg"
    save_bytes(roundup_mp3_path, roundup_mp3)
    save_bytes(roundup_ogg_path, mp3_to_ogg_bytes(roundup_mp3))
    roundup_audio_url = repo_raw_url(repo, branch, roundup_ogg_path)

    # 4) Upsert Notion page & append content
    page = find_or_create_daily_page(notion, daily_db_id, date_str)
    page_id = page["page_id"]

    full_md = "\n\n".join(markdown_sections)
    append_markdown(notion, page_id, full_md)

    # Audio blocks: Roundup first, then sections
    append_audio(notion, page_id, "Roundup (High-importance only)", roundup_audio_url)
    for section, url in section_audio_urls.items():
        title = f"{section.replace('_',' ').title()} – Section Audio"
        append_audio(notion, page_id, title, url)

    # 5) Notify via Notion comment
    add_comment(notion, page_id, "✅ Daily news brief is ready – Roundup + section audios added.")


if __name__ == "__main__":
    main()
