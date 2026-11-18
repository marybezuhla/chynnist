package ua.chynnist.ui.theme

import android.content.Context
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.text.BasicText
import androidx.compose.foundation.text.TextAutoSize
import ua.chynnist.R
import ua.chynnist.ui.AppLanguage

/** Remembers the look on this phone only. Never needed for anything to work: unreadable means the defaults. */
object LookStore {
    private const val FILE = "look"

    fun load(context: Context): Look = try {
        val p = context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
        val d = Look()
        Look(Mode.of(p.getString("mode", null)), Theme.of(p.getString("day", null), d.day), Theme.of(p.getString("night", null), d.night))
            // A day theme is never used at night, and the other way round
            .let { if (it.day.dark || !it.night.dark) d else it }
    } catch (_: Exception) {
        // Unreadable preferences: the default look
        Look()
    }

    fun save(context: Context, look: Look) {
        try {
            context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit()
                .putString("mode", look.mode.key).putString("day", look.day.key).putString("night", look.night.key)
                .apply()
        } catch (_: Exception) {
            // Only a preference: the app works the same without it
        }
    }
}

@Composable
fun themeName(theme: Theme): String = stringResource(
    when (theme) {
        Theme.LINEN -> R.string.theme_linen
        Theme.VISK -> R.string.theme_visk
        Theme.NEBO -> R.string.theme_nebo
        Theme.GLYNA -> R.string.theme_glyna
        Theme.KALYNA -> R.string.theme_kalyna
        Theme.ZORIANA_NICH -> R.string.theme_zoriana_nich
        Theme.SYSTEM -> R.string.theme_system
        Theme.MAK -> R.string.theme_mak
        Theme.SMEREKA -> R.string.theme_smereka
        Theme.CHORNOZEM -> R.string.theme_chornozem
        Theme.ZHAR -> R.string.theme_zhar
        Theme.SYSTEM_DARK -> R.string.theme_system_dark
    },
)

/** Light or dark, then the day and the night theme as small pictures of the app; a tap chooses. */
@Composable
fun LookSettings(
    look: Look,
    onChange: (Look) -> Unit,
    language: AppLanguage.Choice,
    onLanguage: (AppLanguage.Choice) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        SectionTitle(stringResource(R.string.app_language))
        // One under another: the languages' names stay whole with the largest font
        Group {
            Choices(
                options = listOf(
                    AppLanguage.Choice.AUTO to R.string.lang_auto,
                    AppLanguage.Choice.UK to R.string.lang_uk,
                    AppLanguage.Choice.EN to R.string.lang_en,
                ),
                chosen = language,
                onChoose = onLanguage,
            )
        }
        Spacer(Modifier.height(8.dp))
        SectionTitle(stringResource(R.string.look_mode))
        Segments(
            options = listOf(Mode.AUTO to R.string.mode_auto, Mode.LIGHT to R.string.mode_light, Mode.DARK to R.string.mode_dark),
            chosen = look.mode,
        ) { onChange(look.copy(mode = it)) }
        Spacer(Modifier.height(8.dp))
        SectionTitle(stringResource(R.string.day_theme))
        // Choosing either brings its pair along (Starry night with Sky, and so on); the other can still be changed after
        Group { ThemeRow(Theme.DAY, look.day) { onChange(look.copy(day = it, night = Theme.pairOf(it))) } }
        Spacer(Modifier.height(8.dp))
        SectionTitle(stringResource(R.string.night_theme))
        Group { ThemeRow(Theme.NIGHT, look.night) { onChange(look.copy(night = it, day = Theme.pairOf(it))) } }
    }
}

/** A light card with a thin frame, holding one group of settings. */
@Composable
internal fun Group(content: @Composable () -> Unit) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth(),
    ) { Box(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) { content() } }
}

/** A pill split into choices; the chosen one is raised in the card colour. Read as radio buttons. */
@Composable
internal fun <T> Segments(options: List<Pair<T, Int>>, chosen: T, onChoose: (T) -> Unit) {
    val scheme = MaterialTheme.colorScheme
    Row(
        Modifier.fillMaxWidth().background(scheme.surfaceVariant, RoundedCornerShape(50)).padding(4.dp).selectableGroup(),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        for ((value, label) in options) {
            val selected = value == chosen
            Box(
                Modifier.weight(1f).heightIn(min = 48.dp)
                    .background(if (selected) scheme.surface else Color.Transparent, RoundedCornerShape(50))
                    // A frame too, so the choice is clear without telling colours apart
                    .border(1.dp, if (selected) scheme.outline else Color.Transparent, RoundedCornerShape(50))
                    .selectable(selected, role = Role.RadioButton) { onChoose(value) }
                    .padding(horizontal = 2.dp),
                contentAlignment = Alignment.Center,
            ) {
                // One line: with the largest font on a narrow phone the word gets smaller instead of
                // breaking in the middle ("Украї-нська")
                val style = MaterialTheme.typography.bodyMedium.merge(
                    color = if (selected) scheme.onSurface else scheme.onSurfaceVariant,
                    fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
                    textAlign = TextAlign.Center,
                )
                BasicText(
                    stringResource(label),
                    style = style,
                    maxLines = 1,
                    autoSize = TextAutoSize.StepBased(minFontSize = 8.sp, maxFontSize = style.fontSize, stepSize = 0.5.sp),
                )
            }
        }
    }
}

/** Choices one under another, each a whole row with a radio button. */
@Composable
private fun <T> Choices(options: List<Pair<T, Int>>, chosen: T, onChoose: (T) -> Unit) {
    Column(Modifier.fillMaxWidth().selectableGroup()) {
        for ((value, label) in options) {
            Row(
                Modifier.fillMaxWidth().heightIn(min = 48.dp).selectable(value == chosen, role = Role.RadioButton) { onChoose(value) },
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RadioButton(selected = value == chosen, onClick = null)
                Text(stringResource(label), style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(start = 12.dp))
            }
        }
    }
}

@Composable
internal fun SectionTitle(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        // In the middle, like every other title in the app
        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
        modifier = Modifier.fillMaxWidth().padding(top = 4.dp).semantics { heading() },
    )
}

/** All themes at once, in rows across the whole width: none hides behind the edge of the screen. */
@Composable
private fun ThemeRow(themes: List<Theme>, chosen: Theme, onChoose: (Theme) -> Unit) {
    Box(Modifier.fillMaxWidth()) {
        val gap = 10.dp
        // Rows of exactly three, each across the whole width: a flowing row could push the third onto the next line
        Column(
            Modifier.fillMaxWidth().selectableGroup().padding(vertical = 4.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            for (row in themes.chunked(3)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(gap)) {
                    for (theme in row) {
                        val selected = theme == chosen
                        Column(
                            Modifier.weight(1f).selectable(selected, role = Role.RadioButton) { onChoose(theme) },
                            horizontalAlignment = Alignment.CenterHorizontally,
                        ) {
                            Sample(theme, selected)
                            ThemeName(themeName(theme), selected)
                        }
                    }
                    // A short last row keeps the same sizes
                    repeat(3 - row.size) { Spacer(Modifier.weight(1f)) }
                }
            }
        }
    }
}

/** A tiny page: the background, one card with two lines of text and a button, in the theme's colours. */
@Composable
private fun Sample(theme: Theme, selected: Boolean) {
    val context = LocalContext.current
    val s = remember(theme) { colorScheme(theme, context) }
    val frame = if (selected) {
        BorderStroke(3.dp, MaterialTheme.colorScheme.primary)
    } else {
        BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
    }
    // A picture only: a screen reader reads the theme's name below it
    Surface(
        shape = RoundedCornerShape(12.dp),
        border = frame,
        color = s.background,
        modifier = Modifier.fillMaxWidth().clearAndSetSemantics { },
    ) {
        Box(Modifier.padding(8.dp)) {
            Column(
                Modifier.fillMaxWidth().background(s.surfaceContainerHighest, RoundedCornerShape(8.dp)).padding(8.dp),
                verticalArrangement = Arrangement.spacedBy(5.dp),
            ) {
                Bar(s.onSurface, 0.7f, 6)
                Bar(s.onSurfaceVariant, 0.9f, 4)
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    Box(Modifier.width(36.dp).height(14.dp).background(s.primary, RoundedCornerShape(7.dp)))
                    Box(Modifier.width(14.dp).height(14.dp).background(s.secondary, RoundedCornerShape(7.dp)))
                }
            }
        }
    }
}

@Composable
private fun Bar(color: Color, fraction: Float, height: Int) {
    Box(Modifier.fillMaxWidth(fraction).height(height.dp).background(color, RoundedCornerShape(height.dp / 2)))
}

/**
 * A theme's name under its picture. Never broken inside a word: as many lines as it has words, and with a
 * very large font on a narrow phone the name gets a little smaller instead ("Viburnu-m").
 */
@Composable
private fun ThemeName(name: String, selected: Boolean) {
    val style = MaterialTheme.typography.bodyMedium.merge(
        color = MaterialTheme.colorScheme.onSurface,
        fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal,
        textAlign = TextAlign.Center,
    )
    BasicText(
        name,
        modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
        style = style,
        maxLines = name.split(' ').size,
        autoSize = TextAutoSize.StepBased(minFontSize = 8.sp, maxFontSize = style.fontSize, stepSize = 0.5.sp),
    )
}
