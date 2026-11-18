package ua.chynnist.data

import io.github.marybezuhla.suvii.SqlDatabase
import io.github.marybezuhla.suvii.SqlRow
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.sql.Connection
import java.sql.DriverManager

/** The list's questions, asked of a small made-up collection in SQLite (sqlite-jdbc, on the computer). */
class LawsTest {
    private lateinit var connection: Connection
    private lateinit var db: SqlDatabase

    @Before fun setUp() {
        connection = DriverManager.getConnection("jdbc:sqlite::memory:")
        db = Jdbc(connection)
        db.execute("CREATE TABLE docs (id INTEGER PRIMARY KEY, path TEXT NOT NULL, title TEXT NOT NULL)")
        db.execute("CREATE TABLE facets (doc_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY (doc_id, key, value))")
        fun doc(id: Long, title: String, status: String, edition: String?, vararg kinds: String) {
            db.execute("INSERT INTO docs VALUES (?, ?, ?)", listOf(id, "laws/$id", title))
            db.execute("INSERT INTO facets VALUES (?, 'number', ?)", listOf(id, "$id-IX"))
            db.execute("INSERT INTO facets VALUES (?, 'status', ?)", listOf(id, status))
            if (edition != null) db.execute("INSERT INTO facets VALUES (?, 'edition', ?)", listOf(id, edition))
            for (k in kinds) db.execute("INSERT INTO facets VALUES (?, 'kind', ?)", listOf(id, k))
        }
        doc(1, "Ялтинська угода", "in_force", "2020-01-01", "17")
        doc(2, "Інструкція про порядок", "in_force", null, "10")
        doc(3, "Кодекс України про працю", "in_force", "2026-08-05", "1", "21")
        doc(4, "Кодекс адміністративного судочинства", "partly_in_force", "2025-01-01", "1", "21")
        doc(5, "Закон про давнє", "repealed", "2001-01-01", "1")
        doc(6, "Ґрунтовий закон", "in_force", "2024-01-01", "1")
    }

    @After fun tearDown() = connection.close()

    private fun titles(filter: Filter) = Laws.rows(db, Laws.ids(db, filter)).map { it.title }

    @Test fun inTheOrderOfTheUkrainianAlphabet() {
        assertEquals(
            listOf("Ґрунтовий закон", "Закон про давнє", "Інструкція про порядок", "Кодекс адміністративного судочинства", "Кодекс України про працю", "Ялтинська угода"),
            titles(Filter(activeOnly = false, kinds = emptySet())),
        )
    }

    @Test fun onlyInForce() {
        assertFalse("Закон про давнє" in titles(Filter(activeOnly = true, kinds = emptySet())))
        assertTrue("Кодекс адміністративного судочинства" in titles(Filter(activeOnly = true, kinds = emptySet())))
    }

    @Test fun byKind() {
        assertEquals(listOf("Кодекс адміністративного судочинства", "Кодекс України про працю"), titles(Filter(activeOnly = true, kinds = setOf("21"))))
        assertEquals(listOf("Ґрунтовий закон", "Кодекс адміністративного судочинства", "Кодекс України про працю"), titles(Filter()))
    }

    @Test fun newestEditionsFirst() {
        assertEquals(
            listOf("Кодекс України про працю", "Кодекс адміністративного судочинства", "Ґрунтовий закон", "Ялтинська угода", "Інструкція про порядок"),
            titles(Filter(activeOnly = true, kinds = emptySet(), order = Order.NEWEST)),
        )
    }

    @Test fun rowsHaveTheirDetails() {
        val row = Laws.rows(db, longArrayOf(3)).single()
        assertEquals(DocRow("laws/3", "Кодекс України про працю", "3-IX", "in_force", "2026-08-05"), row)
    }

    @Test fun kindsWithCounts() {
        assertEquals(listOf("1" to 3L, "21" to 2L, "10" to 1L, "17" to 1L), Laws.kinds(db, activeOnly = true))
    }

    @Test fun whetherADocumentIsHere() {
        assertTrue(Laws.has(db, "laws/3"))
        assertFalse(Laws.has(db, "laws/99"))
    }

    /** Just enough of SqlDatabase over JDBC for these tests. */
    private class Jdbc(private val c: Connection) : SqlDatabase {
        private fun prepare(sql: String, args: List<Any?>) = c.prepareStatement(sql).apply {
            args.forEachIndexed { i, v ->
                when (v) {
                    is Long -> setLong(i + 1, v)
                    is Int -> setLong(i + 1, v.toLong())
                    is String -> setString(i + 1, v)
                    null -> setNull(i + 1, java.sql.Types.NULL)
                    else -> error("unsupported $v")
                }
            }
        }

        override fun query(sql: String, args: List<Any?>, row: (SqlRow) -> Unit) {
            prepare(sql, args).use { s ->
                s.executeQuery().use { rs ->
                    val r = object : SqlRow {
                        override fun isNull(column: Int) = rs.getObject(column + 1) == null
                        override fun long(column: Int) = rs.getLong(column + 1)
                        override fun string(column: Int): String = rs.getString(column + 1)
                        override fun blob(column: Int): ByteArray = rs.getBytes(column + 1)
                    }
                    while (rs.next()) row(r)
                }
            }
        }

        override fun execute(sql: String, args: List<Any?>) {
            prepare(sql, args).use { it.execute() }
        }

        override fun insert(sql: String, args: List<Any?>): Long = error("not needed")

        override fun <T> transaction(block: () -> T): T = block()
    }
}
