# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepares a new state of the collection for publishing: the files and a signed index.

Once a month the new state becomes the base that new installations download whole. In between,
each new state comes as patches: one from every earlier state of the month, so that a phone on
any of them needs exactly one small download. Nothing is uploaded here; the files are put into
`outbox/<release>/` and the publisher uploads them.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from suvii import SuviiError, keys, make_patch, open_scroll

from . import rules

LEDGER = "published.json"
STATES = "published"
OUTBOX = "outbox"


class ReleaseError(Exception):
    """`code`: not_newer (the state is not newer than the last one), wrong_collection,
    outbox_full (the files of the previous state have not been uploaded and cleared yet)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Prepared:
    seq: int
    new_base: bool
    patches: int
    outbox: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(path: Path, tag: str) -> dict:
    return {
        "file": path.name,
        "url": rules.RELEASES_URL + tag + "/" + path.name,
        "size": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _read_ledger(work: Path) -> dict:
    """What has been published: the month of the base and every state of that month, oldest first."""
    try:
        return json.loads((work / LEDGER).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"month": "", "states": []}


def _write_atomically(path: Path, data: bytes) -> None:
    partial = path.with_name(path.name + ".part")
    partial.write_bytes(data)
    os.replace(partial, path)


def sign_index(index: dict, key: Ed25519PrivateKey) -> tuple[bytes, bytes]:
    """The bytes of index.json and of index.sig. The app checks the signature over these exact bytes."""
    data = json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8") + b"\n"
    return data, (keys.sign(key, rules.INDEX_SIG_PREFIX + data) + "\n").encode("ascii")


def prepare(
    work: Path, new_path: Path, key: Ed25519PrivateKey, *, now: float, month: str, new_base: bool = False
) -> Prepared:
    """Puts the state `new_path` into the publishing ledger and fills the outbox.

    Raises ReleaseError, SuviiError (the file is damaged or signed with another key), OSError.
    """
    trusted = [keys.public_text(key)]
    with open_scroll(new_path, trusted) as new:
        if new.kind != "base" or new.collection_id != rules.COLLECTION_ID:
            raise ReleaseError("wrong_collection")
        seq = new.seq
    ledger = _read_ledger(work)
    if ledger["states"] and seq <= ledger["states"][-1]:
        raise ReleaseError("not_newer")
    states_dir = work / STATES
    states_dir.mkdir(exist_ok=True)
    outbox = work / OUTBOX
    if outbox.exists() and any(outbox.iterdir()):
        # The month's base goes into the outbox only once; clearing it here could lose it unseen.
        raise ReleaseError("outbox_full")

    starts_month = new_base or ledger["month"] != month or not ledger["states"]
    month_dir = outbox / rules.month_tag(month if starts_month else ledger["month"])
    month_dir.mkdir(parents=True)
    kept = states_dir / rules.base_file(seq)
    shutil.copyfile(new_path, kept)
    try:
        with open_scroll(kept, trusted) as new:
            earlier = [] if starts_month else ledger["states"]
            for old_seq in earlier:
                with open_scroll(states_dir / rules.base_file(old_seq), trusted) as old:
                    make_patch(old, new, month_dir / rules.patch_file(old_seq, seq), key)
    except BaseException:
        kept.unlink(missing_ok=True)
        shutil.rmtree(outbox, ignore_errors=True)
        raise

    if starts_month:
        shutil.copyfile(kept, month_dir / kept.name)
        ledger = {"month": month, "states": [seq]}
    else:
        ledger = {"month": ledger["month"], "states": [*ledger["states"], seq]}

    tag = rules.month_tag(ledger["month"])
    base_seq = ledger["states"][0]
    base = month_dir / rules.base_file(base_seq) if starts_month else states_dir / rules.base_file(base_seq)
    index = {
        "format": rules.INDEX_FORMAT,
        "collection": rules.COLLECTION_ID,
        "created": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seq": seq,
        "base": {"seq": base_seq, **_entry(base, tag)},
        "patches": [
            {"from": path_from, "to": seq, **_entry(month_dir / rules.patch_file(path_from, seq), tag)}
            for path_from in ledger["states"][:-1]
        ],
    }
    data, sig = sign_index(index, key)
    index_dir = outbox / rules.INDEX_TAG
    index_dir.mkdir()
    (index_dir / "index.json").write_bytes(data)
    (index_dir / "index.sig").write_bytes(sig)
    # The ledger changes last: if anything above failed, the next run starts from the same place.
    _write_atomically(work / LEDGER, json.dumps(ledger).encode("utf-8"))
    for old in states_dir.iterdir():  # states of a past month are no longer patched from
        if old.name not in {rules.base_file(s) for s in ledger["states"]}:
            old.unlink()
    return Prepared(seq, starts_month, len(index["patches"]), outbox)


__all__ = ["Prepared", "ReleaseError", "SuviiError", "prepare", "sign_index"]
