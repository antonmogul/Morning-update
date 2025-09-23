from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, TypedDict, Optional
import logging
import re
import random
import feedparser
from dateutil import parser as dateparser
from openai import OpenAI

# Set up logging
logger = logging.getLogger(__name__)


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
        "prompt": "Global context with a cultural edge — world events, arts, lifestyle. Flag anything shaping people’s lives or ideas.",
    },
    "bbc": {
        "urls": [
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://feeds.bbci.co.uk/news/technology/rss.xml",
        ],
        "prompt": "Focus on Scotland, UK politics, and cultural currents. Highlight UK tech/business when it ties back to people or society.",
    },
    "montreal_news": {
        "urls": [
            "https://montreal.citynews.ca/feed/",
            "https://www.mtlblog.com/feeds/news.rss",
            "https://globalnews.ca/montreal/feed/",
        ],
        "prompt": "Montreal civic & cultural news; prioritize politics, immigration, and day-to-day quality-of-life shifts.",
    },
    "ai": {
        "urls": [
            "https://feeds.arstechnica.com/arstechnica/ai",
            "https://www.techmeme.com/feed.xml",
        ],
        "prompt": "Practical AI/tech developments that change how people work or live; useful for product strategy.",
    },
}


SYSTEM_SCORE = """
You are a news prioritization model for Anton Morrison (UX/AI strategist in Montreal, originally from Glasgow).
Score the IMPORTANCE of a news item from 0–100.

Priorities:
- Fresh (last 24h)
- Montreal/Canada relevance
- Scotland/UK connections
- Social, cultural, and human impact (immigration, community, people’s stories)
- AI/tech relevance, especially where it touches people’s lives
- Global events that change how people live or work

80% = quick awareness of essentials
20% = surprising human-interest insights

Return ONLY JSON:
{"score": <0-100>, "reason": "<1–2 lines, in the tone of a smart colleague, focusing on human/cultural impact>"}
"""

SYSTEM_SUMMARY = """
You summarize news items for Anton Morrison’s daily brief.
Write 2–3 short bullets per article. Keep them crisp, conversational, and scannable.
Do NOT include dates — Anton listens daily.
Do NOT include “read here”, “view here”, “click here”, or similar instructions.
End each item with: "Why it matters: ..." — one line, human/cultural impact first.

80% = must-know awareness
20% = human-interest enrichment
"""


def parse_date(entry) -> Optional[datetime]:
    """Parse date from RSS entry, trying multiple fields.
    
    Args:
        entry: RSS feed entry
        
    Returns:
        Parsed datetime or None if parsing fails
    """
    for field in ("published", "updated"):
        if field in entry:
            try:
                return dateparser.parse(entry[field])
            except Exception as e:
                logger.debug(f"Failed to parse date from {field}: {e}")
    return None


def fetch_feeds(sources: Dict[str, FeedConfig], since_hours=24) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch and parse RSS feeds from configured sources.
    
    Args:
        sources: Dictionary mapping section names to feed configurations
        since_hours: Only include items published within this many hours
        
    Returns:
        Dictionary mapping section names to lists of news items
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    cutoff = cutoff.replace(tzinfo=None)  # Make cutoff timezone naive for comparison
    result: Dict[str, List[Dict[str, Any]]] = {}
    
    for section, conf in sources.items():
        urls = conf["urls"]
        items: List[Dict[str, Any]] = []
        
        for url in urls:
            try:
                logger.info(f"Fetching feed: {url}")
                parsed = feedparser.parse(url)
                
                # Check if feed parsing had issues
                if parsed.bozo:
                    logger.warning(f"Feed parsing warning for {url}: {parsed.bozo_exception}")
                
                # Process entries even if there were parsing warnings
                for e in parsed.entries:
                    dt = parse_date(e)
                    if dt is None:
                        continue
                    # Convert to naive UTC for comparison
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                    if dt < cutoff:
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
                    
                logger.info(f"Successfully fetched {len(parsed.entries)} entries from {url}")
                
            except Exception as e:
                logger.error(f"Failed to fetch feed {url}: {e}")
                # Continue with other feeds rather than failing entirely
                continue
        
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
        
        logger.info(f"Section '{section}': {len(deduped)} unique items after deduplication")
    
    return result


def chat_json(client: OpenAI, system_prompt: str, user_content: str) -> dict:
    """Call OpenAI chat API and parse JSON response.
    
    Args:
        client: OpenAI client instance
        system_prompt: System message for the model
        user_content: User message content
        
    Returns:
        Parsed JSON response or error fallback
    """
    import json
    
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        
        parsed = json.loads(resp.choices[0].message.content)
        return parsed
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        return {"score": 0, "reason": "JSON parse error"}
    except Exception as e:
        logger.error(f"API call failed: {e}")
        return {"score": 0, "reason": f"API error: {str(e)[:100]}"}


def score_items(client: OpenAI, items: List[Dict[str, Any]], prompt: str = "") -> List[Dict[str, Any]]:
    """Score news items for importance using OpenAI.
    
    Args:
        client: OpenAI client instance
        items: List of news items to score
        prompt: Additional context for scoring
        
    Returns:
        List of items with importance scores added
    """
    system = SYSTEM_SCORE + (f" Focus on: {prompt}" if prompt else "")
    scored = []
    
    for idx, it in enumerate(items):
        try:
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
            
        except Exception as e:
            logger.error(f"Failed to score item {idx}: {e}")
            # Add with low score rather than failing
            it["importance"] = 0
            it["importance_reason"] = "Scoring failed"
            scored.append(it)
    
    scored.sort(key=lambda x: x.get("importance", 0), reverse=True)
    logger.info(f"Scored {len(scored)} items")
    return scored


def summarize_items(
    client: OpenAI,
    section_name: str,
    items: List[Dict[str, Any]],
    max_items=5,
    prompt: str = "",
    name: str = "Anton",
) -> str:
    """Generate summary of news items using OpenAI.
    
    Args:
        client: OpenAI client instance
        section_name: Name of the news section
        items: List of news items to summarize
        max_items: Maximum number of items to include
        prompt: Additional context for summarization
        
    Returns:
        Markdown formatted summary
    """
    system = SYSTEM_SUMMARY + (f" Focus on: {prompt}" if prompt else "")
    
    if not items:
        return f"## {section_name.title()}\n_No fresh items found._"
    
    # Count articles for intro
    article_count = len(items[:max_items])
    section_display = section_name.replace('_', ' ').title()
    
    # Get section emoji
    section_emojis = {
        "guardian": "🏛️",
        "bbc": "📺", 
        "montreal_news": "🍁",
        "ai": "🤖"
    }
    emoji = section_emojis.get(section_name.lower(), "📰")
    
    # Personal intro with emoji matching template 3
    article_word = "compelling article" if article_count == 1 else "articles"
    if article_count >= 3:
        article_word = f"compelling {article_word}"
    intro = f"{emoji} {section_display} highlights — {article_count} {article_word} teed up.\n\n"
    
    try:
        lines = []
        for it in items[:max_items]:
            # Don't include URLs in the summary request
            lines.append(f"- **{it['title']}**")

        user = (
            "Summarize the following articles as conversational bullet points for Anton Morrison’s daily brief.\n"
            "Keep it tight and scannable, like a smart colleague explaining.\n"
            "Do not include dates, links, or phrases like “read more”, “view here”, “click here”.\n"
            "Avoid repeating section names (e.g., Guardian, BBC) in every bullet — keep it varied.\n\n"
            + "\n".join(lines)
        )
        
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        
        summary_text = resp.choices[0].message.content.strip()
        # Remove any URLs from the summary
        summary_text = re.sub(r'https?://[^\s]+', '', summary_text)
        
        logger.info(f"Generated summary for section '{section_name}' with {len(items[:max_items])} items")
        return f"## {section_name.title()}\n{intro}" + summary_text
        
    except Exception as e:
        logger.error(f"Failed to generate summary for section '{section_name}': {e}")
        # Return a basic summary as fallback
        return f"## {section_name.title()}\n_Summary generation failed. {len(items)} items available._"


def tts_to_mp3_bytes(client: OpenAI, text: str, voice: Optional[str] = None) -> bytes:
    """Convert text to MP3 audio using OpenAI TTS.
    
    Args:
        client: OpenAI client instance
        text: Text to convert to speech
        
    Returns:
        MP3 audio data as bytes
        
    Raises:
        Exception: If TTS generation fails
    """
    # Rotate through available voices for variety
    voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    if voice is None:
        voice = random.choice(voices)
    
    # Remove URLs from text before TTS
    clean_text = re.sub(r'https?://[^\s]+', '', text)
    
    try:
        speech = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=clean_text
        )
        logger.info(f"Generated TTS audio for {len(clean_text)} characters using voice '{voice}'")
        return speech.content  # bytes
        
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise


def generate_morning_intro(
    client: OpenAI,
    sections_summary: Dict[str, int],
    name: str = "Anton",
    location: str = "Montreal"
) -> str:
    """Generate a personalized morning intro with weather, zen quote, and overview.
    
    Args:
        client: OpenAI client instance
        sections_summary: Dictionary mapping section names to article counts
        name: User's name for personalization
        location: Location for weather context
        
    Returns:
        Personalized intro text for TTS
    """
    # Create overview of news sections
    overview_parts = []
    for section, count in sections_summary.items():
        section_display = section.replace('_', ' ').title()
        if count > 0:
            article_word = "article" if count == 1 else "articles"
            if count >= 3:
                overview_parts.append(f"{count} interesting {article_word} from {section_display}")
            else:
                overview_parts.append(f"{count} {article_word} from {section_display}")
    
    overview = ", ".join(overview_parts) if overview_parts else "No major news today"
    
    # Generate personalized intro with AI using the updated template
    sections_hint = overview if overview_parts else "Keep it light; no major sections today."
    prompt = f"""Create a warm, sharp morning intro for Anton Morrison (UX/AI strategist in Montreal, originally from Glasgow).

Format EXACTLY:

🌅 Good morning Anton! Here’s what’s worth knowing today.

🧘 Zen moment: [short, human-centered quote about clarity or presence]

📊 Quick scan: [overview of sections, no repetitive provider naming]

👥 Human touch: [one person-focused nugget]

Tone = smart colleague: helpful, concise, a little conversational, not formal or corporate.

Sections overview to reference: {sections_hint}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": "You are a warm, friendly morning news host creating a personalized daily intro.",
                },
                {"role": "user", "content": prompt}
            ]
        )
        
        intro_text = response.choices[0].message.content.strip()
        logger.info(f"Generated morning intro for {name}")
        return intro_text
        
    except Exception as e:
        logger.error(f"Failed to generate morning intro: {e}")
        # Fallback intro matching template 3 style
        return (
            "🌅 Good morning Anton! Here’s what’s worth knowing today.\n\n"
            "🧘 Zen moment: \"The present moment is the only moment available to us, and it is the door to all moments.\"\n\n"
            f"📊 Quick scan: {sections_hint}\n\n"
            "👥 Human touch: Spotlighting one neighbourly story to start your day."
        )


CLEAN_PHRASES = re.compile(
    r"\b(?:read|view|click|watch|listen)\s+(?:here|more)\b",
    flags=re.IGNORECASE
)

DATE_PARENS = re.compile(
    r"\(Date:\s*\d{4}-\d{2}-\d{2}\)"
)

# Remove Markdown links but keep anchor text: [text](url) -> text
MARKDOWN_LINK = re.compile(
    r"\[([^\]]+)\]\((?:https?://|www\.)[^\s)]+\)"
)

# Remove repeated "News from Guardian/BBC..." intros at the top of a section block
SECTION_INTRO = re.compile(
    r"^\s*(?:[^\n]*?News from\s+(?:Guardian|BBC)[^\n]*\n\n)",
    flags=re.IGNORECASE | re.MULTILINE
)

# Collapse excess whitespace/newlines
MULTISPACE = re.compile(r"[ \t]{2,}")
MULTINEWLINE = re.compile(r"\n{3,}")


def clean_for_text(markdown: str) -> str:
    """Cleanup for Notion text blocks (keeps bullets/headings, removes noise)."""

    s = markdown
    s = DATE_PARENS.sub("", s)
    s = CLEAN_PHRASES.sub("", s)
    s = MARKDOWN_LINK.sub(r"\1", s)
    s = SECTION_INTRO.sub("", s)
    s = re.sub(r"[ \t]+\n", "\n", s)  # trim trailing spaces before newline
    s = MULTISPACE.sub(" ", s)
    s = MULTINEWLINE.sub("\n\n", s)
    return s.strip()


def clean_for_tts(text: str) -> str:
    """Cleanup for speech: stricter; remove links, provider intros, and instrux."""

    s = text
    # Strip any raw URLs first (existing behavior is inside tts_to_mp3_bytes, this makes it idempotent)
    s = re.sub(r"https?://[^\s]+", "", s)
    s = MARKDOWN_LINK.sub(r"\1", s)
    s = DATE_PARENS.sub("", s)
    s = CLEAN_PHRASES.sub("", s)
    s = SECTION_INTRO.sub("", s)
    s = MULTISPACE.sub(" ", s)
    s = MULTINEWLINE.sub("\n", s)
    return s.strip()
