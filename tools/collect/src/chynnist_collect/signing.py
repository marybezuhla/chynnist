# SPDX-License-Identifier: GPL-3.0-or-later
"""The data signing key (ed25519). It exists only in the Keychain of the publisher's Mac.

The phone app trusts a collection only if it is signed with this key, so the key never goes into
a file, a repository, a log or GitHub.
"""

from __future__ import annotations

import subprocess

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from suvii import keys

from . import rules

_SECURITY = "/usr/bin/security"


class SigningKeyError(Exception):
    """`code`: missing (no key yet), exists (keygen would overwrite), no_keychain (not a Mac), bad."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _security(*args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run([_SECURITY, *args], capture_output=True, text=True, timeout=60, check=False)
    except FileNotFoundError as e:
        raise SigningKeyError("no_keychain") from e


def load() -> Ed25519PrivateKey:
    found = _security(
        "find-generic-password", "-s", rules.KEYCHAIN_SERVICE, "-a", rules.KEYCHAIN_ACCOUNT, "-w"
    )
    if found.returncode != 0:
        raise SigningKeyError("missing")
    try:
        return keys.private_from_text(found.stdout)
    except ValueError as e:
        raise SigningKeyError("bad") from e


def create() -> str:
    """Makes the key, keeps it in the Keychain and returns the public key for the app."""
    try:
        load()
    except SigningKeyError as e:
        if e.code != "missing":
            raise
    else:
        raise SigningKeyError("exists")  # a new key would make every installed app reject our data
    key = keys.generate()
    # `security` takes the secret as an argument. Other programs of the same user could see it in
    # the process list for that moment; on a personal Mac this is accepted, and nothing is written.
    added = _security(
        "add-generic-password", "-s", rules.KEYCHAIN_SERVICE, "-a", rules.KEYCHAIN_ACCOUNT,
        "-l", "Chynnist data signing key", "-w", keys.private_to_text(key),
    )  # fmt: skip
    if added.returncode != 0:
        raise SigningKeyError("bad")
    if keys.public_text(load()) != keys.public_text(key):
        raise SigningKeyError("bad")
    return keys.public_text(key)
