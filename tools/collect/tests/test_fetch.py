# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import random

from conftest import FakeSender, answer_of

from chynnist_collect import fetch, rules
from chynnist_collect.portal import Portal
from chynnist_collect.state import Counts
from chynnist_collect.transport import TransportError

SHOW = "https://data.rada.gov.ua/laws/show/"


def run(state, clock, routes, minutes=60.0):
    sender = FakeSender(clock, routes)
    ended = fetch.run(state, Portal(state, sender, clock, random.Random(1)), clock, clock.now() + minutes * 60)
    return ended, sender


def test_queue_is_fetched_and_pages_are_stored(state, clock):
    state.add("254к/96-вр", 0)
    state.add("2341-14", 1)
    state.add("0-00", 2)
    routes = {
        SHOW + "254к/96-вр": answer_of(200, "Конституція".encode(), last_modified="Mon, 02 Nov 2026 08:00:00 GMT"),
        SHOW + "2341-14": answer_of(200, b"code"),
    }
    ended, sender = run(state, clock, routes)
    assert ended == "done"
    assert [url for _, url, _ in sender.calls] == [SHOW + "254к/96-вр", SHOW + "2341-14", SHOW + "0-00"]
    assert state.page("254к/96-вр").decode() == "Конституція" and state.page("2341-14") == b"code"
    assert state.counts() == Counts(total=3, waiting=0, done=2, missing=1, given_up=0)
    assert run(state, clock, routes)[1].calls == []  # a second run has nothing to ask


def test_changed_edition_is_asked_with_the_date_of_our_copy(state, clock):
    state.add("1-20", 0, wanted="20260101")
    run(state, clock, {SHOW + "1-20": answer_of(200, b"old", last_modified="Thu, 01 Jan 2026 00:00:00 GMT")})
    state.add("1-20", 0, wanted="20261103")
    ended, sender = run(state, clock, {SHOW + "1-20": answer_of(304)})
    assert ended == "done" and state.page("1-20") == b"old"
    assert sender.calls[0][2]["If-Modified-Since"] == "Thu, 01 Jan 2026 00:00:00 GMT"


def test_run_ends_when_its_time_is_over(state, clock):
    for n in range(100):
        state.add(f"{n}-20", n)
    ended, sender = run(state, clock, {}, minutes=1.0)
    assert ended == "time"
    assert 9 <= len(sender.calls) <= 13  # one request every 5-7 seconds


def test_refusal_ends_the_run_and_keeps_the_queue(state, clock):
    state.add("1-20", 0)
    state.add("2-20", 1)
    ended, sender = run(state, clock, {SHOW + "1-20": answer_of(403)})
    assert ended == "blocked" and len(sender.calls) == 1
    assert state.counts().waiting == 2
    assert run(state, clock, {})[0] == "blocked"


def test_failed_documents_do_not_stop_the_others(state, clock):
    state.add("1-20", 0)
    state.add("2-20", 1)
    state.add("3-20", 2)
    routes = {
        SHOW + "1-20": answer_of(500),
        SHOW + "2-20": TransportError("too_large", rules.MAX_RESPONSE_BYTES + 1),
        SHOW + "3-20": answer_of(200, b"ok"),
    }
    ended, sender = run(state, clock, routes)
    assert ended == "later" and len(sender.calls) == 3
    assert state.counts() == Counts(total=3, waiting=1, done=1, missing=0, given_up=1)
    clock.moment += rules.RETRY_SECONDS
    ended, sender = run(state, clock, routes)
    assert [url for _, url, _ in sender.calls] == [SHOW + "1-20"]  # the oversized one is not asked again


def test_portal_down_ends_the_run_after_three_tries(state, clock):
    for n in range(10):
        state.add(f"{n}-20", n)
    ended, sender = run(state, clock, {SHOW + f"{n}-20": TransportError("network") for n in range(10)})
    assert ended == "errors" and len(sender.calls) == rules.MAX_ERRORS_IN_ROW
    clock.moment += 3600  # the next hourly run does not knock again
    ended, sender = run(state, clock, {})
    assert ended == "errors" and sender.calls == []
