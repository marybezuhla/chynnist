# SPDX-License-Identifier: GPL-3.0-or-later
"""The Keychain is replaced with a small stand-in for the `security` command."""

from __future__ import annotations

import subprocess

import pytest
from suvii import keys

from chynnist_collect import rules, signing


class FakeKeychain:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], str] = {}
        self.calls: list[list[str]] = []

    def __call__(self, *args: str) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        named = dict(zip(args[1::2], args[2::2], strict=False))
        item = (named.get("-s"), named.get("-a"))
        if args[0] == "find-generic-password":
            if item in self.items:
                return subprocess.CompletedProcess(args, 0, self.items[item] + "\n", "")
            return subprocess.CompletedProcess(args, 44, "", "not found")
        if args[0] == "add-generic-password":
            self.items[item] = named["-w"]
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(args)


@pytest.fixture
def keychain(monkeypatch):
    fake = FakeKeychain()
    monkeypatch.setattr(signing, "_security", fake)
    return fake


def test_create_then_load(keychain):
    public = signing.create()
    key = signing.load()
    assert keys.public_text(key) == public
    assert list(keychain.items) == [(rules.KEYCHAIN_SERVICE, rules.KEYCHAIN_ACCOUNT)]


def test_existing_key_is_never_replaced(keychain):
    signing.create()
    before = dict(keychain.items)
    with pytest.raises(signing.SigningKeyError) as e:
        signing.create()
    assert e.value.code == "exists" and keychain.items == before


def test_missing_and_damaged_key(keychain):
    with pytest.raises(signing.SigningKeyError) as e:
        signing.load()
    assert e.value.code == "missing"
    keychain.items[(rules.KEYCHAIN_SERVICE, rules.KEYCHAIN_ACCOUNT)] = "not a key"
    with pytest.raises(signing.SigningKeyError) as e:
        signing.load()
    assert e.value.code == "bad"


def test_not_a_mac(monkeypatch):
    monkeypatch.setattr(signing, "_SECURITY", "/nonexistent/security")
    with pytest.raises(signing.SigningKeyError) as e:
        signing.load()
    assert e.value.code == "no_keychain"
