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

# --- the list of all documents (cards) and the order of the queue

# One file with a line for every document of the database, rewritten by the portal every hour.
CATALOG_URL_PATH = "/ogd/zak/laws/data/csv/doc.txt"
CATALOG_ENCODING = "cp1251"
CATALOG_FIELDS = 9  # dokid, nreg, nazva, status, types, organs, minjust, npix, datred
# The file is about 52 MB, a quarter of the day's allowance, so it is taken once a week at most.
MAX_CATALOG_BYTES = 64 * 1024 * 1024
CATALOG_SECONDS = 7 * 24 * 60 * 60
# The real file has about 289 000 lines. Much fewer means an error page or a cut file,
# and the queue must not be rebuilt from it.
MIN_CATALOG_ROWS = 100_000

# Codes of the portal's dictionaries typ.txt and stan.txt.
TYPE_CONSTITUTION = 216
TYPE_CODES = frozenset({21, 124})
TYPE_LAW = 1
TYPE_RESOLUTIONS_AND_DECREES = frozenset({2, 3})
# 1 lost force, 3 suspended, 6 never came into force, 7 not applied in Ukraine.
STATUS_NOT_IN_FORCE = frozenset({1, 3, 6, 7})
# Notices issued every working day. There are thousands of them and few people read old ones,
# so they are downloaded last.
DAILY_TITLES = ("Про офіційний курс гривні", "Про облікову ціну банківських металів")

# Order of the queue: a smaller number is downloaded earlier.
PRIORITY_CONSTITUTION = 0
PRIORITY_CODE = 1
PRIORITY_LAW = 2
PRIORITY_RESOLUTION_OR_DECREE = 3
PRIORITY_OTHER_IN_FORCE = 4
PRIORITY_NOT_IN_FORCE = 5
PRIORITY_DAILY = 6

# --- the collection (SPEC.md, appendix A)

COLLECTION_ID = "8e3b6c1a-5d2f-4b7e-9a41-2c6f0d8e7b53"  # the same for every base and patch, forever
COLLECTION_TITLE = "Законодавство України"
COLLECTION_TITLE_EN = "Legislation of Ukraine"
COLLECTION_PUBLISHER = "Chynnist"
COLLECTION_SOURCE = "https://data.rada.gov.ua"
COLLECTION_LICENSE = (
    "Дані Порталу відкритих даних Верховної Ради України: вільне використання та поширення "
    "з обов'язковим посиланням на джерело. Не є офіційним виданням."
)
COLLECTION_HOMEPAGE = "https://github.com/marybezuhla/chynnist"
TEST_TITLE_SUFFIX = " (пробна збірка)"

# --- publishing (INDEX.md)

RELEASES_URL = "https://github.com/marybezuhla/chynnist/releases/download/"
INDEX_FORMAT = "chynnist-index-1"
# Signed together with the index bytes, so that a signature can never be taken for another kind of message.
INDEX_SIG_PREFIX = b"chynnist-index-sig-1\n"
INDEX_TAG = "data"  # the one release that always holds the current index


def month_tag(month: str) -> str:
    """Release of one month's base and its patches, e.g. data-2026-11 (never v*, those are the app)."""
    return f"{INDEX_TAG}-{month}"


def base_file(seq: int) -> str:
    return f"chynnist-{seq}.suvii"


def patch_file(from_seq: int, to_seq: int) -> str:
    return f"chynnist-{from_seq}-{to_seq}.patch.suvii"


# Where the data signing key lives on the publisher's Mac (Keychain, generic password).
KEYCHAIN_SERVICE = "chynnist-data-key"
KEYCHAIN_ACCOUNT = "chynnist"

# Names of the portal's document states (stan.txt) as enum values of the `status` field.
STATUS_VALUES = {
    0: ("unknown", "Не визначено", "Not specified"),
    1: ("repealed", "Втратив чинність", "Repealed"),
    2: ("coming_into_force", "Набирає чинності", "Coming into force"),
    3: ("suspended", "Дію зупинено", "Suspended"),
    4: ("restored", "Дію відновлено", "Restored"),
    5: ("in_force", "Чинний", "In force"),
    6: ("not_in_force_yet", "Не набрав чинності", "Not yet in force"),
    7: ("not_applied", "Не застосовується на території України", "Not applied in Ukraine"),
    8: ("partly_in_force", "Частково набрав чинності", "Partly in force"),
    9: ("repealed_except", "Втратив чинність, крім окремих положень", "Repealed except some provisions"),
}
# Kinds known so far (typ.txt). Other codes are left out and counted in the build report;
# the full dictionary comes from the portal later.
KIND_VALUES = {
    1: ("law", "Закон", "Law"),
    2: ("resolution", "Постанова", "Resolution"),
    3: ("decree", "Указ", "Decree"),
    6: ("order", "Розпорядження", "Order"),
    9: ("ministry_order", "Наказ", "Ministerial order"),
    21: ("code_of_ukraine", "Кодекс України", "Code of Ukraine"),
    124: ("code", "Кодекс", "Code"),
    216: ("constitution", "Конституція України", "Constitution of Ukraine"),
}


def collection_fields() -> dict:
    """`collection.fields` of the collection (SPEC.md, 7)."""

    def enum(table: dict[int, tuple[str, str, str]]) -> dict:
        return {key: {"uk": uk, "en": en} for key, uk, en in table.values()}

    return {
        "kind": {"type": "enum", "title": {"uk": "Вид", "en": "Type"}, "multi": True, "values": enum(KIND_VALUES)},
        "status": {"type": "enum", "title": {"uk": "Стан", "en": "Status"}, "values": enum(STATUS_VALUES)},
        "number": {"type": "text", "title": {"uk": "Номер", "en": "Number"}},
        "edition": {"type": "date", "title": {"uk": "Редакція від", "en": "Edition of"}},
    }


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
