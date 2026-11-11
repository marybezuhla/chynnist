# SPDX-License-Identifier: GPL-3.0-or-later
"""Blocks of a converted document and how they are written as the safe HTML subset of Suvii.

The output is canonical: the same text and formatting always give the same bytes, whatever the nesting
in the source was. That keeps document hashes stable, so weekly patches hold only real changes.
"""

from __future__ import annotations

import html
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import NamedTuple

# Order in which formatting elements are opened when several start at once (a link goes first).
_FLAG_ORDER = ("b", "i", "u", "s", "sub", "sup")


class Text(NamedTuple):
    text: str
    flags: frozenset[str]
    href: str | None


class Anchor(NamedTuple):
    id: str


class Break(NamedTuple):
    pass


Item = Text | Anchor | Break


@dataclass
class Para:
    tag: str  # "p" or "pre"
    align: str = ""
    id: str | None = None
    classes: list[str] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)

    def anchors(self) -> list[str]:
        own = [self.id] if self.id else []
        return own + [item.id for item in self.items if isinstance(item, Anchor)]

    def plain_text(self) -> str:
        parts = [item.text if isinstance(item, Text) else " " for item in self.items if not isinstance(item, Anchor)]
        return " ".join("".join(parts).split())


@dataclass
class Cell:
    tag: str  # "td" or "th"
    colspan: int
    rowspan: int
    blocks: list[Block]


@dataclass
class Table:
    rows: list[list[Cell]]


Block = Para | Table


def paragraphs(blocks: list[Block]) -> Iterator[Para]:
    """All paragraphs in reading order, including those inside tables."""
    for block in blocks:
        if isinstance(block, Para):
            yield block
        else:
            for row in block.rows:
                for cell in row:
                    yield from paragraphs(cell.blocks)


def _escape_text(text: str) -> str:
    out = html.escape(text, quote=False)
    if out and unicodedata.combining(out[0]):
        # A combining mark right after ">" could merge with it under NFC and break the markup.
        out = f"&#x{ord(out[0]):X};{out[1:]}"
    return out


def _wanted(item: Text, ids: set[str]) -> list[tuple[str, str]]:
    tags: list[tuple[str, str]] = []
    href = item.href
    if href is not None and href.startswith("#") and href[1:] not in ids:
        href = None  # the place it points to is not in this document
    if href is not None:
        tags.append(("a", f' href="{html.escape(href, quote=True)}"'))
    tags.extend((flag, "") for flag in _FLAG_ORDER if flag in item.flags)
    return tags


def _inline(items: list[Item], ids: set[str]) -> str:
    out: list[str] = []
    open_tags: list[tuple[str, str]] = []

    def close_to(depth: int) -> None:
        while len(open_tags) > depth:
            out.append(f"</{open_tags.pop()[0]}>")

    for item in items:
        if isinstance(item, Break):
            out.append("<br>")
        elif isinstance(item, Anchor):
            out.append(f'<span id="{html.escape(item.id, quote=True)}"></span>')
        else:
            wanted = _wanted(item, ids)
            # Keep open whatever this text still needs, so that an italic note with links inside
            # stays one <i> element instead of many short ones.
            keep = 0
            while keep < len(open_tags) and open_tags[keep] in wanted:
                keep += 1
            close_to(keep)
            for tag in wanted:
                if tag not in open_tags:
                    out.append(f"<{tag[0]}{tag[1]}>")
                    open_tags.append(tag)
            out.append(_escape_text(item.text))
    close_to(0)
    return "".join(out)


def _para(para: Para, ids: set[str]) -> str:
    attrs = f' id="{html.escape(para.id, quote=True)}"' if para.id else ""
    if para.classes:
        attrs += f' class="{" ".join(para.classes)}"'
    return f"<{para.tag}{attrs}>{_inline(para.items, ids)}</{para.tag}>"


def _table(table: Table, ids: set[str]) -> str:
    lines = ["<table>"]
    for row in table.rows:
        lines.append("<tr>")
        for cell in row:
            attrs = f' colspan="{cell.colspan}"' if cell.colspan > 1 else ""
            attrs += f' rowspan="{cell.rowspan}"' if cell.rowspan > 1 else ""
            lines.append(f"<{cell.tag}{attrs}>{render(cell.blocks, ids)}</{cell.tag}>")
        lines.append("</tr>")
    lines.append("</table>")
    return "\n".join(lines)


def render(blocks: list[Block], ids: set[str]) -> str:
    """One block per line. `ids` are the anchors that exist, to drop links that lead nowhere."""
    return "\n".join(_para(b, ids) if isinstance(b, Para) else _table(b, ids) for b in blocks)
