package ua.chynnist.screens

import android.graphics.Bitmap
import android.os.Looper
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.compose.ui.test.junit4.ComposeTestRule
import androidx.test.core.app.ActivityScenario
import org.robolectric.Shadows.shadowOf
import ua.chynnist.ui.theme.ChynnistTheme
import ua.chynnist.ui.theme.Theme
import java.io.File

/**
 * Draws [content] in [theme] on a screen of the test's size and saves it as build/screens/[name].png. A text
 * field with a cursor keeps the screen busy for ever: then ([manualClock]) time is moved on by hand.
 */
internal fun shoot(compose: ComposeTestRule, name: String, theme: Theme, manualClock: Boolean = false, content: @Composable () -> Unit) =
    ActivityScenario.launch(ComponentActivity::class.java).use { scenario ->
        if (manualClock) compose.mainClock.autoAdvance = false
        scenario.onActivity { it.setContent { ChynnistTheme(theme) { content() } } }
        repeat(8) {
            if (manualClock) repeat(30) { compose.mainClock.advanceTimeByFrame() } else compose.waitForIdle()
            shadowOf(Looper.getMainLooper()).idle()
        }
        var bitmap: Bitmap? = null
        scenario.onActivity { activity ->
            val view = activity.window.decorView
            bitmap = Bitmap.createBitmap(view.width, view.height, Bitmap.Config.ARGB_8888).also { view.draw(android.graphics.Canvas(it)) }
        }
        val dir = File("build/screens").apply { mkdirs() }
        File(dir, "$name.png").outputStream().use { bitmap!!.compress(Bitmap.CompressFormat.PNG, 100, it) }
        Unit
    }
