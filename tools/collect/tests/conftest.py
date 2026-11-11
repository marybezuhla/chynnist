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
