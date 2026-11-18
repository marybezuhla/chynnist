package ua.chynnist.ui

import android.content.ActivityNotFoundException
import android.content.Context
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.annotation.DrawableRes
import androidx.annotation.StringRes
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.saveable.rememberSaveableStateHolder
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import ua.chynnist.R
import ua.chynnist.data.Filter
import ua.chynnist.data.Laws
import ua.chynnist.data.Library
import ua.chynnist.text.Reading
import ua.chynnist.ui.theme.CardTitle
import ua.chynnist.ui.theme.ChynnistTheme
import ua.chynnist.ui.theme.Look
import ua.chynnist.ui.theme.LookStore

/** The four sections at the bottom of the screen. */
enum class Tab(@StringRes val title: Int, @DrawableRes val icon: Int, @StringRes val empty: Int) {
    NEWS(R.string.tab_news, R.drawable.ic_news, R.string.empty_news),
    DOCUMENTS(R.string.tab_documents, R.drawable.ic_document, R.string.empty_documents),
    SEARCH(R.string.tab_search, R.drawable.ic_search, R.string.empty_search),
    FOLLOWED(R.string.tab_followed, R.drawable.ic_bookmark, R.string.empty_followed),
}

class MainActivity : ComponentActivity() {
    /** Light or dark, and the day and night themes; remembered on this phone only. */
    private val look = mutableStateOf(Look())

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(AppLanguage.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        look.value = LookStore.load(this)
        setContent {
            val theme = look.value.current(isSystemInDarkTheme())
            // Status and navigation bar icons follow the chosen theme, not only the phone
            LaunchedEffect(theme.dark) {
                val bars = if (theme.dark) SystemBarStyle.dark(Color.TRANSPARENT) else SystemBarStyle.light(Color.TRANSPARENT, Color.TRANSPARENT)
                enableEdgeToEdge(statusBarStyle = bars, navigationBarStyle = bars)
            }
            ChynnistTheme(theme) { App() }
        }
    }

    /**
     * The sections, with settings and "About" on top of them, and the documents opened from the list (one on
     * top of another when a link leads on); back goes one step down.
     */
    @Composable
    private fun App() {
        val context = this
        LaunchedEffect(Unit) { Library.load(context) }
        val laws by Library.state.collectAsState()
        var tab by rememberSaveable { mutableStateOf(Tab.DOCUMENTS) }
        var over by rememberSaveable { mutableStateOf(NONE) }
        // Documents opened, the last on top: "path" or "path#anchor"
        var opened by rememberSaveable { mutableStateOf(listOf<String>()) }
        var toc by rememberSaveable { mutableStateOf(false) }
        var filter by remember { mutableStateOf(ReadingStore.filter(context)) }
        var scale by remember { mutableStateOf(ReadingStore.scale(context)) }
        var missing by rememberSaveable { mutableStateOf<String?>(null) }
        val scope = rememberCoroutineScope()

        // Opening a file with laws: it is checked completely before it is taken
        var installing by remember { mutableStateOf(false) }
        var refused by remember { mutableStateOf<Library.Problem?>(null) }
        val chooser = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
            if (uri != null) {
                installing = true
                scope.launch {
                    try {
                        Library.install(context, uri)
                        ReadingCache.clear()
                        opened = emptyList()
                        over = NONE
                        tab = Tab.DOCUMENTS
                    } catch (e: Library.Refused) {
                        refused = e.problem
                    } finally {
                        installing = false
                    }
                }
            }
        }
        val openFile = { chooser.launch(arrayOf("*/*")) }
        if (installing) Waiting(stringResource(R.string.installing))
        refused?.let { problem ->
            AlertDialog(
                onDismissRequest = { refused = null },
                title = { Text(stringResource(R.string.not_opened)) },
                text = { Text(problemText(problem)) },
                confirmButton = { TextButton(onClick = { refused = null }) { Text(stringResource(R.string.ok)) } },
            )
        }

        val uri = LocalUriHandler.current
        fun browse(url: String) {
            try {
                uri.openUri(url)
            } catch (_: ActivityNotFoundException) {
                // No browser on the phone: nothing to open it with
            } catch (_: IllegalArgumentException) {
                // Not a link Android can open
            }
        }
        missing?.let { target ->
            MissingDocument(
                onSite = { missing = null; browse(radaUrl(target)) },
                onDismiss = { missing = null },
            )
        }

        fun follow(href: String) {
            when {
                href.startsWith("#") -> opened = opened.dropLast(1) + (opened.last().substringBefore('#') + href)
                href.startsWith("suvii:") -> {
                    val target = href.removePrefix("suvii:")
                    scope.launch {
                        val here = try {
                            Library.read { Laws.has(it.db, target.substringBefore('#')) }
                        } catch (_: Exception) {
                            false
                        }
                        if (here) opened = opened + target else missing = target
                    }
                }
                href.startsWith("https://") -> browse(href)
            }
        }

        val ready = laws as? Library.State.Ready
        val top = opened.lastOrNull()
        val states = rememberSaveableStateHolder()
        BackHandler(enabled = over != NONE || top != null) {
            when {
                over == ABOUT -> over = SETTINGS
                over != NONE -> over = NONE
                toc -> toc = false
                else -> opened = opened.dropLast(1)
            }
        }
        when {
            over == SETTINGS -> SettingsPage(
                look.value,
                onLook = { look.value = it; LookStore.save(this, it) },
                language = AppLanguage.current(this),
                onLanguage = { AppLanguage.set(this, it) },
                onAbout = { over = ABOUT },
                onBack = { over = NONE },
                laws = laws,
                onOpenFile = openFile,
            )
            over == ABOUT -> AboutPage { over = SETTINGS }
            top != null && ready != null -> {
                val path = top.substringBefore('#')
                val anchor = top.substringAfter('#', "").ifEmpty { null }
                // Each document opened keeps its own place, also while another is on top of it
                states.SaveableStateProvider(path + "@" + opened.size) {
                    OpenDocument(
                        path = path,
                        anchor = anchor,
                        info = ready.info,
                        scale = scale,
                        onScale = { scale = it; ReadingStore.saveScale(context, it) },
                        toc = toc,
                        onToc = { toc = it },
                        onLink = ::follow,
                        onBack = { if (toc) toc = false else opened = opened.dropLast(1) },
                        onAnchorUsed = { opened = opened.dropLast(1) + path },
                    )
                }
            }
            else -> Sections(tab, onTab = { tab = it }, onSettings = { over = SETTINGS }) { t, padding ->
                val modifier = Modifier.padding(padding)
                when {
                    t != Tab.DOCUMENTS -> Empty(stringResource(t.empty), modifier, title = ready == null)
                    ready != null -> DocumentsSection(
                        ready.info,
                        filter,
                        onFilter = { filter = it; ReadingStore.saveFilter(context, it) },
                        onOpen = { opened = opened + it },
                        modifier = modifier,
                    )
                    laws is Library.State.Loading -> Empty(stringResource(R.string.list_reading), modifier, title = false)
                    else -> NoLaws((laws as? Library.State.Broken)?.problem, openFile, modifier)
                }
            }
        }
    }

    private companion object {
        const val NONE = ""
        const val SETTINGS = "settings"
        const val ABOUT = "about"
    }
}

/** The page of a document on the Rada's site: "laws/2222-15#n12" → zakon.rada.gov.ua/laws/show/2222-15#n12. */
fun radaUrl(target: String): String {
    val path = target.substringBefore('#')
    val anchor = target.substringAfter('#', "")
    val number = path.removePrefix("laws/")
    return "https://zakon.rada.gov.ua/laws/show/" + Uri.encode(number, "/") + if (anchor.isEmpty()) "" else "#" + Uri.encode(anchor)
}

/** A document read from the file, with its contents page on top of it when asked for. */
@Composable
private fun OpenDocument(
    path: String,
    anchor: String?,
    info: Library.Info,
    scale: Float,
    onScale: (Float) -> Unit,
    toc: Boolean,
    onToc: (Boolean) -> Unit,
    onLink: (String) -> Unit,
    onBack: () -> Unit,
    onAnchorUsed: () -> Unit,
) {
    val reading by produceState<Result<Reading?>?>(null, path) {
        value = runCatching { ReadingCache.get(path) }
    }
    val names = rememberNames(info.fields)
    val list = rememberSaveable(saver = LazyListState.Saver) { LazyListState() }
    var jump by rememberSaveable { mutableStateOf(anchor) }
    // A new anchor in the same document (a link inside it) is a jump too
    LaunchedEffect(anchor) { if (anchor != null) jump = anchor }
    val loaded = reading
    when {
        loaded == null -> Waiting(stringResource(R.string.document_reading))
        loaded.getOrNull() == null -> {
            // Not here after all, or its text did not pass the checks: said plainly, never shown half-checked
            AlertDialog(
                onDismissRequest = onBack,
                title = { Text(stringResource(R.string.not_opened)) },
                text = { Text(stringResource(R.string.document_damaged)) },
                confirmButton = { TextButton(onClick = onBack) { Text(stringResource(R.string.ok)) } },
            )
        }
        toc -> {
            val r = loaded.getOrThrow()!!
            TocPage(
                r,
                currentBlock = maxOf(0, list.firstVisibleItemIndex - HEAD_ITEMS),
                onPick = { jump = it; onToc(false) },
                onBack = { onToc(false) },
            )
        }
        else -> DocumentScreen(
            reading = loaded.getOrThrow()!!,
            names = names,
            test = info.test,
            scale = scale,
            onScale = onScale,
            list = list,
            jump = jump,
            onJumped = { jump = null; if (anchor != null) onAnchorUsed() },
            onLink = onLink,
            onToc = { onToc(true) },
            onBack = onBack,
        )
    }
}

/** The last few documents read, so going back to one doesn't read it again. */
private object ReadingCache {
    private const val SIZE = 3
    private val kept = object : LinkedHashMap<String, Reading>(SIZE, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, Reading>?) = size > SIZE
    }

    suspend fun get(path: String): Reading? {
        synchronized(kept) { kept[path] }?.let { return it }
        val doc = Library.document(path) ?: return null
        val reading = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.Default) { Reading.from(doc) }
        synchronized(kept) { kept[path] = reading }
        return reading
    }

    /** Forgets everything: the laws on the phone were replaced. */
    fun clear() = synchronized(kept) { kept.clear() }
}

@Composable
private fun MissingDocument(onSite: () -> Unit, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.missing_title)) },
        text = { Text(stringResource(R.string.missing_text)) },
        confirmButton = { Button(onClick = onSite) { Text(stringResource(R.string.missing_site)) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}

/** A short wait, said in words. */
@Composable
private fun Waiting(text: String) {
    AlertDialog(
        onDismissRequest = {},
        confirmButton = {},
        text = { Text(text, style = MaterialTheme.typography.bodyLarge) },
    )
}

/** A section with the bar on top and the four sections at the bottom; [content] fills the rest. */
@Composable
fun Sections(
    tab: Tab,
    onTab: (Tab) -> Unit,
    onSettings: () -> Unit,
    content: @Composable (Tab, PaddingValues) -> Unit = { t, padding -> Empty(stringResource(t.empty), Modifier.padding(padding)) },
) {
    val scheme = MaterialTheme.colorScheme
    Scaffold(
        containerColor = scheme.background,
        topBar = {
            Bar(stringResource(tab.title), onBack = null) {
                IconButton(onClick = onSettings) {
                    Icon(painterResource(R.drawable.ic_settings), contentDescription = stringResource(R.string.settings))
                }
            }
        },
        bottomBar = {
            NavigationBar(containerColor = scheme.surface) {
                for (t in Tab.entries) {
                    NavigationBarItem(
                        selected = t == tab,
                        onClick = { onTab(t) },
                        icon = { Icon(painterResource(t.icon), contentDescription = null) },
                        label = { TabLabel(stringResource(t.title)) },
                    )
                }
            }
        },
    ) { padding ->
        content(tab, padding)
    }
}

/**
 * A section's name under its icon: one line, never broken inside a word. Four of them share a phone's
 * width, so the phone's font size enlarges them only up to [MAX_LABEL_SCALE]; the screen's own text
 * still grows in full.
 */
@Composable
private fun TabLabel(text: String) {
    val scale = LocalDensity.current.fontScale
    val style = MaterialTheme.typography.labelMedium
    val size = style.fontSize * (minOf(scale, MAX_LABEL_SCALE) / scale)
    Text(text, style = style.copy(fontSize = size, lineHeight = size * 1.3f), maxLines = 1, softWrap = false, overflow = TextOverflow.Ellipsis)
}

private const val MAX_LABEL_SCALE = 1.15f

/**
 * What a section shows before it has anything. Said plainly, with what comes next, so an empty screen
 * never looks broken.
 */
@Composable
fun Empty(text: String, modifier: Modifier = Modifier, title: Boolean = true) {
    Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(
            Modifier.widthIn(max = READING_WIDTH).fillMaxWidth().padding(32.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (title) {
                Text(stringResource(R.string.empty_title), style = CardTitle, color = MaterialTheme.colorScheme.onBackground,
                    textAlign = TextAlign.Center, modifier = Modifier.semantics { heading() })
            }
            Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center)
        }
    }
}
