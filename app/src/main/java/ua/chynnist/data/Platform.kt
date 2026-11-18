package ua.chynnist.data

import androidx.sqlite.SQLiteConnection
import androidx.sqlite.SQLiteStatement
import androidx.sqlite.driver.bundled.BundledSQLiteDriver
import com.github.luben.zstd.Zstd
import com.github.luben.zstd.ZstdDecompressCtx
import io.github.marybezuhla.suvii.Decompressor
import io.github.marybezuhla.suvii.SqlDatabase
import io.github.marybezuhla.suvii.SqlRow
import java.io.File

/**
 * SQLite for the Suvii library: the SQLite that comes inside the app (androidx.sqlite, bundled), the same on
 * every phone and with full-text search, rather than whatever version the phone has.
 *
 * Opened read-only, a file can't be changed by anything the app runs. Suvii also asks for SQLite's defensive
 * mode (SPEC.md, 10); this driver has no way to switch it on. What it guards against (SQL that rewrites the
 * schema or the file's pages) needs SQL the app never runs: every statement is written in this code, and a
 * scroll's schema is checked before anything is read.
 *
 * One connection is used by one thread at a time (see [Library]).
 */
class BundledDatabase private constructor(private val connection: SQLiteConnection) : SqlDatabase, AutoCloseable {
    private fun <T> statement(sql: String, args: List<Any?>, use: (SQLiteStatement) -> T): T {
        val statement = connection.prepare(sql)
        try {
            args.forEachIndexed { i, value ->
                when (value) {
                    null -> statement.bindNull(i + 1)
                    is Long -> statement.bindLong(i + 1, value)
                    is Int -> statement.bindLong(i + 1, value.toLong())
                    is String -> statement.bindText(i + 1, value)
                    is ByteArray -> statement.bindBlob(i + 1, value)
                    else -> error("unsupported argument ${value::class}")
                }
            }
            return use(statement)
        } finally {
            statement.close()
        }
    }

    override fun query(sql: String, args: List<Any?>, row: (SqlRow) -> Unit) {
        statement(sql, args) { s ->
            val wrapped = Row(s)
            while (s.step()) row(wrapped)
        }
    }

    override fun execute(sql: String, args: List<Any?>) {
        statement(sql, args) { s -> while (s.step()) { /* rows, if any, are not wanted */ } }
    }

    override fun insert(sql: String, args: List<Any?>): Long {
        execute(sql, args)
        return statement("SELECT last_insert_rowid()", emptyList()) { s -> s.step(); s.getLong(0) }
    }

    override fun <T> transaction(block: () -> T): T {
        execute("BEGIN IMMEDIATE")
        try {
            return block().also { execute("COMMIT") }
        } catch (e: Throwable) {
            execute("ROLLBACK")
            throw e
        }
    }

    override fun close() = connection.close()

    private class Row(private val s: SQLiteStatement) : SqlRow {
        override fun isNull(column: Int): Boolean = s.isNull(column)

        override fun long(column: Int): Long = s.getLong(column)

        override fun string(column: Int): String = s.getText(column)

        override fun blob(column: Int): ByteArray = s.getBlob(column)
    }

    companion object {
        private const val OPEN_READONLY = 0x00000001

        /** Opens [file] read-only: a scroll on the phone is only ever read (updates come as a new file). */
        fun openReadOnly(file: File): BundledDatabase = BundledDatabase(BundledSQLiteDriver().open(file.absolutePath, OPEN_READONLY))
    }
}

/** zstd for the Suvii library (zstd-jni): a frame is unpacked only if its size is stated and within the limit. */
object JniZstd : Decompressor {
    override fun decompress(data: ByteArray, maxSize: Int, dictionary: ByteArray?): ByteArray {
        val size = Zstd.getFrameContentSize(data)
        require(size in 0..maxSize.toLong()) { "bad or unknown content size" }
        ZstdDecompressCtx().use { ctx ->
            if (dictionary != null) ctx.loadDict(dictionary)
            val out = ctx.decompress(data, size.toInt())
            require(out.size.toLong() == size) { "short frame" }
            return out
        }
    }
}
