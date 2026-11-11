# SPDX-License-Identifier: GPL-3.0-or-later
"""The real network code against a small HTTPS server on this computer (no outside network)."""

from __future__ import annotations

import datetime
import gzip
import http.server
import ipaddress
import ssl
import threading

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from chynnist_collect import rules
from chynnist_collect.transport import Transport, TransportError

PAGE = ("<div id='article'>" + "Стаття 1. Текст. " * 200 + "</div>").encode()


class _Handler(http.server.BaseHTTPRequestHandler):
    seen: list[tuple[str, dict[str, str]]] = []

    def log_message(self, *args) -> None:
        pass

    def _answer(self, status: int, body: bytes = b"", **headers: str) -> None:
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name.replace("_", "-"), value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self.seen.append((self.path, dict(self.headers)))
        path = self.path.split("?")[0]
        if path == "/page":
            self._answer(200, PAGE, Last_Modified="Wed, 11 Nov 2026 10:00:00 GMT")
        elif path == "/gzip":
            self._answer(200, gzip.compress(PAGE), Content_Encoding="gzip")
        elif path == "/bomb":
            self._answer(200, gzip.compress(b"\0" * 100_000), Content_Encoding="gzip")
        elif path == "/broken-gzip":
            self._answer(200, gzip.compress(PAGE)[:-20], Content_Encoding="gzip")
        elif path == "/brotli":
            self._answer(200, b"??", Content_Encoding="br")
        elif path == "/moved":
            # The portal writes Cyrillic addresses as plain UTF-8 bytes.
            raw = "HTTP/1.1 302 Found\r\nLocation: /laws/show/254к/96-вр\r\nContent-Length: 0\r\n\r\n"
            self.wfile.write(raw.encode())
        else:
            self._answer(404, b"no")


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """Base address of the server and a TLS context that trusts its one-day certificate."""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    folder = tmp_path_factory.mktemp("tls")
    (folder / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (folder / "key.pem").write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    server_side = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_side.load_cert_chain(folder / "cert.pem", folder / "key.pem")
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    httpd.socket = server_side.wrap_socket(httpd.socket, server_side=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    trusting = ssl.create_default_context(cafile=str(folder / "cert.pem"))
    yield f"https://localhost:{httpd.server_address[1]}", trusting
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def transport(server):
    _Handler.seen.clear()
    return Transport(allowed_hosts=frozenset({"localhost"}), context=server[1])


def test_page(server, transport):
    response = transport.get(server[0] + "/page", {"User-Agent": "OpenData"})
    assert response.status == 200 and response.body == PAGE and response.wire_bytes == len(PAGE)
    assert response.headers["last-modified"] == "Wed, 11 Nov 2026 10:00:00 GMT"
    _, headers = _Handler.seen[0]
    assert headers["User-Agent"] == "OpenData" and headers["Accept-Encoding"] == "gzip"


def test_cyrillic_address_is_encoded(server, transport):
    transport.get(server[0] + "/laws/show/254к/96-вр?a=б", {})
    assert _Handler.seen[0][0] == "/laws/show/254%D0%BA/96-%D0%B2%D1%80?a=%D0%B1"


def test_packed_answer_is_unpacked_and_counted_as_sent(server, transport):
    response = transport.get(server[0] + "/gzip", {})
    assert response.body == PAGE and response.wire_bytes == len(gzip.compress(PAGE)) < len(PAGE) // 10


def test_small_answer_that_unpacks_into_a_huge_one_is_refused(server, transport, monkeypatch):
    monkeypatch.setattr(rules, "MAX_DECODED_BYTES", 50_000)
    with pytest.raises(TransportError) as e:
        transport.get(server[0] + "/bomb", {})
    assert e.value.code == "too_large" and 0 < e.value.wire_bytes < 1000


@pytest.mark.parametrize("path", ["/broken-gzip", "/brotli"])
def test_answer_we_cannot_unpack(server, transport, path):
    with pytest.raises(TransportError) as e:
        transport.get(server[0] + path, {})
    assert e.value.code == "bad_encoding" and e.value.wire_bytes > 0


def test_too_large_answer_is_cut_off(server, transport):
    with pytest.raises(TransportError) as e:
        transport.get(server[0] + "/page", {}, max_bytes=1000)
    assert e.value.code == "too_large" and 1000 < e.value.wire_bytes <= len(PAGE)


def test_redirect_is_returned_not_followed(server, transport):
    response = transport.get(server[0] + "/moved", {})
    assert response.status == 302 and response.headers["location"] == "/laws/show/254к/96-вр"
    assert len(_Handler.seen) == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/page",
        "https://example.org/page",
        "https://user:pass@localhost/page",
        "https://localhost.example.org/page",
        "ftp://localhost/page",
        "https://[bad/page",
        "",
    ],
)
def test_other_addresses_are_refused_before_any_connection(transport, url):
    with pytest.raises(TransportError) as e:
        transport.get(url, {})
    assert e.value.code == "bad_url" and _Handler.seen == []


def test_real_portal_hosts_are_the_only_default():
    assert Transport().allowed_hosts == {"data.rada.gov.ua", "zakon.rada.gov.ua"}


def test_untrusted_certificate_is_a_failure(server):
    careful = Transport(allowed_hosts=frozenset({"localhost"}))  # the usual trust store
    _Handler.seen.clear()
    with pytest.raises(TransportError) as e:
        careful.get(server[0] + "/page", {"User-Agent": "OpenData"})
    assert e.value.code == "network" and _Handler.seen == []


def test_nobody_listening_is_a_failure(transport):
    with pytest.raises(TransportError) as e:
        transport.get("https://localhost:1/page", {})
    assert e.value.code == "network"


def test_whole_chain_from_queue_to_stored_page(server, transport, state, clock, monkeypatch):
    """Queue, polite client and real network code together; only the clock is fake."""
    from chynnist_collect import fetch
    from chynnist_collect.portal import Portal

    monkeypatch.setattr(rules, "PORTAL_ORIGIN", server[0])
    monkeypatch.setattr(rules, "show_url_path", lambda nreg: "/" + nreg)
    state.add("page", 0)
    state.add("gzip", 1)
    state.add("nothing", 2)
    assert fetch.run(state, Portal(state, transport, clock), clock, clock.now() + 600) == "done"
    assert state.page("page") == PAGE and state.page("gzip") == PAGE and state.page("nothing") is None
    assert [headers["User-Agent"] for _, headers in _Handler.seen] == ["OpenData"] * 3
    assert len(clock.sleeps) == 2 and all(5.0 <= pause <= 7.0 for pause in clock.sleeps)
