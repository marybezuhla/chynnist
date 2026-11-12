# SPDX-License-Identifier: GPL-3.0-or-later
"""Everything the collector remembers between runs, in one SQLite file of the working folder.

A run may be stopped at any moment (the computer sleeps, the hour ends). Each step is saved at
once, so the next run continues from the same place and never repeats a request without need.
"""

from __future__ import annotations

import sqlite3
import zlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from . import rules

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY NOT NULL,
  value TEXT NOT NULL
) WITHOUT ROWID;
-- Requests and bytes of each day by Kyiv time, to stay under the portal's daily limits.
CREATE TABLE IF NOT EXISTS days (
  day      TEXT PRIMARY KEY NOT NULL,
  requests INTEGER NOT NULL DEFAULT 0,
  bytes    INTEGER NOT NULL DEFAULT 0
) WITHOUT ROWID;
-- The queue. A document waits while `got` differs from `wanted` (the edition we want to have).
CREATE TABLE IF NOT EXISTS docs (
  nreg          TEXT PRIMARY KEY NOT NULL,
  priority      INTEGER NOT NULL,
  wanted        TEXT NOT NULL DEFAULT '',
  got           TEXT,
  status        INTEGER,
  last_modified TEXT NOT NULL DEFAULT '',
  fetched_at    REAL,
  failures      INTEGER NOT NULL DEFAULT 0,
  retry_at      REAL NOT NULL DEFAULT 0
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS docs_queue ON docs(priority, nreg);
-- Pages as received (deflated). Kept so that a better converter needs no new download.
CREATE TABLE IF NOT EXISTS pages (
  nreg TEXT PRIMARY KEY NOT NULL REFERENCES docs(nreg) ON DELETE CASCADE,
  body BLOB NOT NULL
) WITHOUT ROWID;
"""

_WAITING = "(got IS NULL OR got <> wanted) AND failures < ?"


@dataclass(frozen=True)
class Task:
    nreg: str
    wanted: str
    last_modified: str  # of the page we already have, or ""


@dataclass(frozen=True)
class Counts:
    total: int
    waiting: int
    done: int
    missing: int  # the portal has no such document
    given_up: int  # failed too many times


class State:
    def __init__(self, path: Path) -> None:
        self.conn = sqlite3.connect(path, isolation_level=None)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(_SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # --- settings: when the last request was made, until when the portal must be left alone

    def _get(self, key: str) -> float | None:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return float(row[0]) if row else None

    def _set(self, key: str, value: float) -> None:
        self.conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)", (key, repr(value)))

    def blocked_until(self) -> float | None:
        return self._get("blocked_until")

    def block_until(self, moment: float) -> None:
        self._set("blocked_until", moment)

    def rest_until(self) -> float | None:
        return self._get("rest_until")

    def rest(self, moment: float) -> None:
        self._set("rest_until", moment)

    def catalog_at(self) -> float | None:
        """When the list of all documents was last loaded."""
        return self._get("catalog_at")

    def set_catalog_at(self, moment: float) -> None:
        self._set("catalog_at", moment)

    def last_request(self) -> float | None:
        return self._get("last_request")

    # --- daily use

    def usage(self, day: str) -> tuple[int, int]:
        row = self.conn.execute("SELECT requests, bytes FROM days WHERE day = ?", (day,)).fetchone()
        return (row[0], row[1]) if row else (0, 0)

    def count_request(self, day: str, moment: float) -> None:
        """Called before the request is sent: a crash must never make us forget a request."""
        self.conn.execute("BEGIN")
        self.conn.execute(
            "INSERT INTO days(day, requests) VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET requests = requests + 1",
            (day,),
        )
        self._set("last_request", moment)
        self.conn.execute("COMMIT")

    def count_answer(self, day: str, amount: int, moment: float) -> None:
        """Called when the answer has ended, so that the pause is counted from its end."""
        self.conn.execute("BEGIN")
        self.conn.execute(
            "INSERT INTO days(day, bytes) VALUES (?, ?) ON CONFLICT(day) DO UPDATE SET bytes = bytes + excluded.bytes",
            (day, amount),
        )
        self._set("last_request", moment)
        self.conn.execute("COMMIT")

    # --- queue

    def add(self, nreg: str, priority: int, wanted: str = "") -> None:
        """Puts a document into the queue, or changes its priority and the edition we want."""
        self.add_many([(nreg, priority, wanted)])

    def add_many(self, rows: Iterable[tuple[str, int, str]]) -> None:
        """The same for many documents at once: all of them or, after a failure, none."""
        self.conn.execute("BEGIN")
        try:
            self.conn.executemany(
                "INSERT INTO docs(nreg, priority, wanted) VALUES (?, ?, ?) "
                "ON CONFLICT(nreg) DO UPDATE SET priority = excluded.priority, wanted = excluded.wanted, "
                "failures = CASE WHEN wanted <> excluded.wanted THEN 0 ELSE failures END, "
                "retry_at = CASE WHEN wanted <> excluded.wanted THEN 0 ELSE retry_at END",
                rows,
            )
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise
        self.conn.execute("COMMIT")

    def next_task(self, moment: float) -> Task | None:
        row = self.conn.execute(
            f"SELECT nreg, wanted, last_modified FROM docs WHERE {_WAITING} AND retry_at <= ? "
            "ORDER BY priority, nreg LIMIT 1",
            (rules.MAX_DOC_FAILURES, moment),
        ).fetchone()
        return Task(*row) if row else None

    def store(self, task: Task, page: bytes, last_modified: str, moment: float) -> None:
        self.conn.execute("BEGIN")
        self.conn.execute(
            "INSERT OR REPLACE INTO pages(nreg, body) VALUES (?, ?)", (task.nreg, zlib.compress(page, 6))
        )
        self._finish(task, 200, last_modified, moment)
        self.conn.execute("COMMIT")

    def unchanged(self, task: Task, moment: float) -> None:
        """The portal answered that the page we have is still current."""
        self._finish(task, 200, task.last_modified, moment)

    def missing(self, task: Task, status: int, moment: float) -> None:
        self.conn.execute("BEGIN")
        self.conn.execute("DELETE FROM pages WHERE nreg = ?", (task.nreg,))
        self._finish(task, status, "", moment)
        self.conn.execute("COMMIT")

    def _finish(self, task: Task, status: int, last_modified: str, moment: float) -> None:
        self.conn.execute(
            "UPDATE docs SET got = ?, status = ?, last_modified = ?, fetched_at = ?, failures = 0 WHERE nreg = ?",
            (task.wanted, status, last_modified, moment, task.nreg),
        )

    def failed(self, task: Task, status: int | None, moment: float, *, for_good: bool = False) -> None:
        """Notes a failure. The document is tried again later, not at once; `for_good` gives it up."""
        self.conn.execute(
            "UPDATE docs SET failures = max(failures + 1, ?), status = ?, retry_at = ? WHERE nreg = ?",
            (rules.MAX_DOC_FAILURES if for_good else 0, status, moment + rules.RETRY_SECONDS, task.nreg),
        )

    def page(self, nreg: str) -> bytes | None:
        row = self.conn.execute("SELECT body FROM pages WHERE nreg = ?", (nreg,)).fetchone()
        if row is None:
            return None
        unpacker = zlib.decompressobj()
        page = unpacker.decompress(row[0], rules.MAX_DECODED_BYTES)
        return page if unpacker.eof else None

    def counts(self) -> Counts:
        total, waiting, done, missing, given_up = self.conn.execute(
            f"""SELECT count(*),
                       coalesce(sum({_WAITING}), 0),
                       coalesce(sum(got = wanted AND status = 200), 0),
                       coalesce(sum(got = wanted AND status <> 200), 0),
                       coalesce(sum((got IS NULL OR got <> wanted) AND failures >= ?), 0)
                FROM docs""",
            (rules.MAX_DOC_FAILURES, rules.MAX_DOC_FAILURES),
        ).fetchone()
        return Counts(total, waiting, done, missing, given_up)
