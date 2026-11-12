# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

import pytest
from suvii.html import check_html

from chynnist_collect import Converted, Styles, convert

FIXTURES = Path(__file__).parent / "fixtures"

# Written by hand in the manner of the portal's stylesheet. It is not a copy of u_text.css:
# the tests only need some classes with a known meaning.
SAMPLE_CSS = """
/* text styles */
.rvts9, .rvts15, .rvts78 { font-weight: bold; }
span.rvts46, .rvts11 { font-style: italic }
.rvts37 { vertical-align: super; font-weight: 700; font-size: 80% }
.rvts52 { text-decoration: underline line-through }
.rvts90 { vertical-align: sub }
.gone { display: none }
/* paragraph styles */
p.rvps2 { text-align: justify; text-indent: 30px }
.rvps7, .rvps4, .rvps12 { text-align: center; }
.rvps11 { text-align: right }
@media print { .rvts9 { font-weight: normal; font-style: italic } }
@import url("other.css");
.rvts15 { font-size: 14pt }
"""


@pytest.fixture(scope="session")
def styles() -> Styles:
    return Styles.from_css(SAMPLE_CSS)


@pytest.fixture
def conv(styles):
    """Converts a fragment as the text of document 100-20 and checks that the result is safe HTML."""

    def _conv(fragment: str, nreg: str = "100-20") -> Converted:
        result = convert(f'<html><body><div id="article">{fragment}</div></body></html>', nreg=nreg, styles=styles)
        ids = check_html(result.body)
        assert {entry.anchor for entry in result.toc} <= ids
        return result

    return _conv


@pytest.fixture(scope="session")
def constitution_page() -> str:
    return (FIXTURES / "constitution_part.html").read_text(encoding="utf-8")


# --- a fake portal: time that does not pass, a network that is a list of prepared answers

class FakeClock:
    """Starts at noon by Kyiv time, 11 November 2026. Sleeping moves the time and is recorded."""

    def __init__(self) -> None:
        self.moment = 1794391200.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.moment

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.moment += seconds


class FakeSender:
    """Answers from `routes` (address -> answer, exception, or a list of them used one by one)."""

    def __init__(self, clock: FakeClock, routes: dict | None = None, took: float = 0.0) -> None:
        self.clock = clock
        self.routes = routes or {}
        self.took = took  # how long each answer takes
        self.calls: list[tuple[float, str, dict[str, str]]] = []

    def get(self, url, headers, max_bytes=0):
        self.calls.append((self.clock.now(), url, dict(headers)))
        self.clock.moment += self.took
        answer = self.routes.get(url, answer_of(404))
        if isinstance(answer, list):
            answer = answer.pop(0) if len(answer) > 1 else answer[0]
        if isinstance(answer, Exception):
            raise answer
        return answer


def answer_of(status: int, body: bytes = b"", **headers: str):
    from chynnist_collect.transport import Response

    return Response(status, {name.replace("_", "-"): value for name, value in headers.items()}, body, len(body))


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def state(tmp_path):
    from chynnist_collect.state import State

    s = State(tmp_path / "collect.db")
    yield s
    s.close()


# The one real line we have of the portal's list of documents (doc.txt), as given in its description.
REAL_CARD_LINE = "558207\tn0438500-26\tПро облікову ціну банківських металів\t0\t95\t70:20261103:\t\t2\t20261103"


def card_line(nreg: str, title: str, status: int = 5, types: str = "1", edition: str = "20260101") -> str:
    """A made-up line in the documented format of doc.txt."""
    return f"1\t{nreg}\t{title}\t{status}\t{types}\t1:{edition}:\t\t1\t{edition}"


def catalog_bytes(*lines: str) -> bytes:
    return "\r\n".join(lines).encode("cp1251") + b"\r\n"
