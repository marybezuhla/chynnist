# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import pytest

from chynnist_collect import rules
from chynnist_collect.links import rewrite_href

OWN = "254к/96-вр"

CASES = [
    # inside the document
    ("#n12", "#n12"),
    ("#bad id", None),
    # other documents of the database
    ("https://zakon.rada.gov.ua/laws/show/2222-15", "suvii:laws/2222-15"),
    ("https://zakon.rada.gov.ua/laws/show/586-18#n2", "suvii:laws/586-18#n2"),
    ("https://zakon.rada.gov.ua/laws/show/2222-15#Text", "suvii:laws/2222-15"),
    ("http://zakon2.rada.gov.ua/laws/show/2341-14/paran12#n12", "suvii:laws/2341-14#n12"),
    ("https://zakon.rada.gov.ua/laws/show/2341-14/ed20200101/print", "suvii:laws/2341-14"),
    ("https://zakon.rada.gov.ua/rada/show/v020p710-10", "suvii:laws/v020p710-10"),
    ("https://data.rada.gov.ua/laws/show/995_004", "suvii:laws/995_004"),
    ("/laws/show/64/2022", "suvii:laws/64/2022"),
    ("https://ZAKON.rada.gov.ua/laws/show/Z0001-20", "suvii:laws/z0001-20"),
    # this document
    ("https://zakon.rada.gov.ua/laws/show/254%D0%BA/96-%D0%B2%D1%80#n4188", "#n4188"),
    ("https://zakon.rada.gov.ua/laws/show/254К/96-ВР/ed20200101#n5", "#n5"),
    ("https://zakon.rada.gov.ua/laws/show/254к/96-вр", None),
    # the portal, but not a document
    ("https://zakon.rada.gov.ua/laws/file/text/1.pdf", "https://zakon.rada.gov.ua/laws/file/text/1.pdf"),
    ("/laws/main/r?page=2", "https://zakon.rada.gov.ua/laws/main/r?page=2"),
    ("https://zakon.rada.gov.ua/laws/show/a/b/c", "https://zakon.rada.gov.ua/laws/show/a/b/c"),
    # other sites
    ("https://example.org/a?b=1#c", "https://example.org/a?b=1#c"),
    ("https://zakon.rada.gov.ua.example.org/laws/show/1-20", "https://zakon.rada.gov.ua.example.org/laws/show/1-20"),
    ("http://example.org/", None),
    ("https://exa mple.org/", None),
    ('https://example.org/"onclick="x', None),
    ("javascript:alert(1)", None),
    ("mailto:a@example.org", None),
    ("//zakon.rada.gov.ua/laws/show/1-20", None),
    ("laws/show/1-20", None),
    ("", None),
    ("https://[bad", None),
]


@pytest.mark.parametrize(("href", "expected"), CASES)
def test_rewrite_href(href, expected):
    assert rewrite_href(href, OWN) == expected


def test_too_long_href_is_dropped():
    assert rewrite_href("https://example.org/" + "a" * rules.MAX_HREF_CHARS, OWN) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2341-14", "2341-14"),
        (" 254К/96-ВР ", "254к/96-вр"),
        ("64/2022", "64/2022"),
        ("995_004", "995_004"),
        ("", None),
        ("a/b/c", None),
        ("a//b", None),
        ("../x", None),
        ("a b", None),
        ("a?b", None),
        ("a#b", None),
    ],
)
def test_normalize_nreg(raw, expected):
    assert rules.normalize_nreg(raw) == expected
