# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import fcntl

from chynnist_collect.cli import main
from chynnist_collect.state import State


def test_add_and_status(tmp_path, capsys):
    work = tmp_path / "work"
    assert main(["--work", str(work), "add", "254К/96-ВР", "2341-14", "--priority", "1"]) == 0
    assert main(["--work", str(work), "status"]) == 0
    out = capsys.readouterr().out
    assert "Додано до черги: 2" in out and "Документів у списку: 2" in out and "чекає: 2" in out
    state = State(work / "collect.db")
    assert state.next_task(0).nreg == "2341-14"  # stored in the portal's own spelling, in order
    state.close()


def test_bad_number_adds_nothing(tmp_path, capsys):
    assert main(["--work", str(tmp_path), "add", "2341-14", "../etc"]) == 2
    assert "../etc" in capsys.readouterr().out
    assert main(["--work", str(tmp_path), "status"]) == 0
    assert "Документів у списку: 0" in capsys.readouterr().out


def test_run_with_empty_queue_makes_no_requests(tmp_path, capsys):
    assert main(["--work", str(tmp_path), "run", "--minutes", "1"]) == 0
    out = capsys.readouterr().out
    assert "Черга порожня" in out and "запитів 0" in out
    assert "END done" in (tmp_path / "log.txt").read_text(encoding="utf-8")


def test_second_run_at_the_same_time_steps_aside(tmp_path, capsys):
    with open(tmp_path / "lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert main(["--work", str(tmp_path), "run"]) == 0
    assert "уже працює" in capsys.readouterr().out
    assert not (tmp_path / "log.txt").exists()


def test_catalog_from_a_file(tmp_path, capsys, monkeypatch):
    from conftest import REAL_CARD_LINE, card_line, catalog_bytes

    from chynnist_collect import rules

    monkeypatch.setattr(rules, "MIN_CATALOG_ROWS", 2)
    source = tmp_path / "doc.txt"
    source.write_bytes(catalog_bytes(REAL_CARD_LINE, card_line("254К/96-ВР", "Конституція України", types="216"), "x"))
    work = tmp_path / "work"
    assert main(["--work", str(work), "catalog", "--file", str(source)]) == 0
    out = capsys.readouterr().out
    assert "Документів у списку порталу: 2, нерозібраних рядків: 1" in out and "чекає: 2" in out
    assert "Список документів порталу оновлено" in out
    state = State(work / "collect.db")
    assert state.next_task(0).nreg == "254к/96-вр"
    state.close()


def test_catalog_from_a_wrong_or_absent_file(tmp_path, capsys):
    (tmp_path / "doc.txt").write_bytes(b"<html>not a list</html>")
    assert main(["--work", str(tmp_path / "w"), "catalog", "--file", str(tmp_path / "doc.txt")]) == 1
    assert "не схожий на список" in capsys.readouterr().out
    assert main(["--work", str(tmp_path / "w"), "catalog", "--file", str(tmp_path / "none.txt")]) == 1
    assert "Не вдалося прочитати" in capsys.readouterr().out
