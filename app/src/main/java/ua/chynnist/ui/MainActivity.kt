package ua.chynnist.ui

import android.content.Context
import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.annotation.DrawableRes
import androidx.annotation.StringRes
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import ua.chynnist.R
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

    /** The sections, with settings and "About" on top of them; back goes one step down. */
    @Composable
    private fun App() {
        var tab by rememberSaveable { mutableStateOf(Tab.NEWS) }
        var over by rememberSaveable { mutableStateOf(NONE) }
        BackHandler(enabled = over != NONE) { over = if (over == ABOUT) SETTINGS else NONE }
        when (over) {
            SETTINGS -> SettingsPage(
                look.value,
                onLook = { look.value = it; LookStore.save(this, it) },
                language = AppLanguage.current(this),
                onLanguage = { AppLanguage.set(this, it) },
                onAbout = { over = ABOUT },
                onBack = { over = NONE },
            )
            ABOUT -> AboutPage { over = SETTINGS }
            else -> Sections(tab, onTab = { tab = it }, onSettings = { over = SETTINGS })
        }
    }

    private companion object {
        const val NONE = ""
        const val SETTINGS = "settings"
        const val ABOUT = "about"
    }
}

/** A section with the bar on top and the four sections at the bottom. */
@Composable
fun Sections(tab: Tab, onTab: (Tab) -> Unit, onSettings: () -> Unit) {
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
                        label = { Text(stringResource(t.title)) },
                    )
                }
            }
        },
    ) { padding ->
        Empty(stringResource(tab.empty), Modifier.padding(padding))
    }
}

/**
 * What a section shows before the first laws are on the phone. Said plainly, with what comes next,
 * so an empty screen never looks broken.
 */
@Composable
private fun Empty(text: String, modifier: Modifier = Modifier) {
    Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(
            Modifier.widthIn(max = READING_WIDTH).fillMaxWidth().padding(32.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(stringResource(R.string.empty_title), style = CardTitle, color = MaterialTheme.colorScheme.onBackground,
                textAlign = TextAlign.Center, modifier = Modifier.semantics { heading() })
            Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center)
        }
    }
}
