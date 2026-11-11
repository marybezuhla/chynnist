# SPDX-License-Identifier: GPL-3.0-or-later
"""Works through the queue: one document page after another, until something says stop."""

from __future__ import annotations

from . import rules
from .portal import Clock, Portal, RequestFailed, Stop
from .state import State


def run(state: State, portal: Portal, clock: Clock, until: float) -> str:
    """Fetches waiting documents. Returns why it ended: done, later (the rest waits for a retry),
    time, blocked, budget or errors."""
    while clock.now() < until:
        task = state.next_task(clock.now())
        if task is None:
            return "later" if state.counts().waiting else "done"
        try:
            reply = portal.get(rules.show_url_path(task.nreg), if_modified_since=task.last_modified)
        except Stop as stop:
            return stop.reason
        except RequestFailed as failure:
            # An answer over the size limit will be over it next time too; do not spend the day on it.
            state.failed(task, failure.status, clock.now(), for_good=failure.code == "too_large")
            continue
        if reply.status == 200:
            state.store(task, reply.body, reply.last_modified, clock.now())
        elif reply.status == 304:
            state.unchanged(task, clock.now())
        else:
            state.missing(task, reply.status, clock.now())
    return "time"
