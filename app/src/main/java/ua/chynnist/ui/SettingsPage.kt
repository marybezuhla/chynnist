package ua.chynnist.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import ua.chynnist.R
import ua.chynnist.data.Library
import ua.chynnist.ui.theme.Group
import ua.chynnist.ui.theme.SectionTitle
import ua.chynnist.ui.theme.Look
import ua.chynnist.ui.theme.LookSettings

/** The laws on the phone, the app's language, light or dark, the day and night themes (as in Komora), "About", and erasing all data. */
@Composable
fun SettingsPage(
    look: Look,
    onLook: (Look) -> Unit,
    language: AppLanguage.Choice,
    onLanguage: (AppLanguage.Choice) -> Unit,
    onAbout: () -> Unit,
    onBack: () -> Unit,
    laws: Library.State = Library.State.Empty,
    onOpenFile: () -> Unit = {},
) {
    val scheme = MaterialTheme.colorScheme
    Scaffold(containerColor = scheme.background, topBar = { Bar(stringResource(R.string.settings), onBack) }) { padding ->
        Box(Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()), contentAlignment = Alignment.TopCenter) {
            Column(Modifier.widthIn(max = READING_WIDTH).fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                LawsSettings(laws, onOpenFile)
                Spacer(Modifier.height(8.dp))
                LookSettings(look, onLook, language, onLanguage)
                Spacer(Modifier.height(16.dp))
                OutlinedButton(
                    onClick = onAbout,
                    shape = RoundedCornerShape(16.dp),
                    border = BorderStroke(1.dp, scheme.outline),
                    modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
                ) {
                    Text(stringResource(R.string.about_app), style = MaterialTheme.typography.titleMedium)
                }
                Spacer(Modifier.height(8.dp))
                EraseAll()
            }
        }
    }
}

/** What laws are on the phone, and a way to open a file with them. */
@Composable
private fun LawsSettings(laws: Library.State, onOpenFile: () -> Unit) {
    val scheme = MaterialTheme.colorScheme
    SectionTitle(stringResource(R.string.laws_title))
    Group {
        Column(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            val text = when (laws) {
                is Library.State.Ready -> listOfNotNull(
                    laws.info.title,
                    pluralStringResource(R.plurals.documents_count, laws.info.count.toInt(), laws.info.count.toInt()),
                    laws.info.sourceDate.takeIf { it.isNotEmpty() }?.let { stringResource(R.string.laws_as_of, showDate(it)) },
                    if (laws.info.test) stringResource(R.string.test_data) else null,
                ).joinToString("\n")
                is Library.State.Broken -> stringResource(R.string.laws_broken) + "\n" + problemText(laws.problem)
                else -> stringResource(R.string.empty_title)
            }
            Text(text, style = MaterialTheme.typography.bodyMedium, color = scheme.onSurface)
            Text(stringResource(R.string.laws_file_note), style = MaterialTheme.typography.bodySmall, color = scheme.onSurfaceVariant)
            OutlinedButton(onClick = onOpenFile, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                Text(stringResource(R.string.open_file))
            }
        }
    }
}
