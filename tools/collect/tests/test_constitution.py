# SPDX-License-Identifier: GPL-3.0-or-later
"""The converter on a real page: the Constitution as saved from zakon.rada.gov.ua."""

from __future__ import annotations

import re

import pytest
from suvii import Document, Writer, keys, open_scroll
from suvii.html import check_html, html_to_text

from chynnist_collect import convert, rules

NREG = "254к/96-вр"
FIELDS = {"kind": {"type": "enum", "title": {"uk": "Вид"}, "values": {"constitution": {"uk": "Конституція"}}}}


@pytest.fixture(scope="module")
def result(constitution_page, styles):
    return convert(constitution_page, nreg=NREG, styles=styles)


def test_every_anchor_of_the_page_is_kept(constitution_page, result):
    names = re.findall(r'<a name="([^"]+)"', constitution_page)
    assert len(names) == len(set(names)) == 941
    assert check_html(result.body) == set(names)


def test_contents(result):
    levels = [entry.level for entry in result.toc]
    assert levels.count(1) == 15 and levels.count(3) == 166 and len(levels) == 181
    assert result.toc[0].title == "Розділ I ЗАГАЛЬНІ ЗАСАДИ"
    assert result.toc[1].title == "Стаття 1. Україна є суверенна і незалежна, демократична, соціальна, правова держава."
    titles = [entry.title for entry in result.toc]
    assert any(title.startswith("Стаття 149-1. ") for title in titles)
    assert "Розділ VIII ПРАВОСУДДЯ" in titles


def test_text(result):
    body = result.body
    assert '<p id="n4174"><b>Стаття 1.</b> Україна є суверенна і незалежна' in body
    assert '<p id="n4760" class="suvii-center"><b>Розділ VIII<br>ПРАВОСУДДЯ</b></p>' in body
    assert "12<b><sup>-1</sup></b>) призначення на посаду" in body
    text = html_to_text(body)
    assert "Стаття 149-1. Повноваження судді Конституційного Суду України припиняються" in text
    assert result.report.text_chars > 130_000


def test_links(result):
    hrefs = re.findall(r'href="([^"]+)"', result.body)
    assert len(hrefs) == 323
    assert all(h.startswith(("#n", "suvii:laws/")) for h in hrefs)
    assert "suvii:laws/1401-19#n2" in hrefs and "suvii:laws/v020p710-10" in hrefs
    # Two adjacent links to the same place on the page become one.
    assert '<a href="#n5277">статтею 149-1</a> Конституції' in result.body
    assert result.report.dropped_links == 0


def test_nothing_of_the_page_layout_is_left(result):
    assert set(re.findall(r"<([a-z0-9]+)", result.body)) == {"p", "a", "b", "i", "br", "sup"}
    assert set(re.findall(r' ([a-z-]+)="', result.body)) == {"id", "class", "href"}
    classes = {c for value in re.findall(r'class="([^"]+)"', result.body) for c in value.split()}
    assert classes == {rules.CLASS_CENTER, rules.CLASS_NOTE}
    assert result.report.images == 1  # the coat of arms
    assert result.report.unknown_kinds == () and result.report.unknown_tags == ()


def test_conversion_is_stable(constitution_page, styles, result):
    assert convert(constitution_page, nreg=NREG, styles=styles).body == result.body


def test_document_fits_into_a_scroll(tmp_path, result):
    key = keys.generate()
    out = tmp_path / "test.suvii"
    with Writer(
        out,
        collection_id="0b6f3a52-3d1e-4c2a-9a57-6f8d2a1c4e10",
        title="Тест",
        language="uk",
        publisher="Test",
        fields=FIELDS,
        seq=1,
        source_date="2026-11-01",
        level=3,
    ) as w:
        w.add(
            Document(
                path=rules.doc_path(NREG),
                title="Конституція України",
                body=result.body,
                updated="2026-11-01T00:00:00Z",
                facets=[("kind", "constitution")],
                toc=result.toc,
            )
        )
        w.finish(key)
    with open_scroll(out, [keys.public_text(key)]) as scroll:
        doc = scroll.document("laws/254к/96-вр")
        assert doc.body == result.body and doc.toc == result.toc
        assert scroll.verify_all() == []
        assert [path for path, _ in scroll.search("узурпувати")] == ["laws/254к/96-вр"]
