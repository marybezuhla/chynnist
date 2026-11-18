package ua.chynnist.text

import io.github.marybezuhla.suvii.SafeHtml
import io.github.marybezuhla.suvii.SafeHtml.Token

/** Inline looks of the safe HTML subset. */
enum class Mark { BOLD, ITALIC, UNDERLINE, STRIKE, SUP, SUB, SMALL, CODE }

enum class Align { START, CENTER, END }

/** A span of a paragraph's text, from [start] (inclusive) to [end] (exclusive). */
data class Marked(val mark: Mark, val start: Int, val end: Int)

data class Linked(val href: String, val start: Int, val end: Int)

/**
 * One paragraph, ready to draw: plain text with its looks and links, the anchors that lead to it, and how it
 * stands on the page. [heading] is the level of an h1-h6 (0 for a plain paragraph).
 */
data class Para(
    val text: String,
    val marks: List<Marked> = emptyList(),
    val links: List<Linked> = emptyList(),
    val anchors: List<String> = emptyList(),
    val note: Boolean = false,
    val align: Align = Align.START,
    val heading: Int = 0,
    val pre: Boolean = false,
)

data class Cell(val paras: List<Para>, val header: Boolean, val colspan: Int)

sealed interface Block {
    /** Every anchor in the block: a link to any of them leads here. */
    val anchors: List<String>

    data class Text(val para: Para) : Block {
        override val anchors get() = para.anchors
    }

    data class Table(val rows: List<List<Cell>>, override val anchors: List<String>) : Block

    data class Rule(override val anchors: List<String>) : Block
}

/**
 * A document body in the safe HTML subset (already checked by the Suvii library) as a list of blocks. Nothing
 * here runs the HTML: it is read token by token, and what isn't understood is kept as plain text.
 */
object Body {
    private val INLINE = mapOf(
        "b" to Mark.BOLD, "strong" to Mark.BOLD, "i" to Mark.ITALIC, "em" to Mark.ITALIC, "u" to Mark.UNDERLINE,
        "s" to Mark.STRIKE, "sup" to Mark.SUP, "sub" to Mark.SUB, "small" to Mark.SMALL, "code" to Mark.CODE,
    )
    private val PARAGRAPHS = setOf("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "li", "dt", "dd", "caption")
    private val WHITESPACE = Regex("[ \t\r\n\u000C]+")

    fun parse(html: String): List<Block> = Parser().run(SafeHtml.tokens(html))

    private class Open(val tag: String, val mark: Mark?, val href: String?, var start: Int)

    private class BlockTag(val tag: String, val classes: Set<String>, var number: Int = 0)

    private class Parser {
        val out = mutableListOf<Block>()
        val blocks = ArrayDeque<BlockTag>()
        val inline = mutableListOf<Open>()

        // The paragraph being written
        val text = StringBuilder()
        val marks = mutableListOf<Marked>()
        val links = mutableListOf<Linked>()
        val anchors = mutableListOf<String>()

        // A table being read: its rows, the cell being filled, and anchors given to the table itself
        var rows: MutableList<MutableList<Cell>>? = null
        var cell: MutableList<Para>? = null
        var cellHeader = false
        var cellSpan = 1
        val tableAnchors = mutableListOf<String>()
        var tableDepth = 0

        fun run(tokens: List<Token>): List<Block> {
            for (token in tokens) {
                when (token) {
                    is Token.Text -> text(token.text)
                    is Token.Start -> start(token.tag, token.attrs.toMap())
                    is Token.End -> end(token.tag)
                }
            }
            flush()
            finishTable()
            return out
        }

        fun inPre() = blocks.any { it.tag == "pre" }

        fun text(raw: String) {
            if (inPre()) {
                text.append(raw)
                return
            }
            val collapsed = WHITESPACE.replace(raw, " ")
            for (c in collapsed) {
                // No space at the start of a paragraph or twice in a row
                if (c == ' ' && (text.isEmpty() || text.last() == ' ' || text.last() == '\n')) continue
                text.append(c)
            }
        }

        fun start(tag: String, attrs: Map<String, String>) {
            val id = attrs["id"]
            when {
                tag in INLINE || tag == "a" || tag == "span" -> {
                    inline += Open(tag, INLINE[tag], if (tag == "a") attrs["href"] else null, text.length)
                    if (id != null) anchors += id
                }
                tag == "br" -> {
                    if (text.isNotEmpty() && text.last() == ' ') text.setLength(text.length - 1)
                    text.append('\n')
                    if (id != null) anchors += id
                }
                tag == "hr" -> {
                    flush()
                    if (tableDepth == 0) out += Block.Rule(listOfNotNull(id))
                }
                tag == "table" -> {
                    flush()
                    tableDepth++
                    if (tableDepth == 1) {
                        rows = mutableListOf()
                        tableAnchors.clear()
                    }
                    if (id != null) tableAnchors += id
                }
                tag == "tr" && tableDepth == 1 -> {
                    flush()
                    rows?.add(mutableListOf())
                    if (id != null) tableAnchors += id
                }
                (tag == "td" || tag == "th") && tableDepth == 1 -> {
                    flush()
                    finishCell()
                    if (rows?.isEmpty() == true) rows?.add(mutableListOf())
                    cell = mutableListOf()
                    cellHeader = tag == "th"
                    cellSpan = attrs["colspan"]?.toIntOrNull()?.coerceIn(1, 64) ?: 1
                    if (id != null) anchors += id
                }
                else -> {
                    // A block: whatever was written before it is a paragraph of its own
                    flush()
                    val classes = attrs["class"]?.split(' ')?.filter { it.isNotEmpty() }?.toSet() ?: emptySet()
                    val parent = blocks.lastOrNull()
                    blocks.addLast(BlockTag(tag, classes))
                    if (tag == "li") {
                        val list = blocks.lastOrNull { it.tag == "ol" || it.tag == "ul" }
                        if (list?.tag == "ol") {
                            list.number++
                            text.append("${list.number}. ")
                        } else {
                            text.append("• ")
                        }
                    }
                    if (parent != null && tag == "dd") text.append("    ")
                    if (id != null) anchors += id
                }
            }
        }

        fun end(tag: String) {
            when {
                tag in INLINE || tag == "a" || tag == "span" -> {
                    val at = inline.indexOfLast { it.tag == tag }
                    if (at >= 0) {
                        val open = inline.removeAt(at)
                        close(open, text.length)
                    }
                }
                tag == "table" -> {
                    flush()
                    if (tableDepth == 1) finishTable()
                    tableDepth = maxOf(0, tableDepth - 1)
                }
                tag == "td" || tag == "th" -> if (tableDepth == 1) {
                    flush()
                    finishCell()
                }
                tag == "tr" -> if (tableDepth == 1) flush()
                tag == "br" || tag == "hr" -> Unit
                else -> {
                    flush()
                    val at = blocks.indexOfLast { it.tag == tag }
                    if (at >= 0) while (blocks.size > at) blocks.removeLast()
                }
            }
        }

        fun close(open: Open, end: Int) {
            if (end <= open.start) return
            open.mark?.let { marks += Marked(it, open.start, end) }
            open.href?.let { links += Linked(it, open.start, end) }
        }

        /** Ends the paragraph being written; what is still open goes on in the next one. */
        fun flush() {
            while (text.isNotEmpty() && (text.last() == ' ' || text.last() == '\n')) text.setLength(text.length - 1)
            val length = text.length
            for (open in inline) close(open, length)
            if (length > 0) {
                val para = Para(
                    text = text.toString(),
                    marks = marks.map { it.copy(end = minOf(it.end, length)) }.filter { it.start < it.end },
                    links = links.map { it.copy(end = minOf(it.end, length)) }.filter { it.start < it.end },
                    anchors = anchors.toList(),
                    note = blocks.any { "suvii-note" in it.classes },
                    align = blocks.lastOrNull { "suvii-center" in it.classes || "suvii-right" in it.classes }
                        ?.let { if ("suvii-center" in it.classes) Align.CENTER else Align.END } ?: Align.START,
                    heading = blocks.lastOrNull { it.tag.length == 2 && it.tag[0] == 'h' }?.tag?.get(1)?.digitToInt() ?: 0,
                    pre = inPre(),
                )
                val inCell = cell
                when {
                    inCell != null -> inCell += para
                    rows != null -> rows?.lastOrNull()?.add(Cell(listOf(para), header = false, colspan = 1))
                        ?: out.add(Block.Text(para))
                    else -> out += Block.Text(para)
                }
                // (with no text, the anchors stay for the next paragraph: they lead to whatever comes next)
                anchors.clear()
            }
            text.clear()
            marks.clear()
            links.clear()
            for (open in inline) open.start = 0
        }

        fun finishCell() {
            val paras = cell ?: return
            if (anchors.isNotEmpty() && paras.isEmpty()) tableAnchors += anchors.also { anchors.clear() }
            rows?.lastOrNull()?.add(Cell(paras.toList(), cellHeader, cellSpan))
            cell = null
        }

        fun finishTable() {
            finishCell()
            val found = rows ?: return
            rows = null
            val kept = found.filter { it.isNotEmpty() }
            if (kept.isNotEmpty()) {
                // Anchors inside the cells lead to the table as a whole
                val inside = kept.flatMap { row -> row.flatMap { c -> c.paras.flatMap { it.anchors } } }
                out += Block.Table(kept, tableAnchors.toList() + inside)
            }
            tableAnchors.clear()
        }
    }
}
