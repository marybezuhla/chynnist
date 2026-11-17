# SPDX-License-Identifier: GPL-3.0-or-later
"""The converter on real pages the portal gives to open-data clients (see fixtures/README.md)."""

from __future__ import annotations

import re
from collections import Counter

import pytest
from suvii import Document, Writer, keys, open_scroll
from suvii.html import check_html, html_to_text

from chynnist_collect import convert, rules

NREG = "254к/96-вр"


@pytest.fixture(scope="module")
def result(constitution_page):
    return convert(constitution_page, nreg=NREG)


@pytest.fixture(scope="module")
def civil(civil_code_page):
    return convert(civil_code_page, nreg="435-15")


def test_every_anchor_of_the_page_is_kept(constitution_page, result):
    names = re.findall(r'<a name="([^"]+)"', constitution_page)
    assert len(names) == len(set(names)) == 941
    assert check_html(result.body) == set(names)


def test_contents_of_the_constitution(result):
    levels = Counter(entry.level for entry in result.toc)
    assert levels == {1: 14, 2: 166}  # parts and articles
    assert result.toc[0].title == "Розділ I ЗАГАЛЬНІ ЗАСАДИ"
    assert result.toc[1].title == "Стаття 1. Україна є суверенна і незалежна, демократична, соціальна, правова держава."
    titles = [entry.title for entry in result.toc]
    assert any(title.startswith("Стаття 149 - 1 . Повноваження") for title in titles)
    assert "Розділ XV ПЕРЕХІДНІ ПОЛОЖЕННЯ" in titles


def test_contents_of_the_civil_code(civil):
    kinds = Counter(entry.level for entry in civil.toc)
    # Book, section, subsection, chapter, paragraph (§), article: all six levels are used.
    assert sorted(kinds) == [1, 2, 3, 4, 5, 6]
    first = [(e.level, e.title) for e in civil.toc[:5]]
    assert first == [
        (1, "КНИГА ПЕРША ЗАГАЛЬНІ ПОЛОЖЕННЯ"),
        (2, "Розділ I ОСНОВНІ ПОЛОЖЕННЯ"),
        (4, "Глава 1 ЦИВІЛЬНЕ ЗАКОНОДАВСТВО УКРАЇНИ"),
        (6, "Стаття 1. Відносини, що регулюються цивільним законодавством"),
        (6, "Стаття 2. Учасники цивільних відносин"),
    ]
    assert (5, "§ 1. Господарські товариства") in [(e.level, e.title) for e in civil.toc]
    assert civil.toc[-1].title == "ПРИКІНЦЕВІ ТА ПЕРЕХІДНІ ПОЛОЖЕННЯ" and civil.toc[-1].level == 2


def test_text(result):
    body = result.body
    assert '<p id="n4174"><b>Стаття 1.</b> Україна є суверенна і незалежна' in body
    assert '<p id="n4173" class="suvii-center"><b>Розділ I<br>ЗАГАЛЬНІ ЗАСАДИ</b></p>' in body
    assert '<p id="n4158">(Відомості Верховної Ради України (ВВР), 1996, № 30, ст. 141)</p>' in body
    assert "КОНСТИТУЦІЯ УКРАЇНИ" in body and "[ image ]" not in body
    assert "<b>Стаття 149 - 1 .</b> Повноваження" in body
    text = html_to_text(body)
    assert "Стаття 149 - 1 . Повноваження судді Конституційного Суду України припиняються" in text
    assert result.report.text_chars > 130_000 and result.report.images == 1


def test_links(result):
    hrefs = re.findall(r'href="([^"]+)"', result.body)
    assert all(h.startswith(("#n", "suvii:laws/")) for h in hrefs)
    assert "suvii:laws/2222-15" in hrefs and "suvii:laws/v011p710-19" in hrefs
    assert len([h for h in hrefs if h.startswith("suvii:")]) == 293
    assert result.report.dropped_links == 0


def test_notes_are_marked(result):
    notes = re.findall(r'<p id="(n\d+)" class="suvii-note">', result.body)
    assert "n5152" in notes and "n4982" in notes and len(notes) > 100


def test_nothing_of_the_page_layout_is_left(result):
    assert set(re.findall(r"<([a-z0-9]+)", result.body)) == {"p", "a", "b", "br"}
    assert set(re.findall(r' ([a-z-]+)="', result.body)) == {"id", "class", "href"}
    classes = {c for value in re.findall(r'class="([^"]+)"', result.body) for c in value.split()}
    assert classes == {rules.CLASS_CENTER, rules.CLASS_NOTE}
    assert "Верховна Рада України; Конституція України" not in result.body  # page header outside #article
    assert result.report.unknown_tags == ()


def test_conversion_is_stable(constitution_page, result):
    assert convert(constitution_page, nreg=NREG).body == result.body


def test_document_fits_into_a_scroll(tmp_path, result):
    key = keys.generate()
    out = tmp_path / "test.suvii"
    with Writer(
        out, collection_id=rules.COLLECTION_ID, title="Тест", language="uk", publisher="Test",
        fields=rules.collection_fields(), seq=1, source_date="2026-11-01", level=3,
    ) as w:  # fmt: skip
        w.add(
            Document(
                path=rules.doc_path(NREG), title="Конституція України", body=result.body,
                updated="2026-11-01T00:00:00Z", facets=[("kind", "216")], toc=result.toc,
            )  # fmt: skip
        )
        w.finish(key)
    with open_scroll(out, [keys.public_text(key)]) as scroll:
        doc = scroll.document("laws/254к/96-вр")
        assert doc.body == result.body and doc.toc == result.toc
        assert scroll.verify_all() == []
        assert [path for path, _ in scroll.search("узурпувати")] == ["laws/254к/96-вр"]
