# SPDX-License-Identifier: GPL-3.0-or-later
"""Keeps the queue in step with the portal's list of all documents."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import cards, rules
from .portal import Clock, Portal
from .state import State

FILE_NAME = "doc.txt"


class CatalogError(Exception):
    """The list cannot be used. `code` is one of: fresh, not_a_catalog, missing."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Summary:
    documents: int
    skipped_lines: int


def load(state: State, data: bytes, moment: float) -> Summary:
    """Puts every document of the list into the queue with its priority and current edition.

    A document whose edition has changed since it was downloaded waits in the queue again.
    """
    found, skipped = cards.parse(data)
    if len(found) < rules.MIN_CATALOG_ROWS:
        raise CatalogError("not_a_catalog")
    state.add_many((card.nreg, cards.priority(card), card.edition) for card in found)
    state.set_catalog_at(moment)
    return Summary(len(found), skipped)


def refresh(state: State, portal: Portal, clock: Clock, work: Path) -> Summary:
    """Downloads the list, if a week has passed since the last time, and loads it.

    Raises CatalogError, and whatever Portal.get raises (Stop, RequestFailed).
    """
    last = state.catalog_at()
    if last is not None and 0 <= clock.now() - last < rules.CATALOG_SECONDS:
        raise CatalogError("fresh")
    reply = portal.get(rules.CATALOG_URL_PATH, max_bytes=rules.MAX_CATALOG_BYTES)
    if reply.status != 200:
        raise CatalogError("missing")
    # The file is kept for the later build of the collection (titles, kinds, dates).
    # It replaces the old one only when it is whole and has passed the checks.
    partial = work / (FILE_NAME + ".part")
    partial.write_bytes(reply.body)
    try:
        summary = load(state, reply.body, clock.now())
    except CatalogError:
        partial.unlink()
        raise
    os.replace(partial, work / FILE_NAME)
    return summary
