# SPDX-License-Identifier: GPL-3.0-or-later
"""Publishing a month: a base, then patches from every earlier state, then a new month."""

from __future__ import annotations

import json
import shutil

import pytest
from suvii import Document, SuviiError, Writer, apply_patch_copy, keys, open_scroll

from chynnist_collect import release, rules
from chynnist_collect.release import ReleaseError

KEY = keys.generate()
NOW = 1794391200.0


def scroll(path, seq, texts: dict[str, str], key=KEY):
    with Writer(
        path, collection_id=rules.COLLECTION_ID, title="Тест", language="uk", publisher="Test",
        fields=rules.collection_fields(), seq=seq, source_date="2026-11-01",
    ) as w:  # fmt: skip
        for nreg, text in texts.items():
            w.add(Document(path=rules.doc_path(nreg), title=nreg, body=f"<p>{text}</p>", updated="2026-11-01T00:00:00Z"))
        w.finish(key)
    return path


def read_index(work):
    data = (work / "outbox" / "data" / "index.json").read_bytes()
    sig = (work / "outbox" / "data" / "index.sig").read_text().strip()
    assert keys.verify([keys.public_text(KEY)], sig, rules.INDEX_SIG_PREFIX + data)
    assert not keys.verify([keys.public_text(KEY)], sig, data)  # the prefix is part of what is signed
    return json.loads(data)


def send(work):
    """What the publisher does after uploading: clears the outbox."""
    sent = {p.relative_to(work / "outbox").as_posix(): p.read_bytes() for p in (work / "outbox").rglob("*") if p.is_file()}
    shutil.rmtree(work / "outbox")
    return sent


@pytest.fixture
def work(tmp_path):
    (tmp_path / "work").mkdir()
    return tmp_path / "work"


STATES = {
    1: {"1-20": "один", "2-20": "два", "3-20": "три"},
    2: {"1-20": "один", "2-20": "два, нова редакція", "3-20": "три"},
    3: {"1-20": "один", "2-20": "два, нова редакція", "4-20": "чотири"},
}


def test_a_month_of_releases(tmp_path, work):
    made = {seq: scroll(tmp_path / f"s{seq}.suvii", seq, texts) for seq, texts in STATES.items()}

    first = release.prepare(work, made[1], KEY, now=NOW, month="2026-11")
    assert (first.seq, first.new_base, first.patches) == (1, True, 0)
    index = read_index(work)
    assert index["seq"] == 1 and index["patches"] == [] and index["collection"] == rules.COLLECTION_ID
    assert index["base"]["url"] == rules.RELEASES_URL + "data-2026-11/chynnist-1.suvii"
    sent = send(work)
    assert sorted(sent) == ["data-2026-11/chynnist-1.suvii", "data/index.json", "data/index.sig"]
    assert sent["data-2026-11/chynnist-1.suvii"] == made[1].read_bytes()

    release.prepare(work, made[2], KEY, now=NOW + 7 * 86400, month="2026-11")
    assert sorted(send(work)) == ["data-2026-11/chynnist-1-2.patch.suvii", "data/index.json", "data/index.sig"]

    third = release.prepare(work, made[3], KEY, now=NOW + 14 * 86400, month="2026-11")
    assert (third.new_base, third.patches) == (False, 2)
    index = read_index(work)
    assert index["seq"] == 3 and index["base"]["seq"] == 1
    assert [(p["from"], p["to"]) for p in index["patches"]] == [(1, 3), (2, 3)]
    sent = send(work)
    assert "data-2026-11/chynnist-1.suvii" not in sent  # the base is uploaded once a month

    # A phone on any state of the month reaches state 3 with one patch, and the result is signed.
    trusted = [keys.public_text(KEY)]
    with open_scroll(made[3], trusted) as target:
        expected = target.state_root()
    for start in (1, 2):
        patch = tmp_path / f"p{start}.suvii"
        patch.write_bytes(sent[f"data-2026-11/chynnist-{start}-3.patch.suvii"])
        entry = next(p for p in index["patches"] if p["from"] == start)
        assert entry["size"] == patch.stat().st_size
        assert apply_patch_copy(made[start], patch, tmp_path / f"r{start}.suvii", trusted) == 3
        with open_scroll(tmp_path / f"r{start}.suvii", trusted) as result:
            assert result.state_root() == expected
            assert result.document("laws/2-20").body == "<p>два, нова редакція</p>"

    # A new month starts a new base; the states of the old month are forgotten.
    fourth = release.prepare(work, scroll(tmp_path / "s4.suvii", 4, STATES[3]), KEY, now=NOW + 30 * 86400, month="2026-12")
    assert (fourth.new_base, fourth.patches) == (True, 0)
    assert read_index(work)["base"]["url"] == rules.RELEASES_URL + "data-2026-12/chynnist-4.suvii"
    assert sorted(p.name for p in (work / "published").iterdir()) == ["chynnist-4.suvii"]


def test_unsent_outbox_is_never_overwritten(tmp_path, work):
    release.prepare(work, scroll(tmp_path / "a.suvii", 1, STATES[1]), KEY, now=NOW, month="2026-11")
    with pytest.raises(ReleaseError) as e:
        release.prepare(work, scroll(tmp_path / "b.suvii", 2, STATES[2]), KEY, now=NOW, month="2026-11")
    assert e.value.code == "outbox_full"
    assert (work / "outbox" / "data-2026-11" / "chynnist-1.suvii").exists()


def test_older_state_and_foreign_scrolls_are_refused(tmp_path, work):
    release.prepare(work, scroll(tmp_path / "a.suvii", 5, STATES[1]), KEY, now=NOW, month="2026-11")
    send(work)
    ledger = (work / "published.json").read_bytes()
    with pytest.raises(ReleaseError) as e:
        release.prepare(work, scroll(tmp_path / "b.suvii", 5, STATES[2]), KEY, now=NOW, month="2026-11")
    assert e.value.code == "not_newer"
    with pytest.raises(SuviiError):  # a trial build is signed with a throwaway key
        release.prepare(work, scroll(tmp_path / "c.suvii", 6, STATES[2], key=keys.generate()), KEY, now=NOW, month="2026-11")
    assert (work / "published.json").read_bytes() == ledger and not (work / "outbox").exists()


def test_failure_while_patching_changes_nothing(tmp_path, work, monkeypatch):
    release.prepare(work, scroll(tmp_path / "a.suvii", 1, STATES[1]), KEY, now=NOW, month="2026-11")
    send(work)
    ledger = (work / "published.json").read_bytes()

    def broken(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(release, "make_patch", broken)
    with pytest.raises(OSError):
        release.prepare(work, scroll(tmp_path / "b.suvii", 2, STATES[2]), KEY, now=NOW, month="2026-11")
    assert (work / "published.json").read_bytes() == ledger
    assert sorted(p.name for p in (work / "published").iterdir()) == ["chynnist-1.suvii"]
    assert not (work / "outbox").exists()


def test_new_base_on_request(tmp_path, work):
    release.prepare(work, scroll(tmp_path / "a.suvii", 1, STATES[1]), KEY, now=NOW, month="2026-11")
    send(work)
    done = release.prepare(work, scroll(tmp_path / "b.suvii", 2, STATES[2]), KEY, now=NOW, month="2026-11", new_base=True)
    assert done.new_base and read_index(work)["patches"] == []
