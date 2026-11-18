package ua.chynnist.screens

import android.app.Application
import android.content.ComponentName
import androidx.activity.ComponentActivity
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.ui.Modifier
import io.github.marybezuhla.suvii.Field
import io.github.marybezuhla.suvii.TocEntry
import ua.chynnist.data.DocRow
import ua.chynnist.data.Filter
import ua.chynnist.data.Library
import ua.chynnist.text.Body
import ua.chynnist.text.Reading
import ua.chynnist.ui.AboutPage
import ua.chynnist.ui.AppLanguage
import ua.chynnist.ui.DocumentList
import ua.chynnist.ui.DocumentScreen
import ua.chynnist.ui.Names
import ua.chynnist.ui.NoLaws
import ua.chynnist.ui.Sections
import ua.chynnist.ui.SettingsPage
import ua.chynnist.ui.Tab
import ua.chynnist.ui.TocPage
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

    // The laws: the list, a document, its contents (made-up rows; the start of the Constitution)
    private val fields = mapOf(
        "status" to Field("status", "enum", mapOf("uk" to "Стан"), false, mapOf(
            "in_force" to mapOf("uk" to "Чинний", "en" to "In force"),
            "repealed_except" to mapOf("uk" to "Втратив чинність, крім окремих положень", "en" to "Repealed except some provisions"),
        )),
        "kind" to Field("kind", "enum", mapOf("uk" to "Вид"), true, mapOf(
            "1" to mapOf("uk" to "Закон", "en" to "Law"), "21" to mapOf("uk" to "Кодекс України", "en" to "Code of Ukraine"),
        )),
    )
    private val rows = listOf(
        DocRow("laws/2747-15", "Кодекс адміністративного судочинства України", "2747-15", "in_force", "2026-10-23"),
        DocRow("laws/322-08", "Кодекс законів про працю України", "322-08", "in_force", "2026-11-04"),
        DocRow("laws/5464-10", "Житловий Кодекс України", "5464-10", "repealed_except", "2026-02-15"),
        DocRow("laws/254к/96-вр", "Конституція України", "254к/96-вр", "in_force", "2020-01-01"),
        DocRow("laws/2341-14", "Кримінальний кодекс України", "2341-14", "in_force", "2026-11-15"),
        DocRow("laws/435-15", "Цивільний кодекс України", "435-15", "in_force", "2026-08-05"),
    )

    private fun list(name: String, lang: String = "uk") = shot(name, Theme.NEBO) {
        Sections(Tab.DOCUMENTS, onTab = {}, onSettings = {}) { _, padding ->
            DocumentList(
                total = rows.size + 1,
                row = { rows.getOrNull(it) },
                filter = Filter(),
                names = Names(fields, lang),
                onFilter = {},
                onChooseKinds = {},
                onOpen = {},
                modifier = Modifier.padding(padding),
            )
        }
    }

    private fun constitution(): Reading {
        val loader = javaClass.classLoader!!
        val html = loader.getResource("screens/constitution.html").readText()
        val toc = loader.getResource("screens/constitution-toc.tsv").readText().lines().filter { it.isNotBlank() }.map {
            val (level, anchor, title) = it.split('\t')
            TocEntry(level.toInt(), anchor, title)
        }
        return Reading("laws/254к/96-вр", "Конституція України", "254к/96-вр", "in_force", "2020-01-01", Body.parse(html), toc)
    }

    private fun document(name: String, theme: Theme = Theme.NEBO, test: Boolean = false, scale: Float = 1f, at: Int = 0) = shot(name, theme) {
        DocumentScreen(
            reading = remember { constitution() }, names = Names(fields, "uk"), test = test, scale = scale, onScale = {},
            list = rememberLazyListState(initialFirstVisibleItemIndex = at), jump = null, onJumped = {},
            onLink = {}, onToc = {}, onBack = {},
        )
    }

    @Test fun documents() = list("12-documents")
    @Config(qualifiers = "en-w400dp-h880dp-xhdpi")
    @Test fun documentsEnglish() = list("13-documents-english", "en")
    @Config(qualifiers = "uk-w320dp-h1400dp-xhdpi", fontScale = 2.0f)
    @Test fun documentsNarrowLargeFont() = list("14-documents-narrow-large-font")
    @Test fun noLaws() = shot("15-no-laws", Theme.NEBO) {
        Sections(Tab.DOCUMENTS, onTab = {}, onSettings = {}) { _, padding -> NoLaws(null, onOpenFile = {}, Modifier.padding(padding)) }
    }
    @Test fun lawsRefused() = shot("16-laws-broken", Theme.NEBO) {
        Sections(Tab.DOCUMENTS, onTab = {}, onSettings = {}) { _, padding -> NoLaws(Library.Problem.UNTRUSTED, onOpenFile = {}, Modifier.padding(padding)) }
    }
    @Test fun documentStart() = document("17-document", test = true)
    @Test fun documentArticles() = document("18-document-articles", at = 6)
    @Config(qualifiers = "+night")
    @Test fun documentDark() = document("19-document-dark", Theme.ZORIANA_NICH, at = 6)
    @Config(qualifiers = "uk-w320dp-h1400dp-xhdpi", fontScale = 2.0f)
    @Test fun documentNarrowLargeFont() = document("20-document-narrow-large-font", scale = 1.3f, at = 6)
    @Config(qualifiers = "uk-w400dp-h2400dp-xhdpi")
    @Test fun documentTable() = document("21-document-table", at = 50)
    @Test fun contents() = shot("22-contents", Theme.NEBO) { TocPage(remember { constitution() }, currentBlock = 12, onPick = {}, onBack = {}) }
    @Test fun settingsWithLaws() = shot("23-settings-laws", Theme.NEBO) {
        SettingsPage(
            Look(), onLook = {}, language = AppLanguage.Choice.AUTO, onLanguage = {}, onAbout = {}, onBack = {},
            laws = Library.State.Ready(Library.Info("Законодавство України (пробна збірка)", 1, "2026-11-18", 28, test = true, fields = fields)),
        )
    }
}
