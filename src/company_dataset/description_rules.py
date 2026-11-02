"""What makes page text a company description, by where it came from.

A homepage's meta description and a vendor's own record are the company speaking for itself. Other
text on a page is often a slogan, a news item or an instruction to applicants, even when it is long
and names the company, so it must say what the company is, with the company as its subject.
"""
from __future__ import annotations

import re

from company_dataset.identity import _LEGAL_WORDS_FOR_NAMES, _fold

SUBJECT_WINDOW_CHARS = 60
# Text on these pages must describe the company. Everything else is judged by clean_description alone.
PARAGRAPH_METHODS = frozenset(("homepage_paragraph", "about_page_paragraph", "careers_page_paragraph", "board_page_paragraph"))
PAGE_META_METHODS = frozenset(("board_page_meta", "careers_page_meta", "about_page_meta"))
_DESCRIBING_RE = re.compile(
    r"\b(is|are|was|were)\s+(a|an|the|one of|our)\b"
    r"|\b(provides?|offers?|builds?|develops?|creates?|designs?|manufactures?|delivers?|specializ\w+|specialis\w+|serves?|helps?|enables?|empowers?|connects?|operates?)\b"
    r"|\b(is|are) (building|developing|revolutionizing|transforming|creating|leading|reinventing)\b"
    r"|\bfounded\b|\bestablished\b|\bour mission\b|\bmission is\b",
    re.I)


def _subject_words(name: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", _fold(name or "").lower()) if w not in _LEGAL_WORDS_FOR_NAMES]


def describes_company(text: str, name: str) -> bool:
    """The company is the subject, near the start, and the text says what it does or is."""
    words = _subject_words(name)
    if not words or not text:
        return False
    opening = _fold(text[:SUBJECT_WINDOW_CHARS]).lower()
    if not re.search(rf"\b{re.escape(words[0])}\b", opening):
        return False
    first_sentence = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    return bool(_DESCRIBING_RE.search(first_sentence)) and not re.match(r"^(news|location|update|press|posted|if\b)", first_sentence.strip(), re.I)


def acceptable(method: str, text: str, name: str) -> bool:
    if method in PARAGRAPH_METHODS or method in PAGE_META_METHODS:
        return describes_company(text, name)
    return True
