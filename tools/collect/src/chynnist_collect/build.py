# SPDX-License-Identifier: GPL-3.0-or-later
"""Builds a signed Suvii collection from the pages the collector has stored and the list of documents."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from suvii import Document, SuviiError, Writer

from . import cards, rules
from .cards import Card
from .convert import Report, convert
from .state import State
from .styles import Styles
from .tree import ConvertError

REPORT_NAME = "build-report.json"
STYLES_NAME = "u_text.css"


@dataclass
class BuildReport:
    """Counts only: the report is safe to share, it holds no document text."""

    seq: int = 0
    documents: int = 0
    without_card: int = 0
    not_converted: dict[str, int] = field(default_factory=dict)  # error code -> documents
    with_images: int = 0
    dropped_links: int = 0
    unknown_kinds: dict[str, int] = field(default_factory=dict)  # portal type code -> documents
    unknown_classes: dict[str, int] = field(default_factory=dict)  # style class -> documents
    unknown_tags: dict[str, int] = field(default_factory=dict)
    unknown_tree_kinds: dict[str, int] = field(default_factory=dict)
    styles_found: bool = False


def _decode(page: bytes) -> str:
    """Pages of the portal are UTF-8; older ones may still come in Windows-1251."""
    try:
        return page.decode("utf-8")
    except UnicodeDecodeError:
        return page.decode(rules.CATALOG_ENCODING, errors="replace")


def _stamp(moment: float | None) -> str:
    return datetime.fromtimestamp(moment or 0, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_date(compact: str) -> str:
    return f"{compact[:4]}-{compact[4:6]}-{compact[6:]}"


def _facets(nreg: str, card: Card | None, unknown_kinds: Counter[str]) -> list[tuple[str, str]]:
    facets = [("number", nreg)]
    if card is None:
        return facets
    status = rules.STATUS_VALUES.get(card.status)
    if status is not None:
        facets.append(("status", status[0]))
    for code in dict.fromkeys(card.types):
        kind = rules.KIND_VALUES.get(code)
        if kind is not None:
            facets.append(("kind", kind[0]))
        else:
            unknown_kinds[str(code)] += 1
    if card.edition and card.edition[4:] != "0000":
        facets.append(("edition", _iso_date(card.edition)))
    return facets


def _document(
    nreg: str, fetched_at: float | None, page: bytes, card: Card | None, styles: Styles
) -> tuple[Document, Report]:
    converted = convert(_decode(page), nreg=nreg, styles=styles)
    # "updated" is when this text was taken from the portal: the edition date says nothing
    # about the time of day, and a reader compares these values to find newer copies.
    doc = Document(
        path=rules.doc_path(nreg),
        title=card.title if card and card.title else nreg,
        body=converted.body,
        updated=_stamp(fetched_at),
        toc=converted.toc,
    )
    return doc, converted.report


def build(
    state: State,
    work: Path,
    out: Path,
    key: Ed25519PrivateKey,
    *,
    source_date: str,
    test: bool = False,
) -> BuildReport:
    """Writes the collection to `out` and the report next to the state. Raises SuviiError, OSError."""
    css = work / STYLES_NAME
    styles = Styles.from_css(css.read_text(encoding="utf-8", errors="replace")) if css.exists() else Styles()
    catalog_file = work / "doc.txt"
    by_nreg = {card.nreg: card for card in cards.parse(catalog_file.read_bytes())[0]} if catalog_file.exists() else {}

    report = BuildReport(seq=state.next_build_seq(), styles_found=css.exists())
    counters: dict[str, Counter[str]] = {name: Counter() for name in ("kinds", "classes", "tags", "tree", "errors")}
    title = rules.COLLECTION_TITLE + (rules.TEST_TITLE_SUFFIX if test else "")
    with Writer(
        out,
        collection_id=rules.COLLECTION_ID,
        title=title,
        language="uk",
        publisher=rules.COLLECTION_PUBLISHER,
        fields=rules.collection_fields(),
        seq=report.seq,
        source_date=source_date,
        extra_meta={
            "collection.title.en": rules.COLLECTION_TITLE_EN,
            "collection.source": rules.COLLECTION_SOURCE,
            "collection.license": rules.COLLECTION_LICENSE,
            "collection.homepage": rules.COLLECTION_HOMEPAGE,
        },
    ) as writer:
        for nreg, fetched_at in state.stored():
            page = state.page(nreg)
            if page is None:
                counters["errors"]["unreadable"] += 1
                continue
            card = by_nreg.get(nreg)
            try:
                doc, page_report = _document(nreg, fetched_at, page, card, styles)
                doc.facets = _facets(nreg, card, counters["kinds"])
                writer.add(doc)
            except ConvertError as e:
                counters["errors"][e.code] += 1
                continue
            except SuviiError as e:
                counters["errors"]["format:" + e.code] += 1
                continue
            report.documents += 1
            report.without_card += card is None
            report.with_images += page_report.images > 0
            report.dropped_links += page_report.dropped_links
            counters["classes"].update(page_report.unknown_classes)
            counters["tags"].update(page_report.unknown_tags)
            counters["tree"].update(page_report.unknown_kinds)
        writer.finish(key)
    if not test:
        state.set_build_seq(report.seq)  # a trial build must not use up a number of the real ones
    report.not_converted = dict(counters["errors"].most_common())
    report.unknown_kinds = dict(counters["kinds"].most_common())
    report.unknown_classes = dict(counters["classes"].most_common())
    report.unknown_tags = dict(counters["tags"].most_common())
    report.unknown_tree_kinds = dict(counters["tree"].most_common())
    (work / REPORT_NAME).write_text(json.dumps(asdict(report), ensure_ascii=False, indent=1), encoding="utf-8")
    return report
