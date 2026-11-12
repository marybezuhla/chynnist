# SPDX-License-Identifier: GPL-3.0-or-later
"""Building a signed scroll from stored pages, checked by opening it with the format library."""

from __future__ import annotations

import json

import pytest
from conftest import SAMPLE_CSS, card_line, catalog_bytes
from suvii import keys, open_scroll

from chynnist_collect import build, rules
from chynnist_collect.state import Task

NOW = 1794391200.0


def page(text: str) -> bytes:
    return f'<html><body><div id="article"><p class="rvps7"><span class="rvts9">{text}</span></p></div></body></html>'.encode()


@pytest.fixture
def work(tmp_path, state, constitution_page):
    """A working folder as the collector leaves it: stored pages, the list of documents, the styles."""
    pages = {
        "254к/96-вр": constitution_page.encode(),
        "1-20": page("Закон про тест"),
        "2-20": "<div id='article'><p>Стара сторінка</p></div>".encode("cp1251"),
        "3-20": page("Документ без картки"),
        "4-20": b"<html><body><h1>Service unavailable</h1></body></html>",
    }
    for n, (nreg, body) in enumerate(pages.items()):
        state.add(nreg, 0)
        state.store(Task(nreg, "", ""), body, "", NOW + n)
    state.add("5-20", 0)  # in the queue, never downloaded
    (tmp_path / "doc.txt").write_bytes(
        catalog_bytes(
            card_line("254К/96-ВР", "Конституція України", types="216", edition="20240101"),
            card_line("1-20", "Про тест", status=1, types="1|21|95|95", edition="20200000"),
            card_line("2-20", "Про старе", status=42, types="2"),
        )
    )
    (tmp_path / "u_text.css").write_text(SAMPLE_CSS, encoding="utf-8")
    return tmp_path


def test_scroll_is_signed_and_holds_every_good_page(state, work):
    key = keys.generate()
    out = work / "out.suvii"
    report = build.build(state, work, out, key, source_date="2026-11-11")
    with open_scroll(out, [keys.public_text(key)]) as scroll:
        assert scroll.verify_all() == []
        assert scroll.count() == 4
        assert scroll.meta["collection.id"] == rules.COLLECTION_ID
        assert scroll.meta["collection.title"] == "Законодавство України"
        assert scroll.meta["collection.source"] == "https://data.rada.gov.ua"
        assert "посиланням на джерело" in scroll.meta["collection.license"]
        assert scroll.meta["state.seq"] == "1" and scroll.meta["state.source_date"] == "2026-11-11"

        constitution = scroll.document("laws/254к/96-вр")
        assert constitution.title == "Конституція України"
        assert sorted(constitution.facets) == [
            ("edition", "2024-01-01"), ("kind", "constitution"), ("number", "254к/96-вр"), ("status", "in_force"),
        ]  # fmt: skip
        assert len(constitution.toc) == 181 and constitution.updated == "2026-11-11T10:00:00Z"
        assert "<b>Стаття 1.</b>" in constitution.body

        law = scroll.document("laws/1-20")
        assert sorted(law.facets) == [("kind", "code_of_ukraine"), ("kind", "law"), ("number", "1-20"), ("status", "repealed")]
        assert law.body == '<p class="suvii-center"><b>Закон про тест</b></p>'

        assert scroll.document("laws/2-20").body == "<p>Стара сторінка</p>"  # Windows-1251 page
        # An unknown state code (42) is left out rather than guessed.
        assert sorted(scroll.document("laws/2-20").facets) == [("edition", "2026-01-01"), ("kind", "resolution"), ("number", "2-20")]
        assert scroll.document("laws/3-20").title == "3-20"
        assert [path for path, _ in scroll.search("узурпувати")] == ["laws/254к/96-вр"]

    assert report.documents == 4 and report.without_card == 1
    assert report.not_converted == {"no_article": 1}
    assert report.unknown_kinds == {"95": 1}
    assert report.with_images == 1 and report.styles_found
    saved = json.loads((work / build.REPORT_NAME).read_text(encoding="utf-8"))
    assert saved["documents"] == 4 and "Конституція" not in json.dumps(saved, ensure_ascii=False)


def test_states_get_growing_numbers_and_trial_builds_use_none(state, work):
    key = keys.generate()
    build.build(state, work, work / "a.suvii", key, source_date="2026-11-11")
    trial = build.build(state, work, work / "t.suvii", keys.generate(), source_date="2026-11-11", test=True)
    assert trial.seq == 2
    with open_scroll(work / "t.suvii", trust_embedded_key=True) as scroll:
        assert scroll.meta["collection.title"].endswith("(пробна збірка)")
    assert build.build(state, work, work / "b.suvii", key, source_date="2026-11-12").seq == 2


def test_without_styles_and_list_the_text_is_still_there(state, work):
    (work / "u_text.css").unlink()
    (work / "doc.txt").unlink()
    report = build.build(state, work, work / "out.suvii", keys.generate(), source_date="2026-11-11")
    assert report.documents == 4 and report.without_card == 4 and not report.styles_found
    assert "rvts9" in report.unknown_classes


def test_failed_build_leaves_no_file(state, work, monkeypatch):
    def broken(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(build, "_document", broken)
    with pytest.raises(OSError):
        build.build(state, work, work / "out.suvii", keys.generate(), source_date="2026-11-11")
    assert not (work / "out.suvii").exists() and not (work / "out.suvii.part").exists()
    assert state.next_build_seq() == 1


def test_collection_fields_are_valid_for_the_format():
    from suvii import spec

    fields = spec.check_fields(rules.collection_fields())
    assert fields["kind"]["multi"] and "in_force" in fields["status"]["values"]
