# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import pytest
from conftest import REAL_CARD_LINE, card_line, catalog_bytes

from chynnist_collect import cards, rules
from chynnist_collect.cards import Card


def test_real_line_of_the_portal():
    found, skipped = cards.parse(catalog_bytes(REAL_CARD_LINE))
    assert found == [Card("n0438500-26", "Про облікову ціну банківських металів", 0, (95,), "20261103")]
    assert skipped == 0


def test_lines_fields_and_encoding():
    data = catalog_bytes(
        "dokid\tnreg\tnazva\tstatus\ttypes\torgans\tminjust\tnpix\tdatred",  # a heading is not an error
        card_line("254К/96-ВР", " Конституція України ", types="216"),
        "",
        card_line("2341-14", "Кримінальний кодекс України", types="1|21", edition=""),
        card_line("435-15", "Цивільний кодекс України", types="21") + "\textra\tfields",
    )
    found, skipped = cards.parse(data)
    assert found == [
        Card("254к/96-вр", "Конституція України", 5, (216,), "20260101"),
        Card("2341-14", "Кримінальний кодекс України", 5, (1, 21), ""),
        Card("435-15", "Цивільний кодекс України", 5, (21,), "20260101"),
    ]
    assert skipped == 0


@pytest.mark.parametrize(
    "line",
    [
        "1\t2341-14\tToo few fields",
        card_line("../etc", "Bad number"),
        card_line("", "No number"),
        card_line("1-20", "Bad status").replace("\t5\t", "\tx\t"),
        card_line("1-20", "Bad types", types="1|a"),
        card_line("1-20", "Bad date", edition="2026"),
        "<html><body>403 Forbidden</body></html>",
    ],
)
def test_unreadable_line_is_counted_and_skipped(line):
    found, skipped = cards.parse(catalog_bytes(card_line("9-20", "Good"), line))
    assert [card.nreg for card in found] == ["9-20"] and skipped == 1


def test_byte_outside_the_encoding_does_not_lose_the_document():
    data = catalog_bytes(card_line("1-20", "Назва")).replace("Назва".encode("cp1251"), b"\x98")
    found, skipped = cards.parse(data)
    assert [card.nreg for card in found] == ["1-20"] and skipped == 0


@pytest.mark.parametrize(
    ("card", "expected"),
    [
        (Card("254к/96-вр", "Конституція України", 5, (216,), ""), rules.PRIORITY_CONSTITUTION),
        (Card("2341-14", "Кримінальний кодекс України", 5, (1, 21), ""), rules.PRIORITY_CODE),
        (Card("2755-17", "Податковий кодекс України", 5, (124,), ""), rules.PRIORITY_CODE),
        (Card("1-20", "Про щось", 5, (1,), ""), rules.PRIORITY_LAW),
        (Card("2-20", "Про щось", 2, (1,), ""), rules.PRIORITY_LAW),  # coming into force
        (Card("3-20", "Про щось", 5, (2,), ""), rules.PRIORITY_RESOLUTION_OR_DECREE),
        (Card("64/2022", "Про щось", 5, (3,), ""), rules.PRIORITY_RESOLUTION_OR_DECREE),
        (Card("z0001-20", "Про щось", 5, (9,), ""), rules.PRIORITY_OTHER_IN_FORCE),
        (Card("5-20", "Про щось", 0, (), ""), rules.PRIORITY_OTHER_IN_FORCE),  # status unknown
        (Card("1001-05", "Кодекс, що втратив чинність", 1, (21,), ""), rules.PRIORITY_NOT_IN_FORCE),
        (Card("6-20", "Про щось", 6, (1,), ""), rules.PRIORITY_NOT_IN_FORCE),
        (Card("n0438500-26", "Про облікову ціну банківських металів", 0, (95,), ""), rules.PRIORITY_DAILY),
        (Card("v0001500-26", "Про офіційний курс гривні щодо іноземних валют", 5, (95,), ""), rules.PRIORITY_DAILY),
    ],
)
def test_priority(card, expected):
    assert cards.priority(card) == expected
