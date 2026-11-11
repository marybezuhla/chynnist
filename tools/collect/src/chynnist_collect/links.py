# SPDX-License-Identifier: GPL-3.0-or-later
"""Rewrites links of a portal page into the three kinds a Suvii document may hold (SPEC.md, 6.2)."""

from __future__ import annotations

import unicodedata
from urllib.parse import unquote, urlsplit

from . import rules

_SHOW_PREFIXES = ("/laws/show/", "/rada/show/")


def _nreg_from_path(path: str) -> str | None:
    for prefix in _SHOW_PREFIXES:
        if path.startswith(prefix):
            segments = [s for s in unquote(path[len(prefix):]).split("/") if s]
            while len(segments) > 1 and rules.VIEW_SEGMENT.match(segments[-1].lower()):
                segments.pop()
            return rules.normalize_nreg("/".join(segments))
    return None


def rewrite_href(href: str, own_nreg: str) -> str | None:
    """New value of `href`, or None when the link must become plain text.

    - `#anchor` stays (the converter later drops it if the anchor is missing);
    - a link to another document of the database becomes `suvii:laws/<nreg>#anchor`;
    - a link to this same document becomes `#anchor`;
    - any other https link stays; everything else (http, mailto, javascript) is dropped.
    """
    href = unicodedata.normalize("NFC", href.strip())
    if len(href) > rules.MAX_HREF_CHARS:
        return None
    if href.startswith("#"):
        return href if rules.valid_id(href[1:]) else None
    try:
        parts = urlsplit(href)
        host = (parts.hostname or "").lower()
    except ValueError:
        return None
    relative = not parts.scheme and not parts.netloc and parts.path.startswith("/")
    on_rada = relative or (parts.scheme in ("http", "https") and rules.RADA_HOST.match(host) is not None)
    if not on_rada:
        return href if parts.scheme == "https" and host and rules.valid_https(href) else None
    fragment = parts.fragment if rules.valid_id(parts.fragment) else ""
    if fragment == rules.PAGE_TOP_FRAGMENT:
        fragment = ""
    nreg = _nreg_from_path(parts.path)
    if nreg is None:
        absolute = rules.RADA_ORIGIN + parts.path + ("?" + parts.query if parts.query else "")
        return absolute if rules.valid_https(absolute) else None
    if nreg == own_nreg:
        # A link to the document itself is useful only with a place in it.
        return "#" + fragment if fragment else None
    return "suvii:" + rules.doc_path(nreg) + ("#" + fragment if fragment else "")
