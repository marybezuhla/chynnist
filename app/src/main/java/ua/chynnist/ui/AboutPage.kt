package ua.chynnist.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import ua.chynnist.R
import ua.chynnist.ui.theme.CardTitle

private const val SOURCE_URL = "https://github.com/marybezuhla/chynnist"
private const val LICENSE_URL = "https://github.com/marybezuhla/chynnist/blob/main/LICENSE"
/** Where the laws come from; the portal's terms ask every copy to name it. */
private const val DATA_URL = "https://data.rada.gov.ua"

/**
 * "About Chynnist": the author's letter and the ways to support Ukraine (as in her other apps), where the
 * laws come from and that this is not an official publication, and the plain facts: licence, AI,
 * libraries, what the app does not do, version. Links only open in the browser.
 */
@Composable
fun AboutPage(onBack: () -> Unit) {
    val scheme = MaterialTheme.colorScheme
    val uri = LocalUriHandler.current
    // No browser on the phone: nothing happens rather than a crash
    val open = { url: String -> runCatching { uri.openUri(url) }; Unit }
    Scaffold(containerColor = scheme.background, topBar = { Bar(stringResource(R.string.about_app), onBack) }) { padding ->
        Box(Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()), contentAlignment = Alignment.TopCenter) {
            Column(Modifier.widthIn(max = READING_WIDTH).fillMaxWidth().padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                AuthorLetter()
                Spacer(Modifier.height(24.dp))
                SupportUkraine(open)

                Spacer(Modifier.height(24.dp))
                Heading(stringResource(R.string.data_title))
                Body(stringResource(R.string.data_body))
                Body(stringResource(R.string.not_official))
                TextButton(onClick = { open(DATA_URL) }) { Text(stringResource(R.string.data_open)) }

                Spacer(Modifier.height(16.dp))
                Heading(stringResource(R.string.about_title))
                Body(stringResource(R.string.about_text))
                val context = LocalContext.current
                val version = remember {
                    runCatching { context.packageManager.getPackageInfo(context.packageName, 0).versionName }.getOrNull()
                }
                version?.let { Body(stringResource(R.string.about_version, it)) }
                Row {
                    TextButton(onClick = { open(SOURCE_URL) }) { Text(stringResource(R.string.source_code)) }
                    TextButton(onClick = { open(LICENSE_URL) }) { Text(stringResource(R.string.license)) }
                }
            }
        }
    }
}

@Composable
private fun Heading(text: String) {
    Text(text, style = CardTitle, color = MaterialTheme.colorScheme.onSurface, textAlign = TextAlign.Center,
        modifier = Modifier.padding(bottom = 4.dp).semantics { heading() })
}

@Composable
private fun Body(text: String) {
    Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp))
}
