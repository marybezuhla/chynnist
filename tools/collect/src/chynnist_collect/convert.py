# SPDX-License-Identifier: GPL-3.0-or-later
"""Converts the text of a portal page into a Suvii document body with a table of contents.

What is kept: paragraphs, tables, preformatted text, bold/italic/underline/strike/sub/sup, links,
anchors (`<a name>` becomes `id`), structure marks (`data-tree` becomes the table of contents).
What is dropped: scripts, styles, images, layout attributes, everything outside the safe subset.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace

from suvii import TocEntry

from . import rules
from .links import rewrite_href
from .render import (
    Anchor,
    Block,
    Break,
    Cell,
    Item,
    Para,
    Table,
    Text,
    paragraphs,
    render,
)
from .styles import ClassStyle, Styles
from .tree import ConvertError, Node, find_by_id, parse

_INLINE_FLAGS = {
    "b": "b", "strong": "b", "i": "i", "em": "i", "u": "u", "ins": "u",
    "s": "s", "strike": "s", "del": "s", "sub": "sub", "sup": "sup",
}  # fmt: skip
_PLAIN_INLINE = frozenset({"span", "font", "small", "big", "nobr", "wbr", "abbr", "cite", "code", "tt"})
_HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_PARA_TAGS = _HEADINGS | {"p", "pre", "li", "dt", "dd", "caption"}
_CONTAINERS = frozenset(
    "div blockquote center ul ol dl hr section article main body html thead tbody tfoot tr td th".split()
)
_DROPPED = frozenset(
    "script style head title link meta noscript iframe object embed svg math template "
    "input select textarea button canvas audio video map area col colgroup".split()
)
_ROW_GROUPS = frozenset({"thead", "tbody", "tfoot"})
# Lists are written as plain paragraphs, so automatic numbers and bullets are lost. They are
# reported like unknown elements: if real documents use them, they need proper support.
_NOT_FAITHFUL = frozenset({"ul", "ol", "li", "dl", "dt", "dd"})

# Collapsible white space. A no-break space is not in the list: it is meaningful ("ст. 5").
_SPACE = re.compile(r"[ \t\n\r\f\v]+")
_HIDDEN = re.compile(r"display\s*:\s*none")
_KIND = re.compile(r"[a-z]+")


@dataclass(frozen=True)
class Report:
    """What the collector logs about a converted page. Holds counts and markup names, never text."""

    text_chars: int
    images: int
    dropped_links: int
    unknown_kinds: tuple[str, ...]
    unknown_classes: tuple[str, ...]
    unknown_tags: tuple[str, ...]  # elements not known or not written faithfully (lists)


@dataclass(frozen=True)
class Converted:
    body: str
    toc: list[TocEntry]
    report: Report


@dataclass(frozen=True)
class _Format:
    flags: frozenset[str] = frozenset()
    href: str | None = None
    align: str = ""


def _has_text(items: list[Item]) -> bool:
    return any(isinstance(item, Text) and item.text.strip("  \n\t") for item in items)


def _strip_last_text(items: list[Item]) -> None:
    """Removes the space before a line end."""
    for i in range(len(items) - 1, -1, -1):
        item = items[i]
        if isinstance(item, Break):
            return
        if isinstance(item, Text):
            text = item.text.rstrip(" ")
            if text:
                items[i] = item._replace(text=text)
            else:
                del items[i]
            return


def _tidy(items: list[Item]) -> list[Item]:
    """Collapses white space across formatting borders and removes empty lines at both ends."""
    out: list[Item] = []
    at_line_start = True
    for item in items:
        if isinstance(item, Text):
            text = _SPACE.sub(" ", item.text)
            if at_line_start:
                text = text.lstrip(" ")
            if text:
                at_line_start = text.endswith(" ")
                out.append(item._replace(text=text))
        elif isinstance(item, Break):
            _strip_last_text(out)
            out.append(item)
            at_line_start = True
        else:
            out.append(item)
    _strip_last_text(out)
    texts = [i for i, item in enumerate(out) if isinstance(item, Text)]
    if not texts:
        return [item for item in out if isinstance(item, Anchor)]
    first, last = texts[0], texts[-1]
    return [item for i, item in enumerate(out) if first <= i <= last or isinstance(item, Anchor)]


def _tidy_pre(items: list[Item]) -> list[Item]:
    """Preformatted text keeps its spaces and line ends; a line break element becomes a line end."""
    out: list[Item] = []
    for item in items:
        if isinstance(item, Break):
            item = Text("\n", frozenset(), None)
        elif isinstance(item, Text):
            item = item._replace(text=item.text.replace("\r\n", "\n").replace("\r", "\n"))
        out.append(item)
    texts = [i for i, item in enumerate(out) if isinstance(item, Text)]
    if texts:
        first, last = texts[0], texts[-1]
        # Browsers ignore one line end right after <pre>; do the same so the text does not shift.
        out[first] = out[first]._replace(text=out[first].text.removeprefix("\n"))
        out[last] = out[last]._replace(text=out[last].text.rstrip())
    return [item for item in out if not isinstance(item, Text) or item.text]


def _span(value: str) -> int:
    return int(value) if value.isascii() and value.isdigit() and 1 <= int(value) <= rules.MAX_SPAN else 1


class _Converter:
    def __init__(self, nreg: str, styles: Styles) -> None:
        self.nreg = nreg
        self.styles = styles
        self.containers: list[list[Block]] = [[]]
        self.para: Para | None = None
        self.pending: list[str] = []  # anchors waiting for the next paragraph with text
        self.ids: set[str] = set()
        self.kind_of: dict[str, str] = {}
        self.images = 0
        self.dropped_links = 0
        self.unknown_kinds: set[str] = set()
        self.unknown_classes: set[str] = set()
        self.unknown_tags: set[str] = set()

    # --- formatting of one element

    def _style(self, node: Node) -> ClassStyle:
        flags: set[str] = set()
        align = node.attrs.get("align", "").lower()
        hidden = _HIDDEN.search(node.attrs.get("style", "").lower()) is not None
        for name in node.attrs.get("class", "").split():
            style = self.styles.get(name)
            if style is None:
                if rules.STYLE_CLASS.match(name):
                    self.unknown_classes.add(name)
                continue
            flags |= style.flags
            align = style.align or align
            hidden = hidden or style.hidden
        return ClassStyle(frozenset(flags), align if align in ("center", "right") else "", hidden)

    # --- paragraphs

    def _open(self, tag: str, align: str) -> Para:
        self._close()
        self.para = Para(tag=tag, align=align)
        return self.para

    def _close(self) -> None:
        para, self.para = self.para, None
        if para is None:
            return
        items = _tidy_pre(para.items) if para.tag == "pre" else _tidy(para.items)
        if not _has_text(items):
            # An empty paragraph is dropped, but links may point at its anchors: pass them on.
            self.pending.extend(item.id for item in items if isinstance(item, Anchor))
            return
        first_text = next(i for i, item in enumerate(items) if isinstance(item, Text))
        leading = self.pending + [item.id for item in items[:first_text] if isinstance(item, Anchor)]
        self.pending = []
        if leading:
            para.id = leading[0]
        para.items = [Anchor(a) for a in leading[1:]] + items[first_text:]
        if para.align == "center":
            para.classes.append(rules.CLASS_CENTER)
        elif para.align == "right":
            para.classes.append(rules.CLASS_RIGHT)
        if para.id and self.kind_of.get(para.id) == rules.NOTE_KIND:
            para.classes.append(rules.CLASS_NOTE)
        self.containers[-1].append(para)

    def _text(self, text: str, fmt: _Format) -> None:
        if self.para is None:
            if not text.strip():
                return  # white space between blocks
            self._open("p", fmt.align)
        assert self.para is not None
        self.para.items.append(Text(text, fmt.flags, fmt.href))

    def _anchor(self, name: str, tree: str) -> None:
        if not rules.valid_id(name) or name in self.ids:
            return
        self.ids.add(name)
        kind = _KIND.match(tree.split(":")[0])
        if kind:
            self.kind_of[name] = kind.group()
            if kind.group() not in rules.KNOWN_KINDS:
                self.unknown_kinds.add(kind.group())
        if self.para is not None:
            self.para.items.append(Anchor(name))
        else:
            self.pending.append(name)

    # --- elements

    def _link(self, node: Node, fmt: _Format) -> None:
        name = node.attrs.get("name") or node.attrs.get("id")
        if name:
            self._anchor(name, node.attrs.get("data-tree", ""))
        if "href" in node.attrs:
            href = rewrite_href(node.attrs["href"], self.nreg)
            if href is None:
                self.dropped_links += 1
            fmt = replace(fmt, href=href)
        self._walk(node, fmt)

    def _paragraph(self, node: Node, fmt: _Format, style: ClassStyle) -> None:
        if node.tag in _HEADINGS:
            fmt = replace(fmt, flags=fmt.flags | {"b"})
        self._open("pre" if node.tag == "pre" else "p", style.align or fmt.align)
        self._walk(node, fmt)
        self._close()

    def _rows(self, table: Node, fmt: _Format) -> list[list[Node]]:
        """Cells of each row. Anything else found inside the table is text that must not be lost:
        it is written before the table, where a browser would show it."""
        rows: list[list[Node]] = []
        stray = Node("", {})

        def take_row(row: Node) -> None:
            cells = [c for c in row.children if isinstance(c, Node) and c.tag in ("td", "th")]
            for other in row.children:
                if other not in cells:
                    stray.children += [other, " "]
            rows.append(cells)

        for child in table.children:
            if isinstance(child, Node) and child.tag == "tr":
                take_row(child)
            elif isinstance(child, Node) and child.tag in _ROW_GROUPS:
                for inner in child.children:
                    if isinstance(inner, Node) and inner.tag == "tr":
                        take_row(inner)
                    else:
                        stray.children += [inner, " "]
            else:
                stray.children += [child, " "]
        self._walk(stray, fmt)
        self._close()
        return rows

    def _table(self, node: Node, fmt: _Format) -> None:
        self._close()
        rows: list[list[Cell]] = []
        for row in self._rows(node, fmt):
            cells: list[Cell] = []
            for cell in row:
                style = self._style(cell)
                if style.hidden:
                    continue
                self.containers.append([])
                self._walk(cell, replace(fmt, flags=fmt.flags | style.flags, align=style.align))
                self._close()
                blocks = self.containers.pop()
                colspan, rowspan = _span(cell.attrs.get("colspan", "")), _span(cell.attrs.get("rowspan", ""))
                cells.append(Cell(cell.tag, colspan, rowspan, blocks))
            if cells:
                rows.append(cells)
        if not any(cell.blocks for row in rows for cell in row):
            return
        if all(len(row) == 1 and row[0].colspan == 1 and row[0].rowspan == 1 for row in rows):
            # One column is page layout, not a table: keep its text as ordinary paragraphs.
            self.containers[-1].extend(block for row in rows for block in row[0].blocks)
        else:
            self.containers[-1].append(Table(rows))

    def _walk(self, node: Node, fmt: _Format) -> None:
        for child in node.children:
            if isinstance(child, str):
                self._text(child, fmt)
                continue
            tag = child.tag
            if tag in _DROPPED:
                continue
            style = self._style(child)
            if style.hidden:
                continue
            if tag in _NOT_FAITHFUL:
                self.unknown_tags.add(tag)
            inner = replace(fmt, flags=fmt.flags | style.flags)
            if tag == "a":
                self._link(child, inner)
            elif tag == "br":
                if self.para is not None:
                    self.para.items.append(Break())
            elif tag == "img":
                self.images += 1
            elif tag in _INLINE_FLAGS:
                self._walk(child, replace(inner, flags=inner.flags | {_INLINE_FLAGS[tag]}))
            elif tag in _PARA_TAGS:
                self._paragraph(child, inner, style)
            elif tag == "table":
                self._table(child, inner)
            elif tag in _CONTAINERS:
                self._close()
                align = style.align or ("center" if tag == "center" else fmt.align)
                self._walk(child, replace(inner, align=align))
                self._close()
            else:
                if tag not in _PLAIN_INLINE:
                    self.unknown_tags.add(tag)
                self._walk(child, inner)

    # --- result

    def finish(self) -> Converted:
        self._close()
        blocks = self.containers[0]
        if self.pending:
            # Anchors after the last text still must exist, or links to them would break.
            blocks.append(Para("p", id=self.pending[0], items=[Anchor(a) for a in self.pending[1:]]))
        toc: list[TocEntry] = []
        text_chars = 0
        for para in paragraphs(blocks):
            title = unicodedata.normalize("NFC", para.plain_text())
            text_chars += len(title)
            for anchor in para.anchors():
                level = rules.TOC_LEVELS.get(self.kind_of.get(anchor, ""))
                if level and title:
                    toc.append(TocEntry(level, anchor, _shorten(title)))
        report = Report(
            text_chars=text_chars,
            images=self.images,
            dropped_links=self.dropped_links,
            unknown_kinds=tuple(sorted(self.unknown_kinds)),
            unknown_classes=tuple(sorted(self.unknown_classes)),
            unknown_tags=tuple(sorted(self.unknown_tags)),
        )
        return Converted(render(blocks, self.ids), toc, report)


def _shorten(title: str) -> str:
    if len(title) <= rules.TOC_TITLE_CHARS:
        return title
    cut = title[: rules.TOC_TITLE_CHARS]
    return cut[: cut.rfind(" ")].rstrip(" ,;:") + "…" if " " in cut else cut + "…"


def convert(page: str, *, nreg: str, styles: Styles | None = None) -> Converted:
    """Converts a portal page (or just its `#article` element) of the document number `nreg`.

    Raises ConvertError when the page is too large, too deeply nested, or holds no document text
    (for example an error page).
    """
    own = rules.normalize_nreg(nreg)
    if own is None:
        raise ValueError("bad nreg")
    if len(page) > rules.MAX_PAGE_CHARS:
        raise ConvertError("too_large")
    article = find_by_id(parse(page), "article")
    if article is None:
        raise ConvertError("no_article")
    converter = _Converter(own, styles or Styles())
    converter._walk(article, _Format())
    return converter.finish()
