from __future__ import annotations

import argparse

from chynnist_collect import cli
from chynnist_collect.cli import resume_at, sleep_until


def test_when_work_goes_on(state, clock):
    now = clock.now()  # noon in Kyiv, 11 November 2026
    assert resume_at(state, "done", now) is None
    assert resume_at(state, "time", now) == now
    assert resume_at(state, "hour", now) == now + 3600 + 60  # 13:01
    assert resume_at(state, "budget", now) == now + 12 * 3600 + 60  # 00:01 the next day
    state.rest(now + 3 * 3600)
    assert resume_at(state, "errors", now) == now + 3 * 3600
    state.block_until(now + 24 * 3600)
    assert resume_at(state, "blocked", now) == now + 24 * 3600
    assert resume_at(state, "later", now) == now + 3600


def test_a_long_wait_is_slept_a_minute_at_a_time(clock):
    start = clock.now()
    sleep_until(clock, start + 150)
    assert clock.sleeps == [60, 60, 30]
    assert clock.now() == start + 150


def test_wait_ends_on_time_after_the_computer_slept(clock):
    start = clock.now()

    class Asleep:
        """The computer slept for an hour during the first minute's sleep."""

        def now(self):
            return clock.now()

        def sleep(self, seconds):
            clock.sleep(seconds + (3600 if not clock.sleeps else 0))

    sleep_until(Asleep(), start + 600)
    assert clock.now() == start + 3660  # one step, then the wall clock says the wait is over


def test_keep_going_waits_through_the_day_limit_quietly(state, clock, monkeypatch, capsys, tmp_path):
    ends = iter(["time", "budget", "done"])
    monkeypatch.setattr(cli.fetch, "run", lambda *a, **k: next(ends))
    args = argparse.Namespace(keep_going=True, minutes=55)
    assert cli._run(state, args, tmp_path, clock) == 0
    out = capsys.readouterr().out
    assert out.count("Денний ліміт вичерпано. Збирач продовжить 12.11 о 00:01 (за Києвом).") == 1
    assert "Термінал можна залишити або закрити" in out
    assert "Черга порожня" in out
    assert clock.now() == 1794391200.0 + 12 * 3600 + 60
    assert max(clock.sleeps) <= 60  # no long sleep at once


def test_one_run_says_when_requests_may_go_on(state, clock, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli.fetch, "run", lambda *a, **k: "budget")
    args = argparse.Namespace(keep_going=False, minutes=55)
    assert cli._run(state, args, tmp_path, clock) == 0
    out = capsys.readouterr().out
    assert "Денний ліміт вичерпано.\nНаступні запити — не раніше 12.11 о 00:01. Термінал можна" in out
    assert clock.sleeps == []


def test_stopping_by_hand_is_calm(state, clock, monkeypatch, capsys, tmp_path):
    def interrupted(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli.fetch, "run", interrupted)
    assert cli._run(state, argparse.Namespace(keep_going=True, minutes=55), tmp_path, clock) == 0
    assert "Зупинено. Наступний запуск продовжить з цього місця." in capsys.readouterr().out
