from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.news import clean_for_text, clean_for_tts


@pytest.fixture
def single_bullet_markdown():
    return "- **Title** (Date: 2025-09-22) read here"


@pytest.fixture
def multi_bullet_markdown():
    return "- Bullet one.\n\n- Bullet two with [Link](https://example.com).\n\n- Final item read here"


@pytest.mark.parametrize("fn", [clean_for_text, clean_for_tts])
def test_removes_date_parens(fn, single_bullet_markdown):
    out = fn(single_bullet_markdown)
    assert "(Date:" not in out


@pytest.mark.parametrize(
    "phrase",
    [
        "read here",
        "view here",
        "click here",
        "watch more",
        "listen here",
        "READ HERE",
        "View More",
    ],
)
@pytest.mark.parametrize("fn", [clean_for_text, clean_for_tts])
def test_removes_clickbait_phrases(fn, phrase):
    s = f"- Bullet. {phrase} for details."
    out = fn(s)
    assert phrase.lower() not in out.lower()


def test_markdown_links_preserve_anchor_text_text(multi_bullet_markdown):
    out = clean_for_text(multi_bullet_markdown)
    assert "[Link]" not in out
    assert "(https://example.com" not in out
    assert "- Bullet two with Link." in out


def test_markdown_links_preserve_anchor_text_tts():
    s = "- See [Great Piece](https://example.com/article)."
    out = clean_for_tts(s)
    assert "Great Piece" in out
    assert "http" not in out
    assert out.count("Great Piece") == 1


def test_strip_raw_urls_tts_only():
    s = "Read https://example.com now."
    assert "http" in clean_for_text(s)
    assert "http" not in clean_for_tts(s)


@pytest.mark.parametrize("provider", ["Guardian", "BBC", "guardian", "bbc"])
def test_section_intro_removed(provider):
    s = f"Hey Anton! News from {provider} – we have 3 articles\n\n- One\n- Two"
    out_text = clean_for_text(s)
    out_tts = clean_for_tts(s)
    assert "News from" not in out_text
    assert "News from" not in out_tts
    assert "- One" in out_text
    assert "- Two" in out_text
    assert "- One" in out_tts
    assert "- Two" in out_tts


@pytest.mark.parametrize("fn", [clean_for_text, clean_for_tts])
def test_whitespace_normalization(fn):
    s = "-  Bullet   one\n\n\n- Bullet   two  \n"
    out = fn(s)
    assert "  \n" not in out
    assert "\n\n\n" not in out
    assert out.endswith("Bullet   two") or out.endswith("Bullet two")


@pytest.mark.parametrize("fn", [clean_for_text, clean_for_tts])
def test_idempotent(fn, multi_bullet_markdown):
    once = fn(multi_bullet_markdown)
    twice = fn(once)
    assert once == twice


@pytest.mark.parametrize("fn", [clean_for_text, clean_for_tts])
def test_non_destructive_parentheses(fn):
    s = "- Budget (provisional) approved."
    out = fn(s)
    assert "provisional" in out
    assert "(" in out and ")" in out


@pytest.mark.parametrize("fn", [clean_for_text, clean_for_tts])
def test_non_destructive_words(fn):
    s = "Improved readability and viewfinder settings."
    out = fn(s)
    assert "readability" in out
    assert "viewfinder" in out


@pytest.mark.parametrize("fn", [clean_for_text, clean_for_tts])
def test_fixture_examples_cleaned(fn, single_bullet_markdown, multi_bullet_markdown):
    """Ensure representative fixtures already sanitized when cleaned."""
    out_single = fn(single_bullet_markdown)
    out_multi = fn(multi_bullet_markdown)
    assert "(Date:" not in out_single
    assert "read here" not in out_multi.lower()
    assert "http" not in out_multi if fn is clean_for_tts else True
