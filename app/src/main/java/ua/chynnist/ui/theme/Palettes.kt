package ua.chynnist.ui.theme

/**
 * Chynnist's colours, the same as Komora's (after Pysanka's themes): five for the day, five for the night, in pairs, and the
 * phone's own colours (Material You). Plain numbers (ARGB), so they can be checked for contrast on a computer.
 */
class Palette(
    val primary: Long,
    val onPrimary: Long,
    /** The gold or the second colour: progress, the "allow" card. */
    val secondary: Long,
    /** Behind everything. */
    val background: Long,
    /** The cards. */
    val surface: Long,
    val surfaceVariant: Long,
    val onSurface: Long,
    /** Smaller text: status lines, notes. */
    val onSurfaceVariant: Long,
    /** Error text: kept apart from the red of the accent. */
    val error: Long,
)

enum class Theme(val key: String, val dark: Boolean, val palette: Palette?) {
    // By day
    LINEN("linen", false, Palette(
        primary = 0xFFA3392C, onPrimary = 0xFFFFF8F0, secondary = 0xFF7D5A12,
        background = 0xFFE6DFD5, surface = 0xFFF8F3EB, surfaceVariant = 0xFFEBE3D8,
        onSurface = 0xFF2B2420, onSurfaceVariant = 0xFF5A5048, error = 0xFF8C1D18,
    )),
    VISK("visk", false, Palette(
        primary = 0xFF8A4A2A, onPrimary = 0xFFFFF8EC, secondary = 0xFF765010,
        background = 0xFFE2D5BC, surface = 0xFFF2E8D4, surfaceVariant = 0xFFE5D9C0,
        onSurface = 0xFF2E2116, onSurfaceVariant = 0xFF64503C, error = 0xFF9C1F17,
    )),
    NEBO("nebo", false, Palette(
        // Blue with honey, never with red: blue, white and red together read as another flag
        primary = 0xFF3D5F94, onPrimary = 0xFFFFFFFF, secondary = 0xFFA67200,
        background = 0xFFD9E0E7, surface = 0xFFF1F4F7, surfaceVariant = 0xFFE1E7EE,
        onSurface = 0xFF1E2A3C, onSurfaceVariant = 0xFF4A596D, error = 0xFFB3261E,
    )),
    GLYNA("glyna", false, Palette(
        // Fired clay: terracotta on warm cream, white cards
        primary = 0xFF9C4524, onPrimary = 0xFFFFF8F2, secondary = 0xFF8A5A2B,
        background = 0xFFF4EEE5, surface = 0xFFFFFFFF, surfaceVariant = 0xFFEFE7DC,
        onSurface = 0xFF2A211C, onSurfaceVariant = 0xFF6B5D52, error = 0xFFA8201A,
    )),
    KALYNA("kalyna", false, Palette(
        // Viburnum: berry red and a green leaf on warm cream
        primary = 0xFFA3263A, onPrimary = 0xFFFFF8F6, secondary = 0xFF3F6B3A,
        background = 0xFFF3E6E3, surface = 0xFFFFFAF8, surfaceVariant = 0xFFF1E3DF,
        onSurface = 0xFF2A1E1F, onSurfaceVariant = 0xFF62504F, error = 0xFF8C1D18,
    )),
    SYSTEM("system", false, null),

    // By night
    MAK("mak", true, Palette(
        // Lighter than Pysanka's red, so that red text on a dark card stays readable
        primary = 0xFFE0786B, onPrimary = 0xFF2A0D09, secondary = 0xFFC99A3A,
        background = 0xFF15110F, surface = 0xFF2A2320, surfaceVariant = 0xFF3A312C,
        onSurface = 0xFFF1E6D2, onSurfaceVariant = 0xFFC2B5A3, error = 0xFFFFB4A9,
    )),
    SMEREKA("smereka", true, Palette(
        primary = 0xFFC98F3A, onPrimary = 0xFF1A1208, secondary = 0xFFD6A64E,
        background = 0xFF101A15, surface = 0xFF1E2E25, surfaceVariant = 0xFF2A3D32,
        onSurface = 0xFFECE6D6, onSurfaceVariant = 0xFFB9BBA8, error = 0xFFFFB4A9,
    )),
    CHORNOZEM("chornozem", true, Palette(
        primary = 0xFFB98E3E, onPrimary = 0xFF1A1206, secondary = 0xFFB98E3E,
        background = 0xFF000000, surface = 0xFF151210, surfaceVariant = 0xFF241F1B,
        onSurface = 0xFFDED3C2, onSurfaceVariant = 0xFFA89C8B, error = 0xFFFFB4A9,
    )),
    ZHAR("zhar", true, Palette(
        // Embers: a warm glow on soot
        primary = 0xFFE3A07E, onPrimary = 0xFF2B140A, secondary = 0xFFD9B07A,
        background = 0xFF1C1A18, surface = 0xFF26231F, surfaceVariant = 0xFF34302B,
        onSurface = 0xFFF0E8DE, onSurfaceVariant = 0xFFB8ADA0, error = 0xFFFFB4A9,
    )),
    ZORIANA_NICH("zoriana_nich", true, Palette(
        // Starry night: deep blue with golden stars, Sky's pair
        primary = 0xFF93A9EA, onPrimary = 0xFF0F1733, secondary = 0xFFE6C15A,
        background = 0xFF0B1020, surface = 0xFF161E36, surfaceVariant = 0xFF222B47,
        onSurface = 0xFFE8ECF6, onSurfaceVariant = 0xFFA9B2C9, error = 0xFFFFB4A9,
    )),
    SYSTEM_DARK("system_dark", true, null);

    companion object {
        // The phone's own colours come first, then Sky and Starry night, the default pair.
        // In pairs: each day theme stands right above its night theme
        val DAY = listOf(SYSTEM, NEBO, KALYNA, LINEN, VISK, GLYNA)
        val NIGHT = listOf(SYSTEM_DARK, ZORIANA_NICH, MAK, CHORNOZEM, SMEREKA, ZHAR)
        /** A day theme's night pair (and the other way round): sky and starry night, linen and black earth... */
        fun pairOf(t: Theme): Theme = DAY.indexOf(t).takeIf { it >= 0 }?.let { NIGHT[it] } ?: DAY[NIGHT.indexOf(t).coerceAtLeast(0)]

        fun of(key: String?, fallback: Theme) = entries.firstOrNull { it.key == key } ?: fallback
    }
}

/** Light or dark: as the phone, or always one of them. */
enum class Mode(val key: String) {
    AUTO("auto"), LIGHT("light"), DARK("dark");

    companion object {
        fun of(key: String?) = entries.firstOrNull { it.key == key } ?: AUTO
    }
}

/** What the owner chose. Defaults: light or dark as the phone, Sky by day and Starry night by night (they suit the blue and yellow icon). */
data class Look(val mode: Mode = Mode.AUTO, val day: Theme = Theme.NEBO, val night: Theme = Theme.ZORIANA_NICH) {
    fun current(phoneIsDark: Boolean): Theme = when (mode) {
        Mode.AUTO -> if (phoneIsDark) night else day
        Mode.LIGHT -> day
        Mode.DARK -> night
    }
}

/** WCAG contrast between two colours (1 to 21); text needs at least 4.5. */
fun contrast(a: Long, b: Long): Double {
    fun channel(c: Long, shift: Int): Double {
        val v = ((c shr shift) and 0xFF) / 255.0
        return if (v <= 0.03928) v / 12.92 else Math.pow((v + 0.055) / 1.055, 2.4)
    }
    fun lum(c: Long) = 0.2126 * channel(c, 16) + 0.7152 * channel(c, 8) + 0.0722 * channel(c, 0)
    val (hi, lo) = listOf(lum(a), lum(b)).sortedDescending()
    return (hi + 0.05) / (lo + 0.05)
}

/** A mix of two colours: 0 is [a], 1 is [b]. */
fun mix(a: Long, b: Long, t: Double): Long {
    fun ch(c: Long, s: Int) = (c shr s) and 0xFF
    fun m(s: Int) = Math.round(ch(a, s) * (1 - t) + ch(b, s) * t)
    return (0xFFL shl 24) or (m(16) shl 16) or (m(8) shl 8) or m(0)
}
