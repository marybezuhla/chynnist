# SPDX-License-Identifier: GPL-3.0-or-later
"""Finds the structure of a document in its text: parts, chapters, articles.

Pages the portal gives to open-data clients carry no structure marks, only paragraphs. Laws are
written to a fixed pattern, though: a heading paragraph starts with "Розділ II", "Глава 3",
"§ 1.", "Стаття 12." and so on. This module recognises such paragraphs and nothing else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# From the largest unit to the smallest. A document uses only some of them; contents levels are
# given by rank among the kinds the document actually has.
KINDS = ("book", "section", "subsection", "chapter", "paragraph", "article")

_ROMAN_OR_NUMBER = r"(?:[IVXLC]+|\d+)(?:\s*-\s*\d+)?"
_HEADINGS = (
    ("book", re.compile(rf"^Книга\s+(?:{_ROMAN_OR_NUMBER}|[а-яіїєґ']+)\b", re.I)),
    ("section", re.compile(rf"^Розділ\s+{_ROMAN_OR_NUMBER}\b")),
    ("section", re.compile(r"^(?:ПРИКІНЦЕВІ|ПЕРЕХІДНІ)(?: ТА ПЕРЕХІДНІ)? ПОЛОЖЕННЯ\b")),
    ("subsection", re.compile(rf"^Підрозділ\s+{_ROMAN_OR_NUMBER}\b")),
    ("chapter", re.compile(rf"^Глава\s+{_ROMAN_OR_NUMBER}\b")),
    ("paragraph", re.compile(r"^§\s*\d+(?:\s*-\s*\d+)?\s?\.")),
)
# "Стаття 12." or "Стаття 131 - 1 ." (the portal writes the superscript number with spaces). The dot
# right after the number tells a heading from a sentence such as "Стаття 12 цього Закону ...".
ARTICLE = re.compile(r"^Стаття\s+\d+(?:\s*-\s*\d+)?\s?\.")
# A heading of a larger unit is short; a longer paragraph that starts the same way is text.
MAX_HEADING_CHARS = 300


@dataclass(frozen=True)
class Found:
    kind: str
    prefix: int  # characters of the heading label at the start, e.g. len("Стаття 12.")


def _mostly_upper(text: str) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    return bool(letters) and sum(ch.isupper() for ch in letters) >= 0.8 * len(letters)


def classify(first_line: str, whole: str) -> Found | None:
    """`first_line` is the text before the first line break, `whole` the paragraph as plain text."""
    article = ARTICLE.match(whole)
    if article:
        return Found("article", article.end())
    if len(whole) > MAX_HEADING_CHARS:
        return None
    for kind, pattern in _HEADINGS:
        found = pattern.match(first_line)
        if not found:
            continue
        rest = first_line[found.end() :].strip(" .")
        # "Глава 1" with the title on the next line, "§ 1. Господарські товариства",
        # "Розділ I ЗАГАЛЬНІ ЗАСАДИ" — but not "Розділ II цього Кодексу застосовується ...".
        if not rest or _mostly_upper(rest) or kind == "paragraph" or (first_line != whole and len(rest) < 40):
            return Found(kind, found.end())
    return None


def levels(kinds: set[str]) -> dict[str, int]:
    """Contents level of each kind present, 1 for the largest."""
    return {kind: rank for rank, kind in enumerate((k for k in KINDS if k in kinds), start=1)}
