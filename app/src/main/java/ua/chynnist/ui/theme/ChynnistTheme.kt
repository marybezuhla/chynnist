package ua.chynnist.ui.theme

import android.content.Context
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.style.Hyphens
import androidx.compose.ui.text.style.LineBreak
import androidx.compose.ui.text.style.TextAlign

/** Material colours from one of the themes; the phone's own (Material You) for the system ones. */
fun colorScheme(theme: Theme, context: Context): ColorScheme {
    val p = theme.palette
        ?: return if (theme.dark) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
    fun c(v: Long) = Color(v)
    val base = if (theme.dark) darkColorScheme() else lightColorScheme()
    return base.copy(
        primary = c(p.primary),
        onPrimary = c(p.onPrimary),
        primaryContainer = c(mix(p.surface, p.primary, 0.2)),
        onPrimaryContainer = c(p.onSurface),
        secondary = c(p.secondary),
        onSecondary = c(p.onPrimary),
        secondaryContainer = c(mix(p.surface, p.secondary, 0.25)),
        onSecondaryContainer = c(p.onSurface),
        tertiary = c(p.secondary),
        onTertiary = c(p.onPrimary),
        background = c(p.background),
        onBackground = c(p.onSurface),
        // Cards are the lighter (or, at night, raised) surface; the top bar sits on the background
        surface = c(p.surface),
        onSurface = c(p.onSurface),
        surfaceVariant = c(p.surfaceVariant),
        onSurfaceVariant = c(p.onSurfaceVariant),
        surfaceContainerLowest = c(p.surface),
        surfaceContainerLow = c(p.surface),
        surfaceContainer = c(p.surface),
        surfaceContainerHigh = c(p.surface),
        surfaceContainerHighest = c(p.surface),
        surfaceBright = c(p.surface),
        surfaceDim = c(p.background),
        outline = c(p.onSurfaceVariant),
        outlineVariant = c(mix(p.surfaceVariant, p.onSurfaceVariant, 0.3)),
        error = c(p.error),
        // The box a problem is told in: a pale wash of the error colour, ordinary text on it (PaletteTest)
        errorContainer = c(mix(p.surface, p.error, if (theme.dark) 0.25 else 0.12)),
        onErrorContainer = c(p.onSurface),
    )
}

@Composable
fun ChynnistTheme(theme: Theme, content: @Composable () -> Unit) {
    val scheme = colorScheme(theme, LocalContext.current).let {
        // Descriptions and small print darker (or lighter at night) than Android's grey: easier to read
        it.copy(onSurfaceVariant = androidx.compose.ui.graphics.lerp(it.onSurfaceVariant, it.onSurface, 0.45f))
    }
    MaterialTheme(colorScheme = scheme, typography = ChynnistType, content = content)
}

/**
 * Text a size larger than Android's defaults, so nothing is tiny; Android's own font size
 * setting still scales all of it.
 */
private val ChynnistType = androidx.compose.material3.Typography().run {
    // Body text as in Sprotyv: left-aligned, whole words (no hyphens), lines broken evenly over the
    // whole paragraph so the right edge has no chopped bits. Text set in the middle says so itself.
    fun body(t: TextStyle, size: Int, line: Int) = t.copy(
        fontSize = size.sp, lineHeight = line.sp, letterSpacing = 0.sp,
        textAlign = TextAlign.Start, lineBreak = LineBreak.Paragraph, hyphens = Hyphens.None,
    )
    // Labels and titles: the letters at their natural spacing (Material spreads them apart)
    fun label(t: TextStyle, size: Int, line: Int) = t.copy(fontSize = size.sp, lineHeight = line.sp, letterSpacing = 0.sp)
    copy(
        bodyLarge = body(bodyLarge, 18, 26),
        bodyMedium = body(bodyMedium, 17, 24),
        bodySmall = body(bodySmall, 15, 21),
        labelLarge = label(labelLarge, 16, 22),
        labelMedium = label(labelMedium, 15, 20),
        labelSmall = label(labelSmall, 14, 18),
        titleSmall = label(titleSmall, 16, 22),
        titleMedium = label(titleMedium, 19, 26),
        titleLarge = label(titleLarge, 24, 30),
    )
}

/** A card's title: larger and bolder than anything inside, as in Komora and Pysanka. */
val CardTitle: TextStyle
    @Composable get() = MaterialTheme.typography.titleMedium.copy(fontSize = 20.sp, lineHeight = 26.sp, fontWeight = FontWeight.SemiBold)

/**
 * A small embroidered motif under a title: three rhombuses in the middle (the big one in the theme's
 * accent, the small ones in its second colour) between two thin lines that fade out to the sides.
 * Decoration only: hidden from TalkBack.
 */
@Composable
fun Ornament(modifier: Modifier = Modifier) {
    val accent = MaterialTheme.colorScheme.primary
    val second = MaterialTheme.colorScheme.secondary
    val line = MaterialTheme.colorScheme.outlineVariant
    Canvas(modifier.fillMaxWidth().height(14.dp).clearAndSetSemantics { }) {
        val mid = size.height / 2f
        val cx = size.width / 2f
        val big = size.height * 0.5f
        val small = big * 0.62f
        val gap = big * 2.6f
        fun rhombus(x: Float, r: Float, color: androidx.compose.ui.graphics.Color) = drawPath(
            Path().apply {
                moveTo(x, mid - r); lineTo(x + r, mid); lineTo(x, mid + r); lineTo(x - r, mid); close()
            },
            color,
        )
        rhombus(cx - gap, small, second)
        rhombus(cx, big, accent)
        rhombus(cx + gap, small, second)
        // The lines: from a little beyond the motif, fading to nothing a short way off
        val inner = gap + small + big * 1.4f
        val reach = minOf(size.width / 2f - inner, 140.dp.toPx())
        if (reach > 0f) {
            val stroke = 1.dp.toPx()
            drawLine(
                androidx.compose.ui.graphics.Brush.horizontalGradient(listOf(line.copy(alpha = 0f), line), cx - inner - reach, cx - inner),
                Offset(cx - inner - reach, mid), Offset(cx - inner, mid), stroke,
            )
            drawLine(
                androidx.compose.ui.graphics.Brush.horizontalGradient(listOf(line, line.copy(alpha = 0f)), cx + inner, cx + inner + reach),
                Offset(cx + inner, mid), Offset(cx + inner + reach, mid), stroke,
            )
        }
    }
}
