# SPDX-License-Identifier: GPL-3.0-or-later
"""A forgiving HTML tree, built with the standard library only.

Portal pages are not strict HTML: inline elements wrap paragraphs, end tags are missing. The converter
needs a tree to carry formatting down into paragraphs, so this module builds one the way browsers do
for the few cases that matter, and never fails on bad markup.
"""

from __future__ import annotations

import unicodedata
from html.parser import HTMLParser

from . import rules

VOID = frozenset("area base br col embed hr img input link meta source track wbr".split())
_CLOSES_P = frozenset("address blockquote center div dl h1 h2 h3 h4 h5 h6 hr li ol p pre table ul".split())
_TABLE_PARTS = frozenset("table caption thead tbody tfoot tr td th".split())
_CELL_BARRIER = frozenset({"td", "th", "caption", "table"})


class ConvertError(Exception):
    """The page cannot be converted. `code` is stable and safe to log; it never holds page text."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class Node:
    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag: str, attrs: dict[str, str]) -> None:
        self.tag = tag
        self.attrs = attrs
        self.children: list[Node | str] = []


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("", {})
        self.stack = [self.root]

    def _close_open(self, targets: frozenset[str] | set[str], barriers: frozenset[str] | set[str]) -> None:
        """Closes the nearest open element from `targets`, unless a barrier element comes first."""
        for i in range(len(self.stack) - 1, 0, -1):
            tag = self.stack[i].tag
            if tag in targets:
                del self.stack[i:]
                return
            if tag in barriers:
                return

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _CLOSES_P:
            self._close_open({"p"}, _CELL_BARRIER)
        if tag == "tr":
            self._close_open({"tr"}, {"table"})
        elif tag in ("td", "th"):
            self._close_open({"td", "th"}, {"tr", "table"})
        elif tag == "li":
            self._close_open({"li"}, {"ul", "ol", "table"})
        node = Node(tag, {name: value or "" for name, value in attrs})
        self.stack[-1].children.append(node)
        if tag not in VOID:
            if len(self.stack) > rules.MAX_DEPTH:
                raise ConvertError("too_deep")
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        # A stray </p> or </em> inside a table cell must not close an element outside that cell.
        barriers = frozenset() if tag in _TABLE_PARTS else _CELL_BARRIER
        self._close_open({tag}, barriers)

    def handle_data(self, data: str) -> None:
        # Text is normalized piece by piece. Normalizing the whole page could merge a combining
        # mark with the ">" before it and so change the markup.
        self.stack[-1].children.append(unicodedata.normalize("NFC", data))


def parse(page: str) -> Node:
    builder = _Builder()
    builder.feed(page)
    builder.close()
    return builder.root


def find_by_id(root: Node, wanted: str) -> Node | None:
    todo = [root]
    while todo:
        node = todo.pop()
        if node.attrs.get("id") == wanted:
            return node
        todo.extend(child for child in reversed(node.children) if isinstance(child, Node))
    return None
