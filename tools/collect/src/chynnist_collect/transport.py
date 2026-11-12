# SPDX-License-Identifier: GPL-3.0-or-later
"""One HTTPS request with hard limits. Knows nothing about pauses and daily limits (see portal.py).

Uses http.client directly: it never follows redirects and never uses a proxy on its own, so every
network step of the collector is visible in portal.py.
"""

from __future__ import annotations

import http.client
import ssl
import time
import zlib
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

from . import rules

_CHUNK = 64 * 1024


class TransportError(Exception):
    """The request failed. `code` is stable and safe to log; `wire_bytes` were still received."""

    def __init__(self, code: str, wire_bytes: int = 0) -> None:
        super().__init__(code)
        self.code = code
        self.wire_bytes = wire_bytes


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]  # names in lower case
    body: bytes  # unpacked
    wire_bytes: int  # size of the answer body as it came over the network


def _header_text(value: str) -> str:
    """http.client reads headers as Latin-1, but the portal writes Cyrillic addresses in UTF-8."""
    try:
        return value.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return value


def _gunzip(data: bytes) -> bytes:
    """Unpacks no more than the limit, so that a small malicious answer cannot fill the memory."""
    unpacker = zlib.decompressobj(wbits=31)
    try:
        out = unpacker.decompress(data, rules.MAX_DECODED_BYTES + 1)
    except zlib.error as e:
        raise TransportError("bad_encoding", len(data)) from e
    if len(out) > rules.MAX_DECODED_BYTES or unpacker.unconsumed_tail:
        raise TransportError("too_large", len(data))
    if not unpacker.eof:
        raise TransportError("bad_encoding", len(data))
    return out


class Transport:
    def __init__(
        self,
        *,
        allowed_hosts: frozenset[str] = rules.FETCH_HOSTS,
        context: ssl.SSLContext | None = None,
    ) -> None:
        self.allowed_hosts = allowed_hosts
        self.context = context or ssl.create_default_context()

    def _target(self, url: str) -> tuple[str, int | None, str]:
        """Host, port and request target of an allowed address; anything else is refused."""
        try:
            parts = urlsplit(url)
            host, port = parts.hostname or "", parts.port
        except ValueError as e:
            raise TransportError("bad_url") from e
        if parts.scheme != "https" or host not in self.allowed_hosts or parts.username or parts.password:
            raise TransportError("bad_url")
        target = quote(parts.path or "/", safe="/%.-_~")
        if parts.query:
            target += "?" + quote(parts.query, safe="=&%.-_~")
        return host, port, target

    def get(self, url: str, headers: dict[str, str], max_bytes: int = rules.MAX_RESPONSE_BYTES) -> Response:
        host, port, target = self._target(url)
        deadline = time.monotonic() + rules.RESPONSE_DEADLINE_SECONDS
        received = 0
        conn = http.client.HTTPSConnection(host, port, timeout=rules.SOCKET_TIMEOUT_SECONDS, context=self.context)
        try:
            conn.request("GET", target, headers={**headers, "Accept-Encoding": "gzip", "Connection": "close"})
            answer = conn.getresponse()
            chunks: list[bytes] = []
            while chunk := answer.read(_CHUNK):
                received += len(chunk)
                if received > max_bytes:
                    raise TransportError("too_large", received)
                if time.monotonic() > deadline:
                    raise TransportError("timeout", received)
                chunks.append(chunk)
            names = {name.lower(): _header_text(value) for name, value in answer.getheaders()}
            status = answer.status
        except (OSError, http.client.HTTPException, ValueError) as e:
            # ValueError: http.client refuses a header or address with control characters.
            raise TransportError("network", received) from e
        finally:
            conn.close()
        body = b"".join(chunks)
        encoding = names.get("content-encoding", "").strip().lower()
        if encoding == "gzip":
            body = _gunzip(body)
        elif encoding not in ("", "identity"):
            raise TransportError("bad_encoding", received)
        return Response(status, names, body, received)
