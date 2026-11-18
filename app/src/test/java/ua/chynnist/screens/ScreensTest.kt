package ua.chynnist.screens

import android.app.Application
import android.content.ComponentName
import androidx.activity.ComponentActivity
import androidx.compose.runtime.Composable
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import ua.chynnist.ui.AboutPage
import ua.chynnist.ui.AppLanguage
import ua.chynnist.ui.Sections
import ua.chynnist.ui.SettingsPage
import ua.chynnist.ui.Tab
import ua.chynnist.ui.theme.Look
import ua.chynnist.ui.theme.Theme

/**
 * Draws Chynnist's screens on the computer, in several themes, sizes and font sizes. A screen that
 * crashes fails the build; the pictures go to build/screens for review.
 */
@RunWith(AndroidJUnit4::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35], qualifiers = "uk-w400dp-h880dp-xhdpi")
class ScreensTest {
    @get:Rule val compose = createEmptyComposeRule()

    @Before fun setUp() {
        val app = ApplicationProvider.getApplicationContext<Application>()
        // The empty activity that hosts each screen (only known to this test, never to the app)
        shadowOf(app.packageManager).addActivityIfNotPresent(ComponentName(app, ComponentActivity::class.java))
    }

    private fun shot(name: String, theme: Theme, content: @Composable () -> Unit) = shoot(compose, name, theme, content = content)

    private fun section(name: String, tab: Tab, theme: Theme = Theme.NEBO) = shot(name, theme) {
        Sections(tab, onTab = {}, onSettings = {})
    }

    @Test fun news() = section("01-news", Tab.NEWS)
    @Test fun documents() = section("02-documents", Tab.DOCUMENTS)
    @Test fun search() = section("03-search", Tab.SEARCH)
    @Test fun followed() = section("04-followed", Tab.FOLLOWED)
    @Config(qualifiers = "+night")
    @Test fun newsDark() = section("05-news-dark", Tab.NEWS, Theme.ZORIANA_NICH)
    @Test fun settings() = shot("06-settings", Theme.NEBO) {
        SettingsPage(Look(), onLook = {}, language = AppLanguage.Choice.AUTO, onLanguage = {}, onAbout = {}, onBack = {})
    }
    @Config(qualifiers = "uk-w400dp-h4600dp-xhdpi")
    @Test fun about() = shot("07-about", Theme.NEBO) { AboutPage(onBack = {}) }

    // The app in English
    @Config(qualifiers = "en-w400dp-h880dp-xhdpi")
    @Test fun newsEnglish() = section("08-news-english", Tab.NEWS)

    // A narrow phone with the largest font: nothing may be cut off or break inside a word
    @Config(qualifiers = "uk-w320dp-h1400dp-xhdpi", fontScale = 2.0f)
    @Test fun newsNarrowLargeFont() = section("09-news-narrow-large-font", Tab.NEWS)
    @Config(qualifiers = "uk-w320dp-h3200dp-xhdpi", fontScale = 2.0f)
    @Test fun settingsNarrowLargeFont() = shot("10-settings-narrow-large-font", Theme.NEBO) {
        SettingsPage(Look(), onLook = {}, language = AppLanguage.Choice.UK, onLanguage = {}, onAbout = {}, onBack = {})
    }

    // A tablet: the text keeps a readable width
    @Config(qualifiers = "uk-w1000dp-h700dp-xhdpi")
    @Test fun newsTablet() = section("11-news-tablet", Tab.DOCUMENTS)
}
