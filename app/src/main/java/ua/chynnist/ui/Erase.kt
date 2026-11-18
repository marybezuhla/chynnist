package ua.chynnist.ui

import android.app.ActivityManager
import android.content.Context
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import ua.chynnist.R
import java.io.File

/**
 * "Erase all data": the downloaded laws, followed documents and the settings leave the phone at once,
 * as in Sprotyv. The laws that come with the app stay. Asked first: it cannot be undone.
 */
@Composable
internal fun EraseAll() {
    val context = LocalContext.current
    var ask by rememberSaveable { mutableStateOf(false) }
    OutlinedButton(
        onClick = { ask = true },
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
    ) { Text(stringResource(R.string.erase), color = MaterialTheme.colorScheme.error) }
    if (ask) {
        AlertDialog(
            onDismissRequest = { ask = false },
            title = { Text(stringResource(R.string.erase_question)) },
            text = { Text(stringResource(R.string.erase_text)) },
            confirmButton = {
                TextButton(onClick = { ask = false; erase(context) }, modifier = Modifier.heightIn(min = 48.dp)) {
                    Text(stringResource(R.string.erase_confirm), color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { ask = false }, modifier = Modifier.heightIn(min = 48.dp)) { Text(stringResource(android.R.string.cancel)) }
            },
        )
    }
}

private fun erase(context: Context) {
    val app = context.applicationContext
    // The app's language is kept by Android itself (13 and newer): back to "as on the phone"
    if (android.os.Build.VERSION.SDK_INT >= 33) {
        try { app.getSystemService(android.app.LocaleManager::class.java)?.applicationLocales = android.os.LocaleList.getEmptyLocaleList() } catch (_: Exception) { /* the rest still goes */ }
    }
    // Android erases all of the app's files and settings and closes it
    val done = try {
        app.getSystemService(ActivityManager::class.java)?.clearApplicationUserData() == true
    } catch (_: Exception) {
        // Refused by this phone: erased by hand just below
        false
    }
    if (done) return
    val data = File(app.applicationInfo.dataDir)
    // Everything in the app's own folder (what Android keeps there itself, like "lib", is not the app's to delete)
    (data.listFiles().orEmpty().toList() + listOf(app.cacheDir, app.codeCacheDir, app.noBackupFilesDir))
        .forEach { f -> try { f.deleteRecursively() } catch (_: Exception) { /* the next one still goes */ } }
    // Closed, so nothing still in memory writes anything back
    android.os.Process.killProcess(android.os.Process.myPid())
}
