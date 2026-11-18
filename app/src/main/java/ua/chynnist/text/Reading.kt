package ua.chynnist.text

import io.github.marybezuhla.suvii.Document
import io.github.marybezuhla.suvii.TocEntry

/**
 * A document ready to read: its blocks, its contents, and where each entry of the contents is. Built once
 * per opening, away from the screen's thread.
 */
class Reading(
    val path: String,
    val title: String,
    val number: String?,
    val status: String?,
    /** The date of the edition (yyyy-mm-dd), if the portal gives one. */
    val edition: String?,
    val blocks: List<Block>,
    toc: List<TocEntry>,
) {
    /** The block each anchor leads to. */
    val anchorBlock: Map<String, Int> = buildMap {
        blocks.forEachIndexed { i, block -> for (a in block.anchors) putIfAbsent(a, i) }
    }

    /** Entries of the contents that lead somewhere in this text, in order. */
    val toc: List<TocEntry> = toc.filter { it.anchor in anchorBlock }

    /** The level of the finest entries (articles, as a rule): these are what the place in the text is told by. */
    val finest: Int = this.toc.maxOfOrNull { it.level } ?: 0

    /** Blocks that start an entry of the contents, with its level. */
    val entryLevel: Map<Int, Int> = buildMap { for (e in this@Reading.toc) putIfAbsent(anchorBlock.getValue(e.anchor), e.level) }

    private val finestEntries = this.toc.filter { it.level == finest }
    private val finestBlocks = finestEntries.map { anchorBlock.getValue(it.anchor) }

    /** The entry of the contents [block] is in (the last one that starts at or before it), and its place among the finest. */
    fun place(block: Int): Place? {
        if (finestBlocks.isEmpty()) return null
        var lo = 0
        var hi = finestBlocks.size - 1
        var found = -1
        while (lo <= hi) {
            val mid = (lo + hi) / 2
            if (finestBlocks[mid] <= block) {
                found = mid
                lo = mid + 1
            } else {
                hi = mid - 1
            }
        }
        if (found < 0) return null
        return Place(finestEntries[found], found + 1, finestEntries.size)
    }

    data class Place(val entry: TocEntry, val number: Int, val of: Int) {
        /** "Стаття 3" from "Стаття 3. Людина, її життя…": the name up to the first full stop, if it is short. */
        val short: String get() = shortName(entry.title)
    }

    companion object {
        fun from(doc: Document): Reading {
            fun facet(key: String) = doc.facets.firstOrNull { it.first == key }?.second
            return Reading(
                path = doc.path,
                title = doc.title,
                number = facet("number"),
                status = facet("status"),
                edition = facet("edition"),
                blocks = if (doc.mime == "text/html") Body.parse(doc.body) else plain(doc.body),
                toc = doc.toc,
            )
        }

        private fun plain(body: String): List<Block> =
            body.split(Regex("\n\\s*\n")).map { it.trim() }.filter { it.isNotEmpty() }.map { Block.Text(Para(it)) }

        /** The name of an entry up to its first full stop ("Стаття 3"), or the whole title if that is not short. */
        fun shortName(title: String): String {
            val stop = title.indexOf(". ")
            val head = if (stop in 1..40) title.substring(0, stop) else title
            return if (head.length <= 60) head else head.take(59).trimEnd() + "…"
        }
    }
}
