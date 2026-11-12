# SPDX-License-Identifier: GPL-3.0-or-later
"""Command line of the collector: fill the queue (`catalog`, `add`), `run` the download, see `status`."""

from __future__ import annotations

import argparse
import fcntl
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import catalog, fetch, rules
from .catalog import CatalogError
from .portal import Portal, RequestFailed, Stop, SystemClock, day_of
from .state import State
from .transport import Transport

# The journal holds addresses and sizes only. Three files of 5 MB are enough for several weeks.
_LOG_BYTES = 5 * 1024 * 1024
_LOG_FILES = 3

_ENDED = {
    "done": "Черга порожня: усе завантажено.",
    "later": "Решта документів чекає повторної спроби після помилки.",
    "time": "Час запуску вийшов. Наступний запуск продовжить з цього місця.",
    "blocked": "Портал відмовив у доступі. Збирач не робитиме запитів добу.",
    "budget": "Денний ліміт вичерпано. Продовження завтра.",
    "errors": "Кілька помилок поспіль: немає мережі або портал недоступний. Збирач зачекає кілька годин.",
}


_NO_CATALOG = {
    "fresh": "Список документів уже свіжий: його оновлюють не частіше ніж раз на тиждень.",
    "not_a_catalog": "Файл не схожий на список документів порталу. Чергу не змінено.",
    "missing": "Портал не віддав список документів. Чергу не змінено.",
}


def _stamp(moment: float) -> str:
    return datetime.fromtimestamp(moment, rules.day_zone()).strftime("%Y-%m-%d %H:%M")


def _add(state: State, args: argparse.Namespace) -> int:
    numbers = {raw: rules.normalize_nreg(raw) for raw in args.nreg}
    bad = [raw for raw, nreg in numbers.items() if nreg is None]
    if bad:
        print("Не схоже на номер документа: " + ", ".join(bad))
        return 2
    for nreg in numbers.values():
        state.add(nreg or "", args.priority)
    print(f"Додано до черги: {len(numbers)}")
    return 0


@contextmanager
def _only_one(work: Path) -> Iterator[bool]:
    """True if this process is the only one talking to the portal from this working folder.

    Two at once would halve the pauses the portal asks for.
    """
    with open(work / "lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Збирач уже працює в іншому вікні.")
            yield False
        else:
            yield True


@contextmanager
def _journal(work: Path) -> Iterator[logging.Logger]:
    handler = RotatingFileHandler(work / "log.txt", maxBytes=_LOG_BYTES, backupCount=_LOG_FILES, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    journal = logging.getLogger("chynnist_collect")
    journal.addHandler(handler)
    journal.setLevel(logging.INFO)
    try:
        yield journal
    finally:
        journal.removeHandler(handler)
        handler.close()


def _run(state: State, args: argparse.Namespace, work: Path) -> int:
    with _only_one(work) as alone:
        if not alone:
            return 0
        with _journal(work) as journal:
            clock = SystemClock()
            ended = fetch.run(state, Portal(state, Transport(), clock), clock, clock.now() + args.minutes * 60)
            journal.info("END %s", ended)
        print(_ENDED[ended])
    return _status(state)


def _catalog(state: State, args: argparse.Namespace, work: Path) -> int:
    clock = SystemClock()
    try:
        if args.file is not None:
            summary = catalog.load(state, args.file.read_bytes(), clock.now())
        else:
            with _only_one(work) as alone:
                if not alone:
                    return 0
                with _journal(work) as journal:
                    try:
                        summary = catalog.refresh(state, Portal(state, Transport(), clock), clock, work)
                    finally:
                        journal.info("END catalog")
    except CatalogError as e:
        print(_NO_CATALOG[e.code])
        return 0 if e.code == "fresh" else 1
    except Stop as stop:
        print(_ENDED[stop.reason])
        return 1
    except RequestFailed:
        print("Не вдалося завантажити список документів. Спробуйте пізніше.")
        return 1
    except OSError:
        print("Не вдалося прочитати або записати файл списку.")
        return 1
    print(f"Документів у списку порталу: {summary.documents}, нерозібраних рядків: {summary.skipped_lines}")
    return _status(state)


def _status(state: State) -> int:
    clock = SystemClock()
    counts = state.counts()
    requests, used = state.usage(day_of(clock.now()))
    print(f"Документів у списку: {counts.total}")
    print(f"  завантажено: {counts.done}, чекає: {counts.waiting}")
    print(f"  немає на порталі: {counts.missing}, не вдалося: {counts.given_up}")
    print(f"Сьогодні: запитів {requests}, отримано {used / 1_000_000:.1f} МБ з {rules.MAX_BYTES_PER_DAY // 1_000_000}")
    catalog_at = state.catalog_at()
    if catalog_at is not None:
        print(f"Список документів порталу оновлено: {_stamp(catalog_at)}")
    blocked_until = state.blocked_until()
    if blocked_until is not None and blocked_until > clock.now():
        print(f"Портал відмовив у доступі: без запитів до {_stamp(blocked_until)}")
    rest_until = state.rest_until()
    if rest_until is not None and rest_until > clock.now():
        print(f"Перерва після помилок мережі: без запитів до {_stamp(rest_until)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chynnist-collect", description="Збирач «Чинності»")
    parser.add_argument("--work", type=Path, default=Path("work"), help="робоча тека (типово: work)")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="додати документи до черги")
    add.add_argument("nreg", nargs="+", help="номер документа, наприклад 254к/96-вр")
    add.add_argument("--priority", type=int, default=0, help="менше число завантажується раніше")
    run = commands.add_parser("run", help="завантажувати документи з черги")
    run.add_argument("--minutes", type=float, default=55, help="скільки хвилин працювати (типово: 55)")
    cat = commands.add_parser("catalog", help="оновити список усіх документів порталу й чергу")
    cat.add_argument("--file", type=Path, help="узяти список з готового файлу doc.txt, без завантаження")
    commands.add_parser("status", help="показати стан")
    args = parser.parse_args(argv)

    args.work.mkdir(parents=True, exist_ok=True)
    state = State(args.work / "collect.db")
    try:
        if args.command == "add":
            return _add(state, args)
        if args.command == "run":
            return _run(state, args, args.work)
        if args.command == "catalog":
            return _catalog(state, args, args.work)
        return _status(state)
    finally:
        state.close()


if __name__ == "__main__":
    sys.exit(main())
