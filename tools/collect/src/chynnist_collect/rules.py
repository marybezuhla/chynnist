# SPDX-License-Identifier: GPL-3.0-or-later
"""Every limit and naming rule of the collector lives here, so that there is one place to check and change."""

from __future__ import annotations

import re
import unicodedata

# Documents of the "Legislation of Ukraine" database live under this path prefix (SPEC.md, appendix A).
PATH_PREFIX = "laws/"

# The site answers under several names (zakon2, zakon5 are old mirrors still found in links).
RADA_HOST = re.compile(r"^(?:www\.)?(?:zakon\d*|data)\.rada\.gov\.ua$")
RADA_ORIGIN = "https://zakon.rada.gov.ua"

# A document address may end with a view of the same document: an edition, a page, a print version.
# The collection keeps only the current edition, so such links lead to the document itself.
VIEW_SEGMENT = re.compile(r"^(?:ed\d{8}|paran\d+|page\d*|print\d*|conv)$")

# "#Text" is the top of a page on the portal, not a place in the document.
PAGE_TOP_FRAGMENT = "Text"

# Numbered style classes of the portal; one that is missing from our stylesheet copy is reported.
STYLE_CLASS = re.compile(r"^rv[pt]s\d+$")

# data-tree kinds that become entries of the table of contents, with their level.
TOC_LEVELS = {"rz": 1, "gl": 2, "st": 3}
# data-tree kind of an editorial note: "{Changed by law N ...}".
NOTE_KIND = "cm"
# Every data-tree kind seen so far. Anything else is reported, so that we notice new markup.
KNOWN_KINDS = frozenset({"nz", "rz", "gl", "st", "ch", "pu", "pp", "cm"})

CLASS_CENTER = "suvii-center"
CLASS_RIGHT = "suvii-right"
CLASS_NOTE = "suvii-note"

MAX_PAGE_CHARS = 64 * 1024 * 1024  # a page larger than a whole Suvii document cannot be stored anyway
MAX_DEPTH = 100  # nested elements; real pages stay under 20
MAX_ID_CHARS = 64
MAX_HREF_CHARS = 1024
MAX_SPAN = 1000  # colspan and rowspan
TOC_TITLE_CHARS = 200

_ID = re.compile(r"^[A-Za-z0-9_.:-]+$")
_HTTPS = re.compile(r"^https://[^\s<>\"'\\]+$")


def valid_id(value: str) -> bool:
    """Anchors are copied into `id` and into links, so they must be short and plain."""
    return 0 < len(value) <= MAX_ID_CHARS and _ID.match(value) is not None


def valid_https(url: str) -> bool:
    return len(url) <= MAX_HREF_CHARS and _HTTPS.match(url) is not None


def normalize_nreg(raw: str) -> str | None:
    """The document number as the portal writes it in its lists: lower case, NFC, one or two segments.

    Examples: `2341-14`, `254к/96-вр`, `64/2022`, `995_004`. Returns None for anything else.
    """
    nreg = unicodedata.normalize("NFC", raw).strip().lower()
    segments = nreg.split("/")
    if not 1 <= len(segments) <= 2:
        return None
    for segment in segments:
        if not segment or not all(ch.isalnum() or ch in "_.-" for ch in segment):
            return None
        if segment in (".", ".."):
            return None
    return nreg


def doc_path(nreg: str) -> str:
    return PATH_PREFIX + nreg
