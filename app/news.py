from datetime import datetime, timedelta
from typing import List, Dict, Any, TypedDict
import feedparser
from dateutil import parser as dateparser
from openai import OpenAI


class FeedConfig(TypedDict):
    urls: List[str]
    prompt: str


DEFAULT_FEEDS: Dict[str, FeedConfig] = {
    "guardian": {
        "urls": [
            "https://www.theguardian.com/world/rss",
            "https://www.theguardian.com/uk/culture/rss",
            "https://www.theguardian.com/lifeandstyle/rss",
        ],
        "prompt": "Mix of world, culture, and lifestyle stories.",
    },
    "bbc": {
        "urls": [
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://feeds.bbci.co.uk/news/technology/rss.xml",
        ],
        "prompt": "Prioritize Scotland and broader UK coverage.",
    },
    "montreal_gazette": {
        "urls": [
            "https://montrealgazette.com/category/news/local-news/feed",
        ],
        "prompt": "Local Montreal news with civic impact.",
    },
    "ai": {
        "urls": [
            "https://feeds.arstechnica.com/arstechnica/ai",
            "https://www.techmeme.com/feed.xml",
        ],
        "prompt": "AI/tech developments relevant to startups.",
    },
}


SYSTEM_SUMMARY = (
    "You summarize news items for a busy founder in Montreal. "
    "Write crisp, factual bullets (2–3) for each article. "
    "Add (Date: YYYY-MM-DD). End each item with 'Why it matters' (one line)."
)

SYSTEM_SCORE = (
    "You are a news prioritization model. Score the IMPORTANCE of a news item from 0 to 100 "
    "for a busy founder in Montreal. Consider recency (last 24h), broad impact, "
    "business/tech relevance (esp. AI), Canada/Montreal relevance, and credibility. "
    "Return ONLY a JSON object: {\"score\": <0-100>, \"reason\": \"...\"}."
)


def parse_date(entry) -> datetime | None:
    for field in ("published", "updated"):
        if field in entry:
            try:
                return dateparser.parse(entry[field])
            except Exception:
                pass
    return None


def fetch_feeds(sources: Dict[str, FeedConfig], since_hours=24) -> Dict[str, List[Dict[str, Any]]]:
    cutoff = datetime.utcnow() - timedelta(hours=since_hours)
    result: Dict[str, List[Dict[str, Any]]] = {}
    for section, conf in sources.items():
        urls = conf["urls"]
        items: List[Dict[str, Any]] = []
        for url in urls:
            parsed = feedparser.parse(url)
            for e in parsed.entries:
                dt = parse_date(e)
                if dt is None or dt.replace(tzinfo=None) < cutoff:
                    continue
                items.append({
                    "title": e.get("title", "").strip(),
                    "url": e.get("link", "").strip(),
                    "summary": e.get("summary", ""),
                    "published": dt.isoformat() if dt else "",
                    "source": (
                        parsed.feed.title
                        if getattr(parsed, "feed", None) and parsed.feed.get("title")
                        else section
                    ),
                })
        # de-dupe by title+url
        seen = set()
        deduped = []
        for it in items:
            key = (it["title"], it["url"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(it)
        deduped.sort(key=lambda x: x["published"], reverse=True)
        result[section] = deduped
    return result


def chat_json(client: OpenAI, system_prompt: str, user_content: str) -> dict:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    import json

    try:
        return json.loads(resp.choices[0].message.content)
    except Exception:
        return {"score": 0, "reason": "Parse error"}


def score_items(client: OpenAI, items: List[Dict[str, Any]], prompt: str = "") -> List[Dict[str, Any]]:
    system = SYSTEM_SCORE + (f" Focus on: {prompt}" if prompt else "")
    scored = []
    for it in items:
        user = (
            f"Title: {it['title']}\n"
            f"URL: {it['url']}\n"
            f"Published: {it.get('published','')}\n"
            f"Summary: {it.get('summary','')}"
        )
        js = chat_json(client, system, user)
        it["importance"] = int(js.get("score", 0))
        it["importance_reason"] = js.get("reason", "")
        scored.append(it)
    scored.sort(key=lambda x: x.get("importance", 0), reverse=True)
    return scored


def summarize_items(
    client: OpenAI,
    section_name: str,
    items: List[Dict[str, Any]],
    max_items=5,
    prompt: str = "",
) -> str:
    system = SYSTEM_SUMMARY + (f" Focus on: {prompt}" if prompt else "")
    if not items:
        return f"## {section_name.title()}\n_No fresh items found._"
    lines = []
    for it in items[:max_items]:
        date_str = it.get("published", "")[:10]
        lines.append(f"- **{it['title']}** (Date: {date_str})\n  {it['url']}")
    user = "Summarize the following articles as bullet points for a quick brief:\n" + "\n".join(lines)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return f"## {section_name.title()}\n" + resp.choices[0].message.content.strip()


def tts_to_mp3_bytes(client: OpenAI, text: str) -> bytes:
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text,
        format="mp3",
    )
    return speech.content  # bytes
