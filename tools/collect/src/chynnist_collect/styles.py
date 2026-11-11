# SPDX-License-Identifier: GPL-3.0-or-later
"""Reads the portal's shared stylesheet (u_text.css) and keeps the few facts the converter needs.

Text on the portal is marked with numbered classes (`rvts9`, `rvps7`) whose meaning is defined only in
that stylesheet. A Suvii document cannot carry styles, so bold, italic, superscript and alignment are
taken from the stylesheet once and written as plain elements and `suvii-*` classes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
# One class, optionally with an element name: `.rvts9` or `span.rvts9`. Other selectors are not needed.
_SELECTOR = re.compile(r"^(?:[a-z][a-z0-9]*)?\.([A-Za-z0-9_-]+)$")


@dataclass(frozen=True)
class ClassStyle:
    flags: frozenset[str] = frozenset()  # any of: b i u s sub sup
    align: str = ""  # "", "center" or "right"
    hidden: bool = False  # display: none


def _top_level_rules(css: str) -> list[tuple[str, str]]:
    """(selectors, declarations) of rules outside @media and other at-blocks.

    Rules inside at-blocks describe print or narrow screens and must not change the text.
    """
    rules: list[tuple[str, str]] = []
    depth = 0
    start = 0
    head = ""
    for i, ch in enumerate(css):
        if ch == "{":
            if depth == 0:
                head = css[start:i].strip()
                start = i + 1
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
            if depth == 0:
                if not head.startswith("@"):
                    rules.append((head, css[start:i]))
                start = i + 1
        elif ch == ";" and depth == 0:
            start = i + 1  # an at-rule without a block, such as @import
    return rules


def _declarations(block: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for item in block.split(";"):
        name, sep, value = item.partition(":")
        if sep:
            props[name.strip().lower()] = value.replace("!important", "").strip().lower()
    return props


def _is_bold(weight: str) -> bool:
    return weight in ("bold", "bolder") or (weight.isdigit() and int(weight) >= 600)


def _style_of(props: dict[str, str]) -> ClassStyle:
    flags: set[str] = set()
    if _is_bold(props.get("font-weight", "")):
        flags.add("b")
    if props.get("font-style", "") in ("italic", "oblique"):
        flags.add("i")
    decoration = props.get("text-decoration", "") + " " + props.get("text-decoration-line", "")
    if "underline" in decoration:
        flags.add("u")
    if "line-through" in decoration:
        flags.add("s")
    vertical = props.get("vertical-align", "")
    if vertical == "super":
        flags.add("sup")
    elif vertical == "sub":
        flags.add("sub")
    align = props.get("text-align", "")
    return ClassStyle(
        flags=frozenset(flags),
        align=align if align in ("center", "right") else "",
        hidden=props.get("display", "") == "none",
    )


class Styles:
    """Meaning of the portal's classes. Unknown classes mean nothing and are reported by the converter."""

    def __init__(self, classes: dict[str, ClassStyle] | None = None) -> None:
        self._classes = dict(classes or {})

    @classmethod
    def from_css(cls, css: str) -> Styles:
        props_by_class: dict[str, dict[str, str]] = {}
        for selectors, block in _top_level_rules(_COMMENT.sub("", css)):
            props = _declarations(block)
            for selector in selectors.split(","):
                m = _SELECTOR.match(selector.strip())
                if m:
                    # A later rule for the same class overrides single properties, as in a browser.
                    props_by_class.setdefault(m.group(1), {}).update(props)
        return cls({name: _style_of(props) for name, props in props_by_class.items()})

    def get(self, name: str) -> ClassStyle | None:
        return self._classes.get(name)

    def __len__(self) -> int:
        return len(self._classes)
