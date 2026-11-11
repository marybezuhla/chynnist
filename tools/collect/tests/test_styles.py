# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from chynnist_collect import Styles


def test_text_styles(styles):
    assert styles.get("rvts9").flags == {"b"}
    assert styles.get("rvts46").flags == {"i"}  # selector with an element name
    assert styles.get("rvts11").flags == {"i"}  # second selector of a list
    assert styles.get("rvts37").flags == {"b", "sup"}  # numeric weight
    assert styles.get("rvts52").flags == {"u", "s"}
    assert styles.get("rvts90").flags == {"sub"}
    assert styles.get("gone").hidden


def test_paragraph_styles(styles):
    assert styles.get("rvps7").align == "center"
    assert styles.get("rvps11").align == "right"
    assert styles.get("rvps2").align == ""  # justified text is the default, no class needed


def test_later_rule_keeps_other_properties(styles):
    # `.rvts15 { font-size }` comes after `.rvts15 { font-weight: bold }` and must not undo it.
    assert styles.get("rvts15").flags == {"b"}


def test_rules_inside_at_blocks_are_ignored(styles):
    # The print style would make rvts9 italic and not bold.
    assert styles.get("rvts9").flags == {"b"}


def test_unknown_class_and_broken_css():
    assert Styles.from_css("").get("rvts1") is None
    broken = Styles.from_css("}} .a { font-weight: bold } .b { font-style: italic")
    assert broken.get("a").flags == {"b"}
    assert broken.get("b") is None  # the rule was never closed
