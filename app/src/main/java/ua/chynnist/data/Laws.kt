package ua.chynnist.data

import io.github.marybezuhla.suvii.SqlDatabase
import io.github.marybezuhla.suvii.all
import io.github.marybezuhla.suvii.first
import java.text.CollationKey
import java.text.Collator
import java.util.Locale

/** How the list of documents is narrowed and ordered. */
data class Filter(
    /** Only documents in force (fully or in part). */
    val activeOnly: Boolean = true,
    /** Kinds by the portal's code ("1" is a law, "21" a code); empty means every kind. */
    val kinds: Set<String> = DEFAULT_KINDS,
    val order: Order = Order.TITLE,
) {
    companion object {
        /** Laws and codes: what most people come for. */
        val DEFAULT_KINDS = setOf("1", "21")
    }
}

enum class Order { TITLE, NEWEST }

/** A document as the list shows it: no text is read for this. */
data class DocRow(val path: String, val title: String, val number: String?, val status: String?, val edition: String?)

/**
 * The questions the app asks of the laws on the phone, in SQL. Field names and values are Chynnist's own
 * (see tools/collect: rules.collection_fields), so they are written here as they are.
 */
object Laws {
    /** States in which a document, or some of it, is in force. */
    val ACTIVE = listOf("in_force", "restored", "partly_in_force", "repealed_except")

    private fun placeholders(n: Int) = List(n) { "?" }.joinToString(",")

    private fun where(filter: Filter): Pair<String, List<Any?>> {
        val conditions = mutableListOf<String>()
        val args = mutableListOf<Any?>()
        if (filter.activeOnly) {
            conditions += "EXISTS (SELECT 1 FROM facets f WHERE f.doc_id = d.id AND f.key = 'status' AND f.value IN (${placeholders(ACTIVE.size)}))"
            args.addAll(ACTIVE)
        }
        if (filter.kinds.isNotEmpty()) {
            val kinds = filter.kinds.sorted()
            conditions += "EXISTS (SELECT 1 FROM facets f WHERE f.doc_id = d.id AND f.key = 'kind' AND f.value IN (${placeholders(kinds.size)}))"
            args.addAll(kinds)
        }
        return (if (conditions.isEmpty()) "" else "WHERE " + conditions.joinToString(" AND ")) to args
    }

    private fun facet(key: String) = "(SELECT f.value FROM facets f WHERE f.doc_id = d.id AND f.key = '$key' LIMIT 1)"

    /** Lists up to this long are put in the order of the Ukrainian alphabet; longer ones are left in SQLite's order. */
    private const val COLLATED = 60_000

    /** Every document that passes [filter], in its order: only numbers, so even the whole collection is small. */
    fun ids(db: SqlDatabase, filter: Filter): LongArray {
        val (where, args) = where(filter)
        if (filter.order == Order.NEWEST) {
            val out = ArrayList<Long>()
            db.query("SELECT d.id FROM docs d $where ORDER BY ${facet("edition")} DESC NULLS LAST, d.title, d.path", args) { out += it.long(0) }
            return out.toLongArray()
        }
        // SQLite compares the bytes of the text, which puts capitals first and ґ, є, і, ї after я. A list of
        // usual length is sorted here by the rules of Ukrainian instead (by the start of each title: enough to
        // tell them apart, and little memory). The whole collection at once keeps SQLite's order.
        val count = db.first("SELECT count(*) FROM docs d $where", args) { it.long(0) } ?: 0
        if (count > COLLATED) {
            val out = ArrayList<Long>()
            db.query("SELECT d.id FROM docs d $where ORDER BY d.title, d.path", args) { out += it.long(0) }
            return out.toLongArray()
        }
        val collator = Collator.getInstance(Locale.forLanguageTag("uk"))
        val keyed = ArrayList<Pair<Long, CollationKey>>(count.toInt())
        db.query("SELECT d.id, substr(d.title, 1, 80) FROM docs d $where ORDER BY d.path", args) {
            keyed += it.long(0) to collator.getCollationKey(it.string(1))
        }
        // (a stable sort: equal starts stay in the order of their paths)
        keyed.sortWith { a, b -> a.second.compareTo(b.second) }
        return LongArray(keyed.size) { keyed[it].first }
    }

    /** The rows for [ids], in the same order. */
    fun rows(db: SqlDatabase, ids: LongArray): List<DocRow> {
        if (ids.isEmpty()) return emptyList()
        val found = HashMap<Long, DocRow>()
        db.query(
            "SELECT d.id, d.path, d.title, ${facet("number")}, ${facet("status")}, ${facet("edition")} FROM docs d " +
                "WHERE d.id IN (${placeholders(ids.size)})",
            ids.toList(),
        ) {
            found[it.long(0)] = DocRow(it.string(1), it.string(2), it.text(3), it.text(4), it.text(5))
        }
        return buildList { for (id in ids) found[id]?.let(::add) }
    }

    /** The kinds of documents there are (with [activeOnly], among those in force), most common first. */
    fun kinds(db: SqlDatabase, activeOnly: Boolean): List<Pair<String, Long>> {
        val (where, args) = where(Filter(activeOnly = activeOnly, kinds = emptySet()))
        return db.all(
            "SELECT k.value, count(*) FROM docs d JOIN facets k ON k.doc_id = d.id AND k.key = 'kind' $where " +
                "GROUP BY k.value ORDER BY count(*) DESC, k.value",
            args,
        ) { it.string(0) to it.long(1) }
    }

    /** True if the document at [path] is on the phone. */
    fun has(db: SqlDatabase, path: String): Boolean = db.first("SELECT 1 FROM docs WHERE path = ? LIMIT 1", listOf(path)) { true } ?: false

    private fun io.github.marybezuhla.suvii.SqlRow.text(column: Int): String? = if (isNull(column)) null else string(column)
}
