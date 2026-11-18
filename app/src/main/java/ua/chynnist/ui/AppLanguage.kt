package ua.chynnist.ui

import android.app.Activity
import android.app.LocaleManager
import android.content.Context
import android.content.res.Configuration
import android.os.Build
import android.os.LocaleList
import java.util.Locale

/**
 * Chynnist's language: as the phone, Ukrainian or English. On Android 13+ it is Android's own
 * per-app language (the same as in the phone's settings); before that, a setting kept by Chynnist.
 */
object AppLanguage {
    enum class Choice(val tag: String?) { AUTO(null), UK("uk"), EN("en") }

    private const val FILE = "language"
    private const val KEY = "tag"

    fun current(context: Context): Choice {
        val tag = if (Build.VERSION.SDK_INT >= 33) {
            context.getSystemService(LocaleManager::class.java)?.applicationLocales?.get(0)?.language
        } else {
            stored(context)
        }
        return Choice.entries.firstOrNull { it.tag != null && it.tag == tag } ?: Choice.AUTO
    }

    fun set(activity: Activity, choice: Choice) {
        // The same choice again: nothing to change, no restart of the screen
        if (choice == current(activity)) return
        if (Build.VERSION.SDK_INT >= 33) {
            // Android restarts the screen in the new language by itself
            activity.getSystemService(LocaleManager::class.java)?.applicationLocales =
                choice.tag?.let { LocaleList.forLanguageTags(it) } ?: LocaleList.getEmptyLocaleList()
        } else {
            try {
                activity.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit().putString(KEY, choice.tag).apply()
            } catch (_: Exception) {
                // Not saved: the language stays as it was
                return
            }
            activity.recreate()
        }
    }

    /** Before Android 13: the chosen language for this screen. From 13 on, Android does it. */
    fun wrap(base: Context): Context {
        if (Build.VERSION.SDK_INT >= 33) return base
        val tag = stored(base) ?: return base
        val config = Configuration(base.resources.configuration)
        config.setLocales(LocaleList(Locale.forLanguageTag(tag)))
        return base.createConfigurationContext(config)
    }

    private fun stored(context: Context): String? = try {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).getString(KEY, null)
            ?.takeIf { t -> Choice.entries.any { it.tag == t } }
    } catch (_: Exception) {
        // Unreadable preferences: as the phone, the default
        null
    }
}
