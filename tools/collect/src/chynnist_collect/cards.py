# SPDX-License-Identifier: GPL-3.0-or-later
"""Reads the portal's list of all documents and decides in which order to download them.

The list (doc.txt) is a tab-separated table in Windows-1251 with one line for a document:
dokid, nreg, nazva, status, types, organs, minjust, npix, datred. Several values of one field are
separated with "|". Only the fields the queue needs are read here.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass

from . import rules


@dataclass(frozen=True)
class Card:
    nreg: str
    title: str
    status: int  # code of stan.txt
    types: tuple[int, ...]  # codes of typ.txt
    edition: str  # date of the current edition, YYYYMMDD, or ""


def _numbers(field: str) -> tuple[int, ...] | None:
    values = [part for part in field.split("|") if part]
    if not all(part.isascii() and part.isdigit() for part in values):
        return None
    return tuple(int(part) for part in values)


def _card(line: str) -> Card | None:
    fields = line.split("\t")
    if len(fields) < rules.CATALOG_FIELDS:
        return None
    _dokid, raw_nreg, title, status, types, _organs, _minjust, _npix, edition = fields[: rules.CATALOG_FIELDS]
    nreg = rules.normalize_nreg(raw_nreg)
    type_codes = _numbers(types)
    edition = edition.strip()
    if nreg is None or type_codes is None or not (status.isascii() and status.isdigit()):
        return None
    if edition and not (len(edition) == 8 and edition.isascii() and edition.isdigit()):
        return None
    return Card(nreg, unicodedata.normalize("NFC", title.strip()), int(status), type_codes, edition)


def parse(data: bytes) -> tuple[list[Card], int]:
    """Cards of the list and the number of lines that could not be read."""
    cards: list[Card] = []
    skipped = 0
    for number, raw in enumerate(_lines(data)):
        card = _card(raw.decode(rules.CATALOG_ENCODING, errors="replace"))
        if card is not None:
            cards.append(card)
        elif number > 0 or raw[:1].isdigit():
            skipped += 1  # the first line may be a heading, that is not an error
    return cards, skipped


def _lines(data: bytes) -> Iterator[bytes]:
    for line in data.split(b"\n"):
        line = line.rstrip(b"\r")
        if line.strip():
            yield line


def priority(card: Card) -> int:
    """Place in the queue: what people open most comes first."""
    if card.title.startswith(rules.DAILY_TITLES):
        return rules.PRIORITY_DAILY
    if card.status in rules.STATUS_NOT_IN_FORCE:
        return rules.PRIORITY_NOT_IN_FORCE
    types = set(card.types)
    if rules.TYPE_CONSTITUTION in types:
        return rules.PRIORITY_CONSTITUTION
    if types & rules.TYPE_CODES:
        return rules.PRIORITY_CODE
    if rules.TYPE_LAW in types:
        return rules.PRIORITY_LAW
    if types & rules.TYPE_RESOLUTIONS_AND_DECREES:
        return rules.PRIORITY_RESOLUTION_OR_DECREE
    return rules.PRIORITY_OTHER_IN_FORCE
