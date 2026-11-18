package ua.chynnist.ui

import android.content.Context
import ua.chynnist.data.Filter
import ua.chynnist.data.Order

/** The size of the text and the list's filter, remembered on this phone only. Unreadable means the defaults. */
object ReadingStore {
    private const val FILE = "reading"
    const val MIN_SCALE = 0.8f
    const val MAX_SCALE = 2f
    const val SCALE_STEP = 0.1f

    private fun prefs(context: Context) = context.getSharedPreferences(FILE, Context.MODE_PRIVATE)

    fun scale(context: Context): Float = try {
        prefs(context).getFloat("scale", 1f).coerceIn(MIN_SCALE, MAX_SCALE)
    } catch (_: Exception) {
        1f
    }

    fun saveScale(context: Context, scale: Float) = save(context) { putFloat("scale", scale) }

    fun filter(context: Context): Filter = try {
        val p = prefs(context)
        val d = Filter()
        Filter(
            activeOnly = p.getBoolean("active", d.activeOnly),
            kinds = p.getStringSet("kinds", null)?.filter { k -> k.all { it.isDigit() } }?.toSet() ?: d.kinds,
            order = Order.entries.firstOrNull { it.name == p.getString("order", null) } ?: d.order,
        )
    } catch (_: Exception) {
        Filter()
    }

    fun saveFilter(context: Context, filter: Filter) = save(context) {
        putBoolean("active", filter.activeOnly).putStringSet("kinds", filter.kinds).putString("order", filter.order.name)
    }

    private fun save(context: Context, edit: android.content.SharedPreferences.Editor.() -> Unit) {
        try {
            prefs(context).edit().apply(edit).apply()
        } catch (_: Exception) {
            // Only a preference: the app works the same without it
        }
    }
}
