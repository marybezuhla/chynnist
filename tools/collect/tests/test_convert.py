# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import unicodedata

import pytest
from suvii import TocEntry

from chynnist_collect import ConvertError, convert, rules


def test_formatting_around_paragraphs_goes_inside(conv):
    r = conv('<em><p>Note <a href="/go/1-20">N 1</a>.</p></em><p>Plain</p>')
    assert r.body == '<p><i>Note <a href="suvii:laws/1-20">N 1</a>.</i></p>\n<p>Plain</p>'


def test_inline_elements_are_kept(conv):
    r = conv('<p align="center"><strong>Bold</strong> and <u><s>old</s></u> H<sub>2</sub>O</p><div align=right><p>Right</p></div>')
    assert r.body == '<p class="suvii-center"><b>Bold</b> and <u><s>old</s></u> H<sub>2</sub>O</p>\n<p class="suvii-right">Right</p>'


def test_same_text_gives_same_bytes_whatever_the_nesting(conv):
    a = conv("<p><b><i>x</i></b><b><i> y</i></b></p>").body
    b = conv("<p><i><b>x y</b></i></p>").body
    c = conv("<p><strong><em>x</em><em> y</em></strong></p>").body
    assert a == b == c == "<p><b><i>x y</i></b></p>"


def test_headings_become_contents_and_bold(conv):
    # The way pages for open-data clients look: plain paragraphs, the anchor first.
    r = conv(
        '<p><a name="n1"></a>\nРозділ I\n<br> ЗАГАЛЬНІ ЗАСАДИ </p>'
        '<p><a name="n2"></a>\nГлава 2</p>'
        '<p><a name="n3"></a>\nСтаття 5 - 1. Text <a href="#n1">up</a>.</p>'
        '<p><a name="n4"></a>\n1. Part one.</p>'
    )
    assert r.toc == [
        TocEntry(1, "n1", "Розділ I ЗАГАЛЬНІ ЗАСАДИ"),
        TocEntry(2, "n2", "Глава 2"),
        TocEntry(3, "n3", "Стаття 5 - 1. Text up."),
    ]
    assert '<p id="n1" class="suvii-center"><b>Розділ I<br>ЗАГАЛЬНІ ЗАСАДИ</b></p>' in r.body
    assert '<p id="n3"><b>Стаття 5 - 1.</b> Text <a href="#n1">up</a>.</p>' in r.body
    assert '<p id="n4">1. Part one.</p>' in r.body


def test_levels_follow_what_the_document_has(conv):
    r = conv(
        '<p><a name="n1"></a>КНИГА ПЕРША<br>ЗАГАЛЬНІ ПОЛОЖЕННЯ</p><p><a name="n2"></a>Підрозділ 1<br>ОСОБИ</p>'
        '<p><a name="n3"></a>§ 1. Товариства</p><p><a name="n4"></a>Стаття 1. Text</p>'
        '<p><a name="n5"></a>ПРИКІНЦЕВІ ТА ПЕРЕХІДНІ ПОЛОЖЕННЯ</p>'
    )
    assert [(e.level, e.anchor) for e in r.toc] == [(1, "n1"), (3, "n2"), (4, "n3"), (5, "n4"), (2, "n5")]


@pytest.mark.parametrize(
    "text",
    [
        "Стаття 12 цього Закону застосовується з 1 січня.",  # no dot after the number: a sentence
        "Розділ II цього Кодексу застосовується до відносин, що виникли після набрання ним чинності.",
        "Глава 3 визначає порядок.",
        "«Стаття 5. Текст нової статті»",  # quoted text of an amending law
        "{Стаття 5 із змінами}",
    ],
)
def test_text_that_only_looks_like_a_heading(conv, text):
    r = conv(f'<p><a name="n1"></a>{text}</p>')
    assert r.toc == [] and "<b>" not in r.body


def test_headings_inside_tables_are_content(conv):
    r = conv("<table><tr><td>Стаття 1. A</td><td>B</td></tr></table>")
    assert r.toc == [] and "<b>" not in r.body


def test_editorial_note_is_marked(conv):
    r = conv('<p><a name="n7"></a>{Changed by <a href="/go/1-20">law</a>} </p><p>{Not a note</p>')
    assert r.body == '<p id="n7" class="suvii-note">{Changed by <a href="suvii:laws/1-20">law</a>}</p>\n<p>{Not a note</p>'
    assert r.toc == []


def test_image_placeholder_is_counted_not_shown(conv):
    r = conv('<p><a name="n1"></a>[ image ]</p><p>Text</p>')
    assert r.body == '<p id="n1">Text</p>' and r.report.images == 1


def test_long_contents_title_is_shortened(conv):
    r = conv(f'<p><a name="n1"></a>Стаття 1. {"слово " * 100}</p>')
    title = r.toc[0].title
    assert len(title) <= rules.TOC_TITLE_CHARS + 1 and title.endswith("слово…")


def test_empty_paragraph_is_dropped_but_its_anchor_lives(conv):
    r = conv('<p><a name="n1"></a><span><br></span></p><div><a name="n2"></a></div><p> \n </p><p><a name="n3"></a>Text <a href="#n1">up</a></p>')
    assert r.body == '<p id="n1"><span id="n2"></span><span id="n3"></span>Text <a href="#n1">up</a></p>'


def test_anchor_after_last_text_is_kept(conv):
    r = conv('<p>Text</p><p><a name="n9"></a></p>')
    assert r.body == '<p>Text</p>\n<p id="n9"></p>'


def test_anchor_in_the_middle_of_text(conv):
    r = conv('<p><a name="n1"></a>One <a name="n2"></a>two</p>')
    assert r.body == '<p id="n1">One <span id="n2"></span>two</p>'


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
        '<div><a name="n1"></a><table width="100%" border=0><tr valign=top><td width=809><p>[ image ]</p></td></tr>'
        "<tr valign=top><td><p> <br> </p></td></tr><tr><td><p> КОНСТИТУЦІЯ УКРАЇНИ </p></td></tr></table></div>"
    )
    assert r.body == '<p id="n1">КОНСТИТУЦІЯ УКРАЇНИ</p>'
    assert r.report.images == 1


def test_real_table_is_kept(conv):
    r = conv(
        '<table border="1" style="width:100%"><thead><tr><th colspan="2" onclick="x()">Head</th></tr></thead>'
        '<tr><td rowspan="0">1</td><td align="right"><b>2</b><p><b>3</b></p></td></tr>'
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
        '<p><span style="display: none">hidden</span>E &lt;b&gt; &amp;</p>'
    )
    assert r.body == "<p>A</p>\n<p>B C D</p>\n<p>E &lt;b&gt; &amp;</p>"
    assert r.report.dropped_links == 2 and r.report.images == 1


def test_link_to_this_document_and_to_another(conv):
    r = conv(
        '<p><a name="n5"></a><a href="/go/100-20#n5">here</a>, '
        '<a href="https://zakon.rada.gov.ua/laws/show/100-20#n99">gone</a>, '
        '<a href="/go/2222-15#n2" target="_blank">there</a>, <a href="/go/254%D0%BA/96-%D0%B2%D1%80">К</a></p>'
    )
    assert r.body == (
        '<p id="n5"><a href="#n5">here</a>, gone, <a href="suvii:laws/2222-15#n2">there</a>, '
        '<a href="suvii:laws/254к/96-вр">К</a></p>'
    )


def test_adjacent_links_to_one_place_stay_one_link(conv):
    r = conv('<p><a name="n5"></a><a href="#n5">статті 131</a><a href="#n5"> - 2</a> цієї Конституції</p>')
    assert r.body == '<p id="n5"><a href="#n5">статті 131 - 2</a> цієї Конституції</p>'


def test_report_names_new_markup(conv):
    r = conv("<p>A<blink>B</blink></p>")
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


