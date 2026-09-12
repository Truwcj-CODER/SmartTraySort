// Vai thu can nho giua hai lan mo app: dia chi server va kieu giao dien.
package vn.hasaki.traysort.core

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import vn.hasaki.traysort.BuildConfig

private val Context.store by preferencesDataStore(name = "traysort")

enum class ThemeMode { SYSTEM, LIGHT, DARK }

enum class Lang { VI, EN }

class Prefs(private val context: Context) {

    val serverUrl: Flow<String> = context.store.data.map { it[KEY_SERVER].orEmpty() }

    // Rong = chua ai nhap gi. Man hinh dau tien se hoi dia chi truoc khi vao app.
    val theme: Flow<ThemeMode> = context.store.data.map { prefs ->
        runCatching { ThemeMode.valueOf(prefs[KEY_THEME] ?: "SYSTEM") }.getOrDefault(ThemeMode.SYSTEM)
    }

    val lang: Flow<Lang> = context.store.data.map { prefs ->
        runCatching { Lang.valueOf(prefs[KEY_LANG] ?: "VI") }.getOrDefault(Lang.VI)
    }

    suspend fun setServerUrl(value: String) {
        context.store.edit { it[KEY_SERVER] = normalizeUrl(value) }
    }

    suspend fun setTheme(mode: ThemeMode) {
        context.store.edit { it[KEY_THEME] = mode.name }
    }

    suspend fun setLang(value: Lang) {
        context.store.edit { it[KEY_LANG] = value.name }
    }

    companion object {
        private val KEY_SERVER: Preferences.Key<String> = stringPreferencesKey("server_url")
        private val KEY_THEME: Preferences.Key<String> = stringPreferencesKey("theme")
        private val KEY_LANG: Preferences.Key<String> = stringPreferencesKey("lang")

        val SUGGESTED: String = BuildConfig.DEFAULT_SERVER

        // Nguoi van hanh go "192.168.1.20" hay "192.168.1.20:8000" la chuyen
        // thuong. Tu them http:// va cong 8000 cho khoi phai giai thich.
        fun normalizeUrl(raw: String): String {
            var text = raw.trim().trimEnd('/')
            if (text.isEmpty()) return ""
            if (!text.startsWith("http://") && !text.startsWith("https://")) {
                text = "http://$text"
            }
            val afterScheme = text.substringAfter("://")
            if (!afterScheme.contains(':') && !afterScheme.contains('/')) {
                text = "$text:8000"
            }
            return text
        }
    }
}
