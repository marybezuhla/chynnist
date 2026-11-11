# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import unicodedata

import pytest
from suvii import TocEntry

from chynnist_collect import ConvertError, convert, rules


def test_formatting_around_paragraphs_goes_inside(conv):
    r = conv('<em><p class="rvps2"><span class="rvts46">{Note </span><a href="/laws/show/1-20">N 1</a>}</p></em><p>Plain</p>')
    assert r.body == '<p><i>{Note <a href="suvii:laws/1-20">N 1</a>}</i></p>\n<p>Plain</p>'


def test_classes_become_elements(conv):
    r = conv('<p class="rvps7"><span class="rvts9">Bold</span> and <span class="rvts52">old</span> H<span class="rvts90">2</span>O</p>')
    assert r.body == '<p class="suvii-center"><b>Bold</b> and <u><s>old</s></u> H<sub>2</sub>O</p>'


def test_same_text_gives_same_bytes_whatever_the_nesting(conv):
    a = conv("<p><b><i>x</i></b><b><i> y</i></b></p>").body
    b = conv("<p><i><b>x y</b></i></p>").body
    c = conv('<p><span class="rvts9"><em>x</em><em> y</em></span></p>').body
    assert a == b == c == "<p><b><i>x y</i></b></p>"


def test_anchor_becomes_id_and_contents_entry(conv):
    r = conv(
        '<p class="rvps7"><a name="n1" data-tree="rz1"></a><span class="rvts15">Розділ I </span><br><span class="rvts15">ЗАГАЛЬНІ ЗАСАДИ</span></p>'
        '<p><a name="n2" data-tree="gl2:rz1"></a>Глава 2</p>'
        '<p><a name="n3" data-tree="st5-1:gl2:rz1"></a><span class="rvts9">Стаття 5<span class="rvts37"><span style="font-size:0px">-</span>1</span>.</span> Text.</p>'
        '<p><a name="n4" data-tree="ch_1:st5-1"></a>Part one.</p>'
    )
    assert r.toc == [
        TocEntry(1, "n1", "Розділ I ЗАГАЛЬНІ ЗАСАДИ"),
        TocEntry(2, "n2", "Глава 2"),
        TocEntry(3, "n3", "Стаття 5-1. Text."),
    ]
    assert '<p id="n1" class="suvii-center"><b>Розділ I<br>ЗАГАЛЬНІ ЗАСАДИ</b></p>' in r.body
    # The hyphen is invisible on the portal; here it stays, so that "5-1" can be searched and copied.
    assert '<p id="n3"><b>Стаття 5<sup>-1</sup>.</b> Text.</p>' in r.body
    assert '<p id="n4">Part one.</p>' in r.body


def test_editorial_note_is_marked(conv):
    r = conv('<p><a name="n7" data-tree="cm_1:st3"></a>{Changed}</p>')
    assert r.body == '<p id="n7" class="suvii-note">{Changed}</p>'
    assert r.toc == []


def test_long_contents_title_is_shortened(conv):
    r = conv(f'<p><a name="n1" data-tree="st1"></a>Стаття 1. {"слово " * 100}</p>')
    title = r.toc[0].title
    assert len(title) <= rules.TOC_TITLE_CHARS + 1 and title.endswith("слово…")


def test_empty_paragraph_is_dropped_but_its_anchor_lives(conv):
    r = conv('<p><a name="n1"></a><span><br></span></p><div><a name="n2"></a></div><p> \n </p><p><a name="n3"></a>Text <a href="#n1">up</a></p>')
    assert r.body == '<p id="n1"><span id="n2"></span><span id="n3"></span>Text <a href="#n1">up</a></p>'


def test_anchor_after_last_text_is_kept(conv):
    r = conv('<p>Text</p><p><a name="n9"></a></p>')
    assert r.body == '<p>Text</p>\n<p id="n9"></p>'


def test_anchor_in_the_middle_of_text(conv):
    r = conv('<p><a name="n1"></a>One <a name="n2" data-tree="st2"></a>two</p>')
    assert r.body == '<p id="n1">One <span id="n2"></span>two</p>'
    assert r.toc == [TocEntry(3, "n2", "One two")]


def test_duplicate_and_bad_anchors_are_ignored(conv):
    r = conv('<p><a name="n1"></a>A</p><p><a name="n1"></a>B</p><p><a name="x y"></a>C</p>')
    assert r.body == '<p id="n1">A</p>\n<p>B</p>\n<p>C</p>'


def test_white_space(conv):
    r = conv("<p>\n  One  <b> two </b>\n three<br>  four  <br><br></p><p>ст. 5 </p>")
    assert r.body == "<p>One <b>two </b>three<br>four</p>\n<p>ст. 5</p>"


def test_text_outside_paragraphs(conv):
    r = conv("Loose <b>text</b><div>In a block</div> tail")
    assert r.body == "<p>Loose <b>text</b></p>\n<p>In a block</p>\n<p>tail</p>"


def test_missing_end_tags(conv):
    r = conv("<p>One<p>Two<table><tr><td>A<td>B<tr><td>C<td>D</table>Three")
    assert r.body == (
        "<p>One</p>\n<p>Two</p>\n<table>\n<tr>\n<td><p>A</p></td>\n<td><p>B</p></td>\n</tr>\n"
        "<tr>\n<td><p>C</p></td>\n<td><p>D</p></td>\n</tr>\n</table>\n<p>Three</p>"
    )


def test_layout_table_becomes_paragraphs(conv):
    r = conv(
        '<div class="rvps14"><a name="n1" data-tree="nz_1"></a><table width="100%" border="0"><tbody>'
        '<tr valign="top"><td width="809"><p class="rvps4"><img src="https://example.org/gerb.gif"></p></td></tr>'
        '<tr><td><p class="rvps4"><span class="rvts78">КОНСТИТУЦІЯ</span></p></td></tr></tbody></table></div>'
    )
    assert r.body == '<p id="n1" class="suvii-center"><b>КОНСТИТУЦІЯ</b></p>'
    assert r.report.images == 1


def test_real_table_is_kept(conv):
    r = conv(
        '<table border="1" style="width:100%"><thead><tr><th colspan="2" onclick="x()">Head</th></tr></thead>'
        '<tr><td rowspan="0">1</td><td align="right" class="rvts9">2<p>3</p></td></tr>'
        "<tr><td></td><td>4</td></tr></table>"
    )
    assert r.body == (
        '<table>\n<tr>\n<th colspan="2"><p>Head</p></th>\n</tr>\n'
        '<tr>\n<td><p>1</p></td>\n<td><p class="suvii-right"><b>2</b></p>\n<p class="suvii-right"><b>3</b></p></td>\n</tr>\n'
        "<tr>\n<td></td>\n<td><p>4</p></td>\n</tr>\n</table>"
    )


def test_text_lost_inside_a_table_is_written_before_it(conv):
    r = conv("<table>stray<tr>text<td>A</td><td>B</td><b>bold</b></tr><caption>Cap</caption></table>")
    assert r.body.startswith("<p>stray text <b>bold</b></p>\n<p>Cap</p>\n<table>")
    assert "<td><p>A</p></td>\n<td><p>B</p></td>" in r.body


def test_lists_keep_their_text_and_are_reported(conv):
    r = conv("<ol><li>One<li>Two</ol>")
    assert r.body == "<p>One</p>\n<p>Two</p>"
    assert r.report.unknown_tags == ("li", "ol")


def test_empty_table_is_dropped(conv):
    assert conv("<p>A</p><table><tr><td> </td><td><br></td></tr></table>").body == "<p>A</p>"


def test_preformatted_text(conv):
    r = conv("<pre>\n  Стаття 1.\r\n    Text <b>bold</b><br>end  \n</pre>")
    assert r.body == "<pre>  Стаття 1.\n    Text <b>bold</b>\nend</pre>"


def test_unsafe_content_is_removed(conv):
    r = conv(
        '<p onclick="x()" style="color:red">A<script>alert("x")</script><style>p{}</style>'
        '<iframe src="https://example.org"></iframe><img src="x" onerror="y()"><!-- c --></p>'
        '<p><a href="javascript:alert(1)">B</a> <a href="http://example.org">C</a> <a href="#nowhere">D</a></p>'
        '<p><span class="gone">hidden</span><span style="display: none">too</span>E &lt;b&gt; &amp;</p>'
    )
    assert r.body == "<p>A</p>\n<p>B C D</p>\n<p>E &lt;b&gt; &amp;</p>"
    assert r.report.dropped_links == 2 and r.report.images == 1


def test_link_to_this_document_and_to_another(conv):
    r = conv(
        '<p><a name="n5"></a><a class="rvts99" href="https://zakon.rada.gov.ua/laws/show/100-20#n5">here</a>, '
        '<a href="https://zakon.rada.gov.ua/laws/show/100-20#n99">gone</a>, '
        '<a href="https://zakon.rada.gov.ua/laws/show/2222-15#n2" target="_blank">there</a></p>'
    )
    assert r.body == '<p id="n5"><a href="#n5">here</a>, gone, <a href="suvii:laws/2222-15#n2">there</a></p>'


def test_link_with_superscript_stays_one_link(conv):
    r = conv('<p><a name="n5"></a><a href="#n5">статтею 149</a><a class="rvts37" href="#n5"><span style="font-size:0px">-</span>1</a> Конституції</p>')
    assert r.body == '<p id="n5"><a href="#n5">статтею 149<b><sup>-1</sup></b></a> Конституції</p>'


def test_report_names_new_markup(conv):
    r = conv('<p class="rvps999 other"><a name="n1" data-tree="kn1"></a><span class="rvts998">A</span><blink>B</blink></p>')
    assert r.report.unknown_kinds == ("kn",)
    assert r.report.unknown_classes == ("rvps999", "rvts998")
    assert r.report.unknown_tags == ("blink",)
    assert r.report.text_chars == 2


def test_body_is_nfc_even_with_stray_combining_marks(conv):
    # "и" + breve must become "й"; a lone overlay after a tag must not merge with ">".
    r = conv("<p>й <b≯x</b></p>")
    assert r.body == "<p>й <b>&#x338;x</b></p>"
    assert unicodedata.is_normalized("NFC", r.body)


def test_page_without_text_is_an_error():
    with pytest.raises(ConvertError) as e:
        convert("<html><body><h1>403 Forbidden</h1></body></html>", nreg="100-20")
    assert e.value.code == "no_article"


def test_too_deep_page_is_an_error():
    with pytest.raises(ConvertError) as e:
        convert('<div id="article">' + "<div>" * (rules.MAX_DEPTH + 5) + "x", nreg="100-20")
    assert e.value.code == "too_deep"


def test_bad_document_number():
    with pytest.raises(ValueError):
        convert('<div id="article"><p>x</p></div>', nreg="../x")


def test_without_styles_the_text_is_still_whole():
    r = convert('<div id="article"><p class="rvps7"><span class="rvts9">Стаття 1.</span> Text</p></div>', nreg="100-20")
    assert r.body == "<p>Стаття 1. Text</p>"
    assert r.report.unknown_classes == ("rvps7", "rvts9")
