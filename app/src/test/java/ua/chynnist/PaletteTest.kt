package ua.chynnist

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import ua.chynnist.ui.theme.Look
import ua.chynnist.ui.theme.Mode
import ua.chynnist.ui.theme.Theme
import ua.chynnist.ui.theme.contrast
import ua.chynnist.ui.theme.mix

/** Every theme stays easy to read: text at least 4.5:1, shapes that must be seen at least 3:1 (WCAG AA). */
class PaletteTest {
    private val themes = Theme.entries.filter { it.palette != null }

    @Test
    fun textIsReadable() {
        for (t in themes) {
            val p = t.palette!!
            val primaryContainer = mix(p.surface, p.primary, 0.2)
            val secondaryContainer = mix(p.surface, p.secondary, 0.25)
            val pairs = mapOf(
                "onSurface/surface" to (p.onSurface to p.surface),
                "onSurface/background" to (p.onSurface to p.background),
                "onSurfaceVariant/surface" to (p.onSurfaceVariant to p.surface),
                "onSurfaceVariant/background" to (p.onSurfaceVariant to p.background),
                "onSurfaceVariant/surfaceVariant" to (p.onSurfaceVariant to p.surfaceVariant),
                "onPrimary/primary" to (p.onPrimary to p.primary),
                "primary/surface" to (p.primary to p.surface),
                "primary/background" to (p.primary to p.background),
                "error/surface" to (p.error to p.surface),
                "onSurface/primaryContainer" to (p.onSurface to primaryContainer),
                // Words found by the search are shaded with it
                "onSurface/secondaryContainer" to (p.onSurface to secondaryContainer),
            )
            for ((name, c) in pairs) {
                val r = contrast(c.first, c.second)
                assertTrue("${t.key} $name is $r", r >= 4.5)
            }
        }
    }

    @Test
    fun shapesAreVisible() {
        for (t in themes) {
            val p = t.palette!!
            // The ornament, and the bookmark sign on a card
            assertTrue("${t.key} secondary/background", contrast(p.secondary, p.background) >= 3.0)
            assertTrue("${t.key} secondary/surface", contrast(p.secondary, p.surface) >= 3.0)
            assertTrue("${t.key} primary/background", contrast(p.primary, p.background) >= 3.0)
        }
    }

    @Test
    fun dayAndNightAreSeparate() {
        assertTrue(Theme.DAY.none { it.dark })
        assertTrue(Theme.NIGHT.all { it.dark })
        assertEquals(Theme.DAY.size, Theme.NIGHT.size)
    }

    @Test
    fun lookPicksByMode() {
        val look = Look(day = Theme.GLYNA, night = Theme.ZHAR)
        assertEquals(Theme.GLYNA, look.current(phoneIsDark = false))
        assertEquals(Theme.ZHAR, look.current(phoneIsDark = true))
        assertEquals(Theme.GLYNA, look.copy(mode = Mode.LIGHT).current(phoneIsDark = true))
        assertEquals(Theme.ZHAR, look.copy(mode = Mode.DARK).current(phoneIsDark = false))
        assertEquals(Theme.LINEN, Theme.of("unknown", Theme.LINEN))
    }

    @Test
    fun skyAndStarryNightByDefault() {
        val look = Look()
        assertEquals(Mode.AUTO, look.mode)
        assertEquals(Theme.NEBO, look.day)
        assertEquals(Theme.ZORIANA_NICH, look.night)
        assertEquals(Theme.ZORIANA_NICH, Theme.pairOf(look.day))
        assertEquals(Theme.SYSTEM, Theme.DAY.first())
        assertEquals(Theme.SYSTEM_DARK, Theme.NIGHT.first())
    }

    @Test
    fun contrastMatchesWcag() {
        assertEquals(21.0, contrast(0xFF000000, 0xFFFFFFFF), 0.01)
        assertEquals(1.0, contrast(0xFF777777, 0xFF777777), 0.001)
    }
}
