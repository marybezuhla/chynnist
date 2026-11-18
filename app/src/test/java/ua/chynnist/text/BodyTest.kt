package ua.chynnist.text

import io.github.marybezuhla.suvii.TocEntry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** The document body as the collector writes it (tools/collect: render.py), read into blocks. */
class BodyTest {
    private fun para(block: Block) = (block as Block.Text).para

    @Test fun paragraphWithLooksAndLinks() {
        val blocks = Body.parse(
            "<p id=\"n12\"><b>Стаття 1.</b> Україна є <a href=\"suvii:laws/254к/96-вр#n5\">суверенна</a> держава.</p>\n" +
                "<p>Стаття 149<sup>-1</sup></p>",
        )
        assertEquals(2, blocks.size)
        val first = para(blocks[0])
        assertEquals("Стаття 1. Україна є суверенна держава.", first.text)
        assertEquals(listOf("n12"), first.anchors)
        assertEquals(listOf(Marked(Mark.BOLD, 0, 9)), first.marks)
        assertEquals(listOf(Linked("suvii:laws/254к/96-вр#n5", 20, 29)), first.links)
        assertEquals(listOf(Marked(Mark.SUP, 10, 12)), para(blocks[1]).marks)
    }

    @Test fun spacesAndLineBreaks() {
        val p = para(Body.parse("<p>  один \n  два<br>\n три  </p>").single())
        assertEquals("один два\nтри", p.text)
    }

    @Test fun notesAndAlignment() {
        val blocks = Body.parse("<p class=\"suvii-note\">{Із змінами}</p><p class=\"suvii-center\">Розділ I</p><p class=\"suvii-right\">Президент</p>")
        assertTrue(para(blocks[0]).note)
        assertEquals(Align.CENTER, para(blocks[1]).align)
        assertEquals(Align.END, para(blocks[2]).align)
    }

    @Test fun anchorWithoutTextLeadsToTheNextParagraph() {
        val blocks = Body.parse("<p><span id=\"n7\"></span></p><p id=\"n8\">Текст</p>")
        assertEquals(listOf("n7", "n8"), para(blocks.single()).anchors)
    }

    @Test fun tables() {
        val blocks = Body.parse(
            "<p>Перед</p>\n<table>\n<tr>\n<th colspan=\"2\"><p id=\"n3\">Заголовок</p></th>\n</tr>\n<tr>\n<td><p>а</p></td>\n<td><p>б</p><p>в</p></td>\n</tr>\n</table>\n<p>Після</p>",
        )
        assertEquals(3, blocks.size)
        val table = blocks[1] as Block.Table
        assertEquals(2, table.rows.size)
        assertEquals(2, table.rows[0][0].colspan)
        assertTrue(table.rows[0][0].header)
        assertEquals(listOf("б", "в"), table.rows[1][1].paras.map { it.text })
        assertEquals(listOf("n3"), table.anchors)
        assertEquals("Після", para(blocks[2]).text)
    }

    @Test fun lists() {
        val blocks = Body.parse("<ol><li>перше</li><li>друге</li></ol><ul><li>пункт</li></ul>")
        assertEquals(listOf("1. перше", "2. друге", "• пункт"), blocks.map { para(it).text })
    }

    @Test fun lookAcrossALineBreakStaysOne() {
        val p = para(Body.parse("<p><i>курсив<br>далі</i> кінець</p>").single())
        assertEquals(listOf(Marked(Mark.ITALIC, 0, 11)), p.marks)
    }

    @Test fun placeInTheText() {
        val blocks = Body.parse("<p id=\"a\">Розділ I</p><p id=\"b\">Стаття 1. Перша.</p><p>текст</p><p id=\"c\">Стаття 2. Друга.</p>")
        val reading = Reading(
            "laws/1", "Закон", null, null, null, blocks,
            listOf(TocEntry(1, "a", "Розділ I"), TocEntry(2, "b", "Стаття 1. Перша."), TocEntry(2, "c", "Стаття 2. Друга."), TocEntry(2, "x", "Немає")),
        )
        assertEquals(3, reading.toc.size) // an entry that leads nowhere is left out
        assertEquals(2, reading.finest)
        assertEquals(mapOf(0 to 1, 1 to 2, 3 to 2), reading.entryLevel)
        assertEquals(null, reading.place(0))
        val place = reading.place(2)!!
        assertEquals("Стаття 1", place.short)
        assertEquals(1, place.number)
        assertEquals(2, place.of)
        assertEquals("Стаття 2", reading.place(3)!!.short)
    }
}
