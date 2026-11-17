# SPDX-License-Identifier: GPL-3.0-or-later
"""The only way the collector talks to the portal. All rules of polite behaviour are applied here:

- every request names the client as the portal asks and goes only to the portal's own hosts;
- 5-7 seconds pass between any two requests, redirects included, also across runs;
- requests and bytes of the day stay under our share of the portal's limits;
- a refusal (429, or 403 that is not about one document) stops everything for a day;
- bytes are spread over the hours of the day;
- after several failures in a row nothing is requested for a few hours.

The portal forbids asking for limits or tokens before each request, so nothing like that is done:
the limits are counted here.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from urllib.parse import urljoin, urlsplit

from . import rules
from .state import State
from .transport import Response, TransportError

log = logging.getLogger(__name__)

_REDIRECTS = frozenset({301, 302, 303, 307, 308})


class Clock(Protocol):
    def now(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class SystemClock:
    def now(self) -> float:
        return time.time()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class Sender(Protocol):
    def get(self, url: str, headers: dict[str, str], max_bytes: int = ...) -> Response: ...


class Stop(Exception):
    """No more requests in this run. `reason` is one of: blocked, budget, hour, errors."""

    # blocked: the portal refused us, wait a day; budget: the day's share is used up;
    # hour: the hour's share is used up; errors: several failures in a row, wait a few hours.

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class RequestFailed(Exception):
    """This one request failed (network, server error, bad redirect); the next may be tried."""

    def __init__(self, code: str, status: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class Reply:
    status: int  # 200, 304, or a 4xx that is an answer about this address (404, 410)
    body: bytes
    last_modified: str


def day_of(moment: float) -> str:
    return datetime.fromtimestamp(moment, rules.day_zone()).date().isoformat()


def hour_of(moment: float) -> str:
    return datetime.fromtimestamp(moment, rules.day_zone()).strftime("%Y-%m-%dT%H")


def _log_path(url: str) -> str:
    """The address without host and query: enough for the journal."""
    return urlsplit(url).path


class Portal:
    def __init__(self, state: State, sender: Sender, clock: Clock, rng: random.Random | None = None) -> None:
        self.state = state
        self.sender = sender
        self.clock = clock
        self.rng = rng or random.Random()
        self.errors_in_row = 0

    def _wait_for_turn(self, max_bytes: int) -> None:
        """Raises Stop if no request may be made now; otherwise sleeps until the pause has passed."""
        now = self.clock.now()
        blocked_until = self.state.blocked_until()
        if blocked_until is not None and now < blocked_until:
            raise Stop("blocked")
        rest_until = self.state.rest_until()
        if rest_until is not None and now < rest_until:
            raise Stop("errors")
        requests, used = self.state.usage(day_of(now))
        if requests >= rules.MAX_REQUESTS_PER_DAY or used >= rules.MAX_BYTES_PER_DAY:
            raise Stop("budget")
        # An ordinary answer is small enough to cross our limit safely. A large file is not:
        # it is asked for only when the whole of it fits into what is left of the day.
        if max_bytes > rules.MAX_RESPONSE_BYTES and used + max_bytes > rules.MAX_BYTES_PER_DAY:
            raise Stop("budget")
        # The hour's share; a large file takes a whole hour of its own.
        this_hour = self.state.hour_bytes(hour_of(now))
        if this_hour >= rules.MAX_BYTES_PER_HOUR or (max_bytes > rules.MAX_RESPONSE_BYTES and this_hour > 0):
            raise Stop("hour")
        last = self.state.last_request()
        if last is not None:
            pause = self.rng.uniform(*rules.PAUSE_SECONDS)
            elapsed = now - last
            # If the computer's clock went back we cannot know how long ago it was: wait in full.
            wait = pause if elapsed < 0 else pause - elapsed
            if wait > 0:
                self.clock.sleep(wait)

    def _failed(self, code: str, status: int | None = None) -> RequestFailed:
        self.errors_in_row += 1
        if self.errors_in_row >= rules.MAX_ERRORS_IN_ROW:
            until = self.clock.now() + rules.ERROR_REST_SECONDS
            self.state.rest(until)
            log.error("REST after %d failures in a row; no requests until %s", self.errors_in_row, _stamp(until))
            raise Stop("errors")
        return RequestFailed(code, status)

    def _block(self, status: int) -> Stop:
        until = self.clock.now() + rules.BLOCK_SECONDS
        self.state.block_until(until)
        log.error("BLOCKED by the portal (%d); no requests until %s", status, _stamp(until))
        return Stop("blocked")

    def _send(self, url: str, headers: dict[str, str], max_bytes: int, refusal_ok: bool) -> Response:
        self._wait_for_turn(max_bytes)
        now = self.clock.now()
        day = day_of(now)
        self.state.count_request(day, now)
        try:
            response = self.sender.get(url, headers, max_bytes)
        except TransportError as e:
            self.state.count_answer(day, e.wire_bytes, self.clock.now(), hour_of(now))
            log.warning("FAIL %s %s", e.code, _log_path(url))
            raise self._failed(e.code) from e
        self.state.count_answer(day, response.wire_bytes, self.clock.now(), hour_of(now))
        log.info("%d %s %d", response.status, _log_path(url), response.wire_bytes)
        refused = response.status in rules.BLOCK_STATUSES
        recent = self.state.note_answer(refused)
        if not refused:
            return response
        if response.status != rules.REFUSED_DOCUMENT or not refusal_ok:
            raise self._block(response.status)
        if recent.endswith("rr") or recent.count("r") > rules.MAX_REFUSALS_IN_WINDOW:
            raise self._block(response.status)
        log.warning("REFUSED %s: taken as a document without text", _log_path(url))
        return response

    def get(
        self,
        path: str,
        *,
        if_modified_since: str = "",
        max_bytes: int = rules.MAX_RESPONSE_BYTES,
        refusal_ok: bool = False,
    ) -> Reply:
        """Requests a path of the portal. Raises Stop or RequestFailed; returns only clear answers.

        With `refusal_ok` (a document page) a single 403 is a clear answer too: the portal gives no
        text of that document. Anywhere else, and when refusals repeat, 403 stops everything for a day.
        """
        url = rules.PORTAL_ORIGIN + path
        headers = {"User-Agent": rules.USER_AGENT, "Accept": "*/*"}
        if if_modified_since:
            headers["If-Modified-Since"] = if_modified_since
        for _ in range(rules.MAX_REDIRECTS + 1):
            response = self._send(url, headers, max_bytes, refusal_ok)
            if response.status in _REDIRECTS:
                url = _redirect_target(url, response.headers.get("location", ""))
                if url is None:
                    raise self._failed("bad_redirect", response.status)
                continue
            expected = {200, 404, 410} | ({304} if if_modified_since else set()) | ({403} if refusal_ok else set())
            if response.status not in expected:
                raise self._failed("status", response.status)
            self.errors_in_row = 0
            modified = response.headers.get("last-modified", "")
            return Reply(response.status, response.body, modified if rules.valid_http_date(modified) else "")
        raise self._failed("too_many_redirects")


def _redirect_target(url: str, location: str) -> str | None:
    """The next address, only if it is an https address of one of the portal's hosts."""
    if not location:
        return None
    try:
        target = urljoin(url, location)
        parts = urlsplit(target)
        host = parts.hostname or ""
    except ValueError:
        return None
    if parts.scheme != "https" or host not in rules.FETCH_HOSTS or parts.port is not None:
        return None
    return target


def _stamp(moment: float) -> str:
    return datetime.fromtimestamp(moment, rules.day_zone()).strftime("%Y-%m-%d %H:%M")
