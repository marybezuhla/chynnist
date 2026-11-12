# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import random

import pytest
from conftest import REAL_CARD_LINE, FakeSender, answer_of, card_line, catalog_bytes

from chynnist_collect import catalog, rules
from chynnist_collect.catalog import CatalogError
from chynnist_collect.portal import Portal, RequestFailed, Stop, day_of

URL = "https://data.rada.gov.ua/ogd/zak/laws/data/csv/doc.txt"
LIST = catalog_bytes(
    REAL_CARD_LINE,
    card_line("z0001-20", "Наказ", types="9"),
    card_line("1001-05", "Старий кодекс", status=1, types="21"),
    card_line("3-20", "Постанова", types="2"),
    card_line("2341-14", "Кримінальний кодекс України", types="1|21"),
    card_line("1-20", "Закон", types="1", edition="20260101"),
    card_line("254К/96-ВР", "Конституція України", types="216"),
    "broken line",
)


@pytest.fixture(autouse=True)
def small_lists_allowed(monkeypatch):
    monkeypatch.setattr(rules, "MIN_CATALOG_ROWS", 5)


def queue(state, moment=0.0):
    order = []
    while task := state.next_task(moment):
        order.append(task.nreg)
        state.store(task, b"page", "", moment)
    return order


def portal_for(state, clock, routes):
    sender = FakeSender(clock, routes)
    return Portal(state, sender, clock, random.Random(1)), sender


def test_list_fills_the_queue_in_the_agreed_order(state):
    summary = catalog.load(state, LIST, 1000.0)
    assert (summary.documents, summary.skipped_lines) == (7, 1)
    assert queue(state) == ["254к/96-вр", "2341-14", "1-20", "3-20", "z0001-20", "1001-05", "n0438500-26"]
    assert state.catalog_at() == 1000.0


def test_only_changed_editions_wait_after_the_next_list(state):
    catalog.load(state, LIST, 1000.0)
    queue(state)
    newer = LIST.replace(card_line("1-20", "Закон", types="1", edition="20260101").encode("cp1251"),
                         card_line("1-20", "Закон", types="1", edition="20261103").encode("cp1251"))
    assert newer != LIST
    catalog.load(state, newer, 2000.0)
    assert queue(state) == ["1-20"]


def test_something_else_instead_of_the_list_changes_nothing(state):
    state.add("1-20", 0)
    for data in (b"", b"<html><body>403 Forbidden</body></html>", catalog_bytes(REAL_CARD_LINE)):
        with pytest.raises(CatalogError) as e:
            catalog.load(state, data, 1000.0)
        assert e.value.code == "not_a_catalog"
    assert state.counts().total == 1 and state.catalog_at() is None


def test_refresh_downloads_once_a_week(state, clock, tmp_path):
    portal, sender = portal_for(state, clock, {URL: answer_of(200, LIST)})
    assert catalog.refresh(state, portal, clock, tmp_path).documents == 7
    assert (tmp_path / "doc.txt").read_bytes() == LIST and state.counts().waiting == 7
    assert sender.calls[0][2]["User-Agent"] == "OpenData"
    clock.moment += rules.CATALOG_SECONDS - 60
    with pytest.raises(CatalogError) as e:
        catalog.refresh(state, portal, clock, tmp_path)
    assert e.value.code == "fresh" and len(sender.calls) == 1
    clock.moment += 120
    catalog.refresh(state, portal, clock, tmp_path)
    assert len(sender.calls) == 2


def test_large_file_is_asked_only_when_all_of_it_fits_into_the_day(state, clock, tmp_path):
    portal, sender = portal_for(state, clock, {URL: answer_of(200, LIST)})
    today = day_of(clock.now())
    state.count_answer(today, rules.MAX_BYTES_PER_DAY - rules.MAX_CATALOG_BYTES + 1, clock.now())
    with pytest.raises(Stop) as stop:
        catalog.refresh(state, portal, clock, tmp_path)
    assert stop.value.reason == "budget" and sender.calls == []
    assert portal.get("/laws/show/1-20").status == 404  # an ordinary page is still allowed
    clock.moment += 24 * 3600
    assert catalog.refresh(state, portal, clock, tmp_path).documents == 7


def test_bad_answer_keeps_the_old_file_and_queue(state, clock, tmp_path):
    (tmp_path / "doc.txt").write_bytes(b"old")
    portal, _ = portal_for(state, clock, {URL: answer_of(200, b"<html>Maintenance</html>")})
    with pytest.raises(CatalogError) as e:
        catalog.refresh(state, portal, clock, tmp_path)
    assert e.value.code == "not_a_catalog"
    assert (tmp_path / "doc.txt").read_bytes() == b"old" and not (tmp_path / "doc.txt.part").exists()
    assert state.counts().total == 0 and state.catalog_at() is None
    for answer, error in ((answer_of(404), CatalogError), (answer_of(500), RequestFailed), (answer_of(403), Stop)):
        portal, _ = portal_for(state, clock, {URL: answer})
        with pytest.raises(error):
            catalog.refresh(state, portal, clock, tmp_path)
    assert (tmp_path / "doc.txt").read_bytes() == b"old"


def test_size_limit_of_the_list_is_passed_to_the_network(state, clock, tmp_path):
    seen = []

    class Sender(FakeSender):
        def get(self, url, headers, max_bytes=0):
            seen.append(max_bytes)
            return super().get(url, headers, max_bytes)

    portal = Portal(state, Sender(clock, {URL: answer_of(200, LIST)}), clock, random.Random(1))
    catalog.refresh(state, portal, clock, tmp_path)
    portal.get("/laws/show/1-20")
    assert seen == [rules.MAX_CATALOG_BYTES, rules.MAX_RESPONSE_BYTES]
