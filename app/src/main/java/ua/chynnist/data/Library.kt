package ua.chynnist.data

import android.content.Context
import android.content.pm.ApplicationInfo
import android.net.Uri
import io.github.marybezuhla.suvii.Document
import io.github.marybezuhla.suvii.Field
import io.github.marybezuhla.suvii.Scroll
import io.github.marybezuhla.suvii.SuviiException
import io.github.marybezuhla.suvii.first
import kotlinx.coroutines.asCoroutineDispatcher
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException
import java.util.concurrent.Executors

/**
 * The laws on this phone: one signed Suvii file, opened read-only. Every read goes through one thread, so
 * the one SQLite connection is never used by two at once.
 */
object Library {
    /** Chynnist's collection: the same id in every base and update, forever (tools/collect: rules.COLLECTION_ID). */
    const val COLLECTION_ID = "8e3b6c1a-5d2f-4b7e-9a41-2c6f0d8e7b53"

    /**
     * The publisher's data keys (ed25519, base64). The app trusts a file only if one of these signed it. Empty
     * until the key is made on the publisher's Mac (`chynnist-collect keygen` prints the line to put here).
     */
    val TRUSTED_KEYS: List<String> = emptyList()

    /** The largest file the app takes: well above the whole collection, well below what would fill a phone. */
    private const val MAX_FILE = 8L shl 30

    /** What the app knows about the laws on the phone. */
    data class Info(
        val title: String,
        val seq: Long,
        val sourceDate: String,
        val count: Long,
        /** Signed by its own key, not the publisher's: a test file, opened only by a debug build. */
        val test: Boolean,
        val fields: Map<String, Field>,
    )

    sealed interface State {
        data object Loading : State

        data object Empty : State

        data class Ready(val info: Info) : State

        /** The file on the phone could not be opened; the reason is for the screen. */
        data class Broken(val problem: Problem) : State
    }

    /** Why a file was not taken, in words the screen can show. */
    enum class Problem { NOT_LAWS, UNTRUSTED, OTHER_COLLECTION, UPDATE_ONLY, TOO_BIG, NO_SPACE, DAMAGED }

    class Refused(val problem: Problem) : Exception(problem.name)

    private val thread = Executors.newSingleThreadExecutor { Thread(it, "library") }.asCoroutineDispatcher()
    private val _state = MutableStateFlow<State>(State.Loading)
    val state: StateFlow<State> = _state

    private var scroll: Scroll? = null
    private var db: BundledDatabase? = null

    private fun file(context: Context) = File(context.noBackupFilesDir, "laws.suvii")

    private fun incoming(context: Context) = File(context.noBackupFilesDir, "incoming.suvii")

    private fun debuggable(context: Context) = context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE != 0

    /** Opens the laws already on the phone, if any. Called once when the app starts. */
    suspend fun load(context: Context) = withContext(thread) {
        if (scroll != null) return@withContext
        val app = context.applicationContext
        incoming(app).delete() // left over from an install that was cut short
        val file = file(app)
        _state.value = if (!file.exists()) {
            State.Empty
        } else {
            try {
                State.Ready(openFile(app, file))
            } catch (e: Refused) {
                State.Broken(e.problem)
            }
        }
    }

    /**
     * Takes a Suvii file the person chose: copies it in, checks it completely (format, limits, signature,
     * collection) and only then puts it in place of the laws on the phone. Throws [Refused].
     */
    suspend fun install(context: Context, uri: Uri): Info = withContext(thread) {
        val app = context.applicationContext
        val temp = incoming(app)
        try {
            copy(app, uri, temp)
            // Checked on its own first: the laws on the phone stay as they are if this file is refused
            checked(app, temp).let { it.db.close(); if (it.scroll.kind != "base") throw Refused(Problem.UPDATE_ONLY) }
            closeCurrent()
            if (!temp.renameTo(file(app))) throw Refused(Problem.NO_SPACE)
            openFile(app, file(app)).also { _state.value = State.Ready(it) }
        } catch (e: Refused) {
            // Refused before the laws on the phone were touched: they stay as they were
            if (scroll == null && _state.value is State.Ready) _state.value = State.Broken(e.problem)
            throw e
        } finally {
            temp.delete()
        }
    }

    private fun copy(context: Context, uri: Uri, to: File) {
        val input = try {
            context.contentResolver.openInputStream(uri)
        } catch (e: Exception) {
            null
        } ?: throw Refused(Problem.DAMAGED)
        try {
            input.use { from ->
                // The first bytes say whether this is a scroll at all, before anything big is copied
                val header = ByteArray(100)
                var got = 0
                while (got < header.size) {
                    val n = from.read(header, got, header.size - got)
                    if (n < 0) break
                    got += n
                }
                try {
                    Scroll.checkHeader(header.copyOf(got))
                } catch (e: SuviiException) {
                    throw Refused(Problem.NOT_LAWS)
                }
                to.outputStream().use { out ->
                    out.write(header, 0, got)
                    val buffer = ByteArray(1 shl 16)
                    var total = got.toLong()
                    while (true) {
                        val n = from.read(buffer)
                        if (n < 0) break
                        total += n
                        if (total > MAX_FILE) throw Refused(Problem.TOO_BIG)
                        out.write(buffer, 0, n)
                    }
                }
            }
        } catch (e: IOException) {
            // Most often the phone is full; otherwise the file could not be read to the end
            throw Refused(if (to.parentFile?.usableSpace?.let { it < (1L shl 20) } == true) Problem.NO_SPACE else Problem.DAMAGED)
        }
    }

    private class Opened(val scroll: Scroll, val db: BundledDatabase, val test: Boolean)

    /** Opens [file] with every check; the caller closes the database. Throws [Refused]. */
    private fun checked(context: Context, file: File): Opened {
        val header = try {
            file.inputStream().use { input -> ByteArray(100).also { if (input.read(it) != 100) throw Refused(Problem.NOT_LAWS) } }
        } catch (e: IOException) {
            throw Refused(Problem.DAMAGED)
        }
        val db = try {
            BundledDatabase.openReadOnly(file)
        } catch (e: Exception) {
            throw Refused(Problem.DAMAGED)
        }
        try {
            val (scroll, test) = try {
                Scroll.open(header, db, JniZstd, TRUSTED_KEYS) to false
            } catch (e: SuviiException) {
                // A debug build also opens test files, signed by a key made for that one build
                if (e.code !in setOf("bad_signature", "no_trusted_key") || !debuggable(context)) throw e
                val own = db.first("SELECT value FROM meta WHERE key = 'sign.key'") { it.string(0) } ?: throw e
                Scroll.open(header, db, JniZstd, listOf(own)) to true
            }
            if (scroll.collectionId != COLLECTION_ID) throw Refused(Problem.OTHER_COLLECTION)
            return Opened(scroll, db, test)
        } catch (e: Throwable) {
            db.close()
            throw when (e) {
                is Refused -> e
                is SuviiException -> Refused(
                    when (e.code) {
                        "not_sqlite", "not_suvii", "unsupported_version" -> Problem.NOT_LAWS
                        "bad_signature", "no_trusted_key" -> Problem.UNTRUSTED
                        else -> Problem.DAMAGED
                    },
                )
                else -> Refused(Problem.DAMAGED)
            }
        }
    }

    private fun openFile(context: Context, file: File): Info {
        val opened = checked(context, file)
        scroll = opened.scroll
        db = opened.db
        val s = opened.scroll
        return Info(
            title = s.meta["collection.title"].orEmpty(),
            seq = s.seq,
            sourceDate = s.meta["state.source_date"].orEmpty(),
            count = s.count(),
            test = opened.test,
            fields = s.fields,
        )
    }

    private fun closeCurrent() {
        db?.close()
        db = null
        scroll = null
    }

    /** Runs [block] on the library's thread with the open scroll. Throws [IllegalStateException] if there is none. */
    suspend fun <T> read(block: (Scroll) -> T): T = withContext(thread) { block(checkNotNull(scroll) { "no laws" }) }

    /** The document at [path], checked against its hash and the safe HTML subset; null if it is not here. */
    suspend fun document(path: String): Document? = read { s ->
        try {
            s.document(path)
        } catch (e: SuviiException) {
            if (e.code == "not_found") null else throw e
        }
    }
}
