# SPDX-License-Identifier: GPL-3.0-or-later
"""The rules of polite behaviour, checked with a fake clock and a fake network."""

from __future__ import annotations

import random

import pytest
from conftest import FakeSender, answer_of

from chynnist_collect import rules
from chynnist_collect.portal import Portal, RequestFailed, Stop, day_of
from chynnist_collect.transport import TransportError

DATA = "https://data.rada.gov.ua"
ZAKON = "https://zakon.rada.gov.ua"
OK = answer_of(200, b"page", last_modified="Wed, 11 Nov 2026 10:00:00 GMT")


def make(state, clock, routes=None, took=0.0):
    sender = FakeSender(clock, routes, took)
    return Portal(state, sender, clock, random.Random(1)), sender


def test_request_names_the_client_and_returns_the_page(state, clock):
    portal, sender = make(state, clock, {DATA + "/laws/show/1-20": OK})
    reply = portal.get("/laws/show/1-20")
    assert (reply.status, reply.body, reply.last_modified) == (200, b"page", "Wed, 11 Nov 2026 10:00:00 GMT")
    _, url, headers = sender.calls[0]
    assert url == DATA + "/laws/show/1-20"
    assert headers == {"User-Agent": "OpenData", "Accept": "*/*"}
    assert clock.sleeps == []  # nothing to wait for before the very first request


def test_pause_between_requests_is_counted_from_the_end_of_the_answer(state, clock):
    portal, sender = make(state, clock, {DATA + "/a": OK, DATA + "/b": OK}, took=30.0)
    for _ in range(5):
        portal.get("/a")
        portal.get("/b")
    starts = [moment for moment, _, _ in sender.calls]
    gaps = [later - (earlier + 30.0) for earlier, later in zip(starts, starts[1:], strict=False)]
    assert len(gaps) == 9 and all(5.0 <= gap <= 7.0 for gap in gaps)
    assert len(set(gaps)) > 1  # not a fixed rhythm


def test_pause_holds_across_runs(state, clock):
    make(state, clock, {DATA + "/a": OK})[0].get("/a")
    clock.moment += 2.0  # the next run starts two seconds later
    portal, sender = make(state, clock, {DATA + "/a": OK})
    portal.get("/a")
    assert 3.0 <= clock.sleeps[-1] <= 5.0
    clock.moment += 3600.0  # and an hour later there is nothing to wait for
    sleeps = len(clock.sleeps)
    make(state, clock, {DATA + "/a": OK})[0].get("/a")
    assert len(clock.sleeps) == sleeps


def test_clock_set_back_means_a_full_pause(state, clock):
    portal, _ = make(state, clock, {DATA + "/a": OK})
    portal.get("/a")
    clock.moment -= 5000.0
    portal.get("/a")
    assert 5.0 <= clock.sleeps[-1] <= 7.0


@pytest.mark.parametrize("status", [403, 429])
def test_refusal_stops_everything_for_a_day(state, clock, status):
    portal, sender = make(state, clock, {DATA + "/a": answer_of(status), DATA + "/b": OK})
    with pytest.raises(Stop) as stop:
        portal.get("/a")
    assert stop.value.reason == "blocked"
    clock.moment += rules.BLOCK_SECONDS - 60
    another_run, another_sender = make(state, clock, {DATA + "/b": OK})
    with pytest.raises(Stop):
        another_run.get("/b")
    assert len(sender.calls) == 1 and another_sender.calls == []  # not a single request more
    clock.moment += 120
    assert another_run.get("/b").status == 200


def test_daily_bytes_limit_and_a_new_day(state, clock, monkeypatch):
    monkeypatch.setattr(rules, "MAX_BYTES_PER_DAY", 10)
    portal, sender = make(state, clock, {DATA + "/a": answer_of(200, b"123456")})
    portal.get("/a")
    portal.get("/a")  # 6 bytes used: still under the limit, so this one goes
    with pytest.raises(Stop) as stop:
        portal.get("/a")
    assert stop.value.reason == "budget" and len(sender.calls) == 2
    assert state.usage(day_of(clock.now())) == (2, 12)
    clock.moment += 12 * 3600  # midnight in Kyiv has passed
    assert portal.get("/a").status == 200


def test_daily_requests_limit(state, clock, monkeypatch):
    monkeypatch.setattr(rules, "MAX_REQUESTS_PER_DAY", 2)
    portal, sender = make(state, clock, {DATA + "/a": OK})
    portal.get("/a")
    portal.get("/a")
    with pytest.raises(Stop):
        portal.get("/a")
    assert len(sender.calls) == 2


def test_day_changes_at_midnight_in_kyiv():
    assert day_of(1794434399.0) == "2026-11-11"  # 23:59:59 in Kyiv (21:59:59 UTC)
    assert day_of(1794434400.0) == "2026-11-12"


def test_redirect_inside_the_portal_is_followed_as_one_more_polite_request(state, clock):
    routes = {
        DATA + "/laws/show/1-20": answer_of(302, location=ZAKON + "/laws/show/1-20"),
        ZAKON + "/laws/show/1-20": answer_of(301, location="/laws/show/1-20/page"),
        ZAKON + "/laws/show/1-20/page": OK,
    }
    portal, sender = make(state, clock, routes)
    assert portal.get("/laws/show/1-20", if_modified_since="X").body == b"page"
    assert [url for _, url, _ in sender.calls] == list(routes)
    assert all(headers["User-Agent"] == "OpenData" and headers["If-Modified-Since"] == "X" for _, _, headers in sender.calls)
    assert len(clock.sleeps) == 2 and state.usage(day_of(clock.now()))[0] == 3


@pytest.mark.parametrize(
    "location",
    ["https://example.org/x", "http://zakon.rada.gov.ua/x", "https://zakon.rada.gov.ua:8443/x", "//example.org/x", ""],
)
def test_redirect_elsewhere_is_not_followed(state, clock, location):
    portal, sender = make(state, clock, {DATA + "/a": answer_of(302, location=location)})
    with pytest.raises(RequestFailed) as failure:
        portal.get("/a")
    assert failure.value.code == "bad_redirect" and len(sender.calls) == 1


def test_endless_redirects_end(state, clock):
    portal, sender = make(state, clock, {DATA + "/a": answer_of(302, location="/a")})
    with pytest.raises(RequestFailed) as failure:
        portal.get("/a")
    assert failure.value.code == "too_many_redirects"
    assert len(sender.calls) == rules.MAX_REDIRECTS + 1


def test_three_failures_in_a_row_end_the_run(state, clock):
    routes = {DATA + "/bad": answer_of(500), DATA + "/a": OK, DATA + "/down": TransportError("network", 7)}
    portal, _ = make(state, clock, routes)
    for path in ("/bad", "/down", "/a", "/bad", "/down"):  # a good answer in between resets the count
        if path == "/a":
            portal.get(path)
        else:
            with pytest.raises(RequestFailed):
                portal.get(path)
    with pytest.raises(Stop) as stop:
        portal.get("/bad")
    assert stop.value.reason == "errors"
    assert state.usage(day_of(clock.now())) == (6, 4 + 7 + 7)  # bytes of failed answers count too
    # A portal that drops connections may be defending itself: leave it alone for a few hours.
    clock.moment += rules.ERROR_REST_SECONDS - 60
    later_run, later_sender = make(state, clock, routes)
    with pytest.raises(Stop):
        later_run.get("/a")
    assert later_sender.calls == []
    clock.moment += 120
    assert later_run.get("/a").status == 200


def test_odd_last_modified_is_not_kept(state, clock):
    # The value goes back to the portal in a header; anything but a plain date is dropped.
    portal, _ = make(state, clock, {DATA + "/a": answer_of(200, b"x", last_modified="yesterday\r\nX-Evil: 1")})
    assert portal.get("/a").last_modified == ""


def test_missing_document_is_a_clear_answer(state, clock):
    portal, _ = make(state, clock)
    assert portal.get("/laws/show/nothing").status == 404


def test_not_modified_only_when_we_asked(state, clock):
    portal, sender = make(state, clock, {DATA + "/a": answer_of(304)})
    assert portal.get("/a", if_modified_since="Wed, 11 Nov 2026 10:00:00 GMT").status == 304
    assert sender.calls[0][2]["If-Modified-Since"] == "Wed, 11 Nov 2026 10:00:00 GMT"
    with pytest.raises(RequestFailed):
        portal.get("/a")
