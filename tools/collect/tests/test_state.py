# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from chynnist_collect import rules
from chynnist_collect.state import Counts, State, Task

NOW = 1_000_000.0


def test_queue_goes_by_priority_then_number(state):
    state.add("2341-14", 2)
    state.add("254к/96-вр", 0)
    state.add("435-15", 2)
    order = []
    while task := state.next_task(NOW):
        order.append(task.nreg)
        state.store(task, b"<p>x</p>", "", NOW)
    assert order == ["254к/96-вр", "2341-14", "435-15"]
    assert state.counts() == Counts(total=3, waiting=0, done=3, missing=0, given_up=0)


def test_page_is_kept_as_received(state):
    state.add("1-20", 0)
    page = ("<div id='article'>" + "Текст статті. " * 5000 + "</div>").encode()
    state.store(state.next_task(NOW), page, "Wed, 11 Nov 2026 10:00:00 GMT", NOW)
    assert state.page("1-20") == page
    assert state.page("2-20") is None


def test_new_edition_puts_document_back_and_offers_its_date(state):
    state.add("1-20", 0, wanted="20260101")
    state.store(state.next_task(NOW), b"old", "Thu, 01 Jan 2026 00:00:00 GMT", NOW)
    assert state.next_task(NOW) is None
    state.add("1-20", 0, wanted="20260101")  # the same edition again: nothing to do
    assert state.next_task(NOW) is None
    state.add("1-20", 0, wanted="20261103")
    assert state.next_task(NOW) == Task("1-20", "20261103", "Thu, 01 Jan 2026 00:00:00 GMT")


def test_failed_document_waits_and_is_given_up_in_the_end(state):
    state.add("1-20", 0)
    state.add("2-20", 1)
    moment = NOW
    for attempt in range(rules.MAX_DOC_FAILURES):
        task = state.next_task(moment)
        assert task.nreg == "1-20", attempt
        state.failed(task, 500, moment)
        assert state.next_task(moment).nreg == "2-20"  # not the failed one again at once
        moment += rules.RETRY_SECONDS
    assert state.next_task(moment).nreg == "2-20"
    assert state.counts() == Counts(total=2, waiting=1, done=0, missing=0, given_up=1)


def test_document_can_be_given_up_at_once(state):
    state.add("1-20", 0)
    state.failed(state.next_task(NOW), None, NOW, for_good=True)
    assert state.next_task(NOW + 10 * rules.RETRY_SECONDS) is None
    assert state.counts().given_up == 1
    state.add("1-20", 0, wanted="20261103")  # a new edition deserves a new try
    assert state.next_task(NOW).nreg == "1-20"


def test_missing_document_is_not_asked_again(state):
    state.add("1-20", 0)
    state.store(state.next_task(NOW), b"page", "", NOW)
    state.add("1-20", 0, wanted="2")
    state.missing(state.next_task(NOW), 404, NOW)
    assert state.next_task(NOW) is None and state.page("1-20") is None
    assert state.counts() == Counts(total=1, waiting=0, done=0, missing=1, given_up=0)


def test_everything_survives_a_restart(tmp_path):
    first = State(tmp_path / "c.db")
    first.add("1-20", 0)
    first.count_request("2026-11-11", NOW)
    first.count_answer("2026-11-11", 1234, NOW + 2)
    first.block_until(NOW + 500)
    first.close()
    second = State(tmp_path / "c.db")
    assert second.usage("2026-11-11") == (1, 1234) and second.usage("2026-11-12") == (0, 0)
    assert second.last_request() == NOW + 2 and second.blocked_until() == NOW + 500
    assert second.next_task(NOW).nreg == "1-20"
    second.close()
