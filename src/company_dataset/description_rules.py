"""What makes page text a company description, by where it came from.

A homepage's meta description and a vendor's own record are the company speaking for itself. Other
text on a page is often a slogan, a news item, a staff bio or benefits copy, even when it is long and
names the company. So it must open with the company as the subject of a sentence saying what it is
or does. Careers pages and hosted-board meta are about employment and are not used at all: samples
of them were mostly benefits, slogans and recruiting copy.
"""
from __future__ import annotations

import re

from company_dataset.identity import _LEGAL_WORDS_FOR_NAMES, _fold

NEVER_USED_METHODS = frozenset(("careers_page_paragraph", "careers_page_meta", "board_page_meta"))
SUBJECT_METHODS = frozenset(("homepage_paragraph", "about_page_paragraph", "board_page_paragraph", "about_page_meta"))
_LEGAL_ENDINGS = _LEGAL_WORDS_FOR_NAMES - {"the", "and", "of"}
_VERB = (r"(is|are|was|were|provides?|offers?|builds?|develops?|creates?|designs?|manufactures?|delivers?|specializes?|specialises?|serves?|helps?|enables?"
         r"|empowers?|connects?|operates?|partners?|exists?|makes?|leverages?|invests?)")
_LEAD_IN = r"(?:(?:founded|established|launched|started|headquartered|based)\b[^,]{0,60},\s*|since\b[^,]{0,30},\s*)?"
_LEGAL_TAIL = r"(?:,?\s*&?\s*(?:company|co|inc|incorporated|llc|llp|ltd|limited|corp|corporation|gmbh|plc)\b\.?)*"
_NOT_A_DESCRIPTION_RE = re.compile(
    r"\b(place to work|benefits?|bonus|compensation|salary|pto|medical plans?|rotation program|program open|will host|hackathon|employee turnover|is hiring|is looking|is providing)\b", re.I)
_RECRUITING_OPENER_RE = re.compile(r"(are you\b|do you\b|want to\b|looking (for|to)\b|watch\b|join\b|work (with|for|at)\b|come\b|why\b)", re.I)
_JOB_AD_RE = re.compile(
    r"\b(you are|urgently|requires? the services|(?:is|are|currently) (?:looking|seeking)|we(?: are|'re) hiring|apply now|job openings?|vacanc(?:y|ies)"
    r"|envie de|carri[eè]re|nous recherchons|recrute|rejoign\w+|vous r[eê]vez|bieten wir dir|wir suchen|teilzeit|vollzeit|estamos buscando|[uú]nete|cerchiamo"
    r"|hey\s+\w+\s+\w+!|wij zoeken|solliciteer|is hiring|are hiring|job description|per hour|looking for a|calling all|estamos [aà] procura)", re.I)
_DECORATED_OPENER_RE = re.compile(r"^[^\w\s\"'“‘(]")
_SIGNATURE_RE = re.compile(r"\|.*\b(direct|ext|suite)\b|\bsuite #|\d{3}-\d{3}-\d{4}", re.I)


def _tokens(name: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _fold(name or "").lower())


def _subject_patterns(name: str) -> list[str]:
    """The full name without its legal ending, and its first distinctive word."""
    tokens = _tokens(name)
    while tokens and tokens[0] == "the":
        tokens = tokens[1:]
    while tokens and tokens[-1] in _LEGAL_ENDINGS:
        tokens = tokens[:-1]
    if not tokens:
        return []
    return list(dict.fromkeys([r"\W+".join(map(re.escape, tokens)), re.escape(tokens[0])]))


def describes_company(text: str, name: str) -> bool:
    """The first sentence opens with the company as subject of a verb saying what it is or does,
    or opens "At <company>, we ...". "Propel America's pathway" and "Sri is a co-founder" do not."""
    if not text or _NOT_A_DESCRIPTION_RE.search(text):
        return False
    sentence = _fold(re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]).lower().replace("’", "'")
    for subject in _subject_patterns(name):
        direct = rf"^{_LEAD_IN}(?:the\s+)?{subject}(?:\.\w+)?{_LEGAL_TAIL}(?:\s*\([^)]*\))?(?:,[^,]{{0,80}},)?\s+{_VERB}\b"
        team = rf"^at\s+(?:the\s+)?{subject}{_LEGAL_TAIL},\s+(we|we're|we are|our)\b"
        if re.search(direct, sentence) or re.search(team, sentence):
            return True
    return False


def _about_account_holder(text: str, name: str) -> bool:
    """SmartRecruiters' field is filled per posting, so agencies put their client's text in it."""
    tokens = [t for t in _tokens(name) if t not in _LEGAL_WORDS_FOR_NAMES]
    opening = (text or "").strip()
    if not tokens or _SIGNATURE_RE.search(opening) or _RECRUITING_OPENER_RE.match(opening) or _JOB_AD_RE.search(opening) or _DECORATED_OPENER_RE.match(opening):
        return False
    return re.search(rf"\b{re.escape(tokens[0])}\b", _fold(text or "").lower()) is not None


def acceptable(method: str, text: str, name: str) -> bool:
    if method in NEVER_USED_METHODS:
        return False
    if method in SUBJECT_METHODS:
        return describes_company(text, name)
    if method == "smartrecruiters_company_description":
        return _about_account_holder(text, name)
    return True
