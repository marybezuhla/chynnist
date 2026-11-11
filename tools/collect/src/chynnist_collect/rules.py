# SPDX-License-Identifier: GPL-3.0-or-later
"""Every limit and naming rule of the collector lives here, so that there is one place to check and change."""

from __future__ import annotations

import re
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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

# --- talking to the portal (its rules: data.rada.gov.ua/open/main/api/page3)

# Without registration the portal serves open data only to this client name.
USER_AGENT = "OpenData"
PORTAL_ORIGIN = "https://data.rada.gov.ua"
# The only hosts the collector may talk to; the portal redirects document pages to the second one.
FETCH_HOSTS = frozenset({"data.rada.gov.ua", "zakon.rada.gov.ua"})
# The portal asks for 5-7 seconds between requests. A random value does not look like an attack.
PAUSE_SECONDS = (5.0, 7.0)
# The portal blocks an address that ignores its rules. After the first refusal we stop for a day.
BLOCK_STATUSES = frozenset({403, 429})
BLOCK_SECONDS = 24 * 60 * 60
# The portal counts its daily limits by Kyiv time. Old time zone data knows only the second name.
DAY_ZONES = ("Europe/Kyiv", "Europe/Kiev")
# Portal limits are 100 000 requests and 200 MB a day; we use at most 90 %.
MAX_REQUESTS_PER_DAY = 90_000
MAX_BYTES_PER_DAY = 180_000_000
# One answer, as it comes over the network. Small enough that the answer that crosses our daily
# limit still leaves the day under the portal's 200 MB.
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
# An answer after unpacking (gzip); the same as the largest document a scroll can hold.
MAX_DECODED_BYTES = 64 * 1024 * 1024
MAX_REDIRECTS = 3
SOCKET_TIMEOUT_SECONDS = 90
RESPONSE_DEADLINE_SECONDS = 600
# After that many failures in a row the run ends: the network or the portal is down.
MAX_ERRORS_IN_ROW = 3
# ...and nothing is asked for a while. A portal that defends itself may drop connections instead
# of answering 403; knocking again every hour would only prolong that.
ERROR_REST_SECONDS = 3 * 60 * 60
# A document that failed that many times is left alone until someone looks at it.
MAX_DOC_FAILURES = 5
# A failed document is not asked for again sooner than this.
RETRY_SECONDS = 60 * 60

_ID = re.compile(r"^[A-Za-z0-9_.:-]+$")
_HTTP_DATE = re.compile(r"^[A-Z][a-z]{2}, \d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2} GMT$")
_HTTPS = re.compile(r"^https://[^\s<>\"'\\]+$")


def valid_id(value: str) -> bool:
    """Anchors are copied into `id` and into links, so they must be short and plain."""
    return 0 < len(value) <= MAX_ID_CHARS and _ID.match(value) is not None


def valid_http_date(value: str) -> bool:
    """A Last-Modified value is sent back to the portal in a header, so only the plain form is kept."""
    return _HTTP_DATE.match(value) is not None


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


def day_zone() -> ZoneInfo:
    for name in DAY_ZONES:
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            continue
    raise ZoneInfoNotFoundError(DAY_ZONES[0])


def show_url_path(nreg: str) -> str:
    """Where the portal serves the text of a document."""
    return "/laws/show/" + nreg
