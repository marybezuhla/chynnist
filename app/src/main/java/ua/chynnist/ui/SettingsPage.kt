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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import ua.chynnist.R
import ua.chynnist.ui.theme.Look
import ua.chynnist.ui.theme.LookSettings

/** The app's language, light or dark, the day and night themes (as in Komora), "About", and erasing all data. */
@Composable
fun SettingsPage(
    look: Look,
    onLook: (Look) -> Unit,
    language: AppLanguage.Choice,
    onLanguage: (AppLanguage.Choice) -> Unit,
    onAbout: () -> Unit,
    onBack: () -> Unit,
) {
    val scheme = MaterialTheme.colorScheme
    Scaffold(containerColor = scheme.background, topBar = { Bar(stringResource(R.string.settings), onBack) }) { padding ->
        Box(Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()), contentAlignment = Alignment.TopCenter) {
            Column(Modifier.widthIn(max = READING_WIDTH).fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
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
