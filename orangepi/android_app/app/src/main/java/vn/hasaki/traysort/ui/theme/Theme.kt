// Bang mau lay dung tu app/static/css/styles.css cua web, de hai giao dien nhin
// ra la mot san pham. Material3 khong co cho de nhet "vang canh bao" hay "xanh
// con cho", nen may mau nghia-vu do di rieng trong LocalBrand.
package vn.hasaki.traysort.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.isSpecified
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import vn.hasaki.traysort.core.ThemeMode

@Immutable
data class Brand(
    val ok: Color,
    val warn: Color,
    val danger: Color,
    val accentSoft: Color,
    val surfaceAlt: Color,
    val line: Color,
    val muted: Color,
    // Thanh tren la mot dai gradient xanh Hasaki, chu trang - giong .topbar ben
    // web. Mau nay khong phai vai tro nao cua Material3 nen phai di rieng.
    val barStart: Color,
    val barEnd: Color,
    // Nen the nhan noi tren ro trong mo hinh 3D - --tag-bg ben web. Phai la mau
    // DAC MO (khong trong suot han) de chu doc duoc du phia sau la gi.
    val tagBg: Color,
    val dark: Boolean,
)

val LocalBrand = staticCompositionLocalOf {
    Brand(
        Color.Green, Color.Yellow, Color.Red, Color.Gray, Color.LightGray, Color.Gray, Color.Gray,
        Color.DarkGray, Color.Gray, Color.White, false,
    )
}

private val LightScheme = lightColorScheme(
    primary = Color(0xFF2E7D5B),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDCEDE4),
    onPrimaryContainer = Color(0xFF11311F),
    secondary = Color(0xFF3F9670),
    onSecondary = Color.White,
    // Material tu pha mau cho nut tonal va vach chon o thanh dieu huong; khong
    // dat thi no lay tim mac dinh, lac hoan toan voi mau thuong hieu.
    secondaryContainer = Color(0xFFDCEDE4),
    onSecondaryContainer = Color(0xFF11311F),
    tertiary = Color(0xFFD08700),
    onTertiary = Color(0xFF201704),
    tertiaryContainer = Color(0xFFFBEBCB),
    onTertiaryContainer = Color(0xFF3B2A00),
    background = Color(0xFFF3F5F4),
    onBackground = Color(0xFF1E2A25),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF1E2A25),
    surfaceVariant = Color(0xFFEEF1EF),
    onSurfaceVariant = Color(0xFF7B8A83),
    surfaceContainer = Color(0xFFFFFFFF),
    surfaceContainerHigh = Color(0xFFEEF1EF),
    surfaceContainerHighest = Color(0xFFE8ECEA),
    surfaceContainerLow = Color(0xFFF8FAF9),
    surfaceContainerLowest = Color(0xFFFFFFFF),
    outline = Color(0xFFE6E9E7),
    outlineVariant = Color(0xFFE6E9E7),
    error = Color(0xFFEF5A6A),
    onError = Color.White,
    errorContainer = Color(0xFFFBE0E3),
    onErrorContainer = Color(0xFF54121A),
)

private val DarkScheme = darkColorScheme(
    primary = Color(0xFF3F9670),
    onPrimary = Color(0xFF06170F),
    primaryContainer = Color(0xFF1D3C2D),
    onPrimaryContainer = Color(0xFFCFEADC),
    secondary = Color(0xFF2F7A5B),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFF1D3C2D),
    onSecondaryContainer = Color(0xFFCFEADC),
    tertiary = Color(0xFFE0B341),
    onTertiary = Color(0xFF201704),
    tertiaryContainer = Color(0xFF3D3110),
    onTertiaryContainer = Color(0xFFF6E4B6),
    background = Color(0xFF11161C),
    onBackground = Color(0xFFE8EDF1),
    surface = Color(0xFF1A2129),
    onSurface = Color(0xFFE8EDF1),
    surfaceVariant = Color(0xFF242C35),
    onSurfaceVariant = Color(0xFF8B98A3),
    surfaceContainer = Color(0xFF1A2129),
    surfaceContainerHigh = Color(0xFF242C35),
    surfaceContainerHighest = Color(0xFF2C353F),
    surfaceContainerLow = Color(0xFF161C23),
    surfaceContainerLowest = Color(0xFF0D1217),
    outline = Color(0xFF2A323B),
    outlineVariant = Color(0xFF2A323B),
    error = Color(0xFFFF6B6B),
    onError = Color(0xFF23090B),
    errorContainer = Color(0xFF3E1A1D),
    onErrorContainer = Color(0xFFFFD6D8),
)

private val LightBrand = Brand(
    ok = Color(0xFF0A7C3F),
    warn = Color(0xFFD08700),
    danger = Color(0xFFEF5A6A),
    accentSoft = Color(0xFFDCEDE4),
    surfaceAlt = Color(0xFFEEF1EF),
    line = Color(0xFFE6E9E7),
    muted = Color(0xFF7B8A83),
    barStart = Color(0xFF2E7D5B),
    barEnd = Color(0xFF3F9670),
    tagBg = Color(0xE0FFFFFF),
    dark = false,
)

private val DarkBrand = Brand(
    ok = Color(0xFF4ADE80),
    warn = Color(0xFFE0B341),
    danger = Color(0xFFFF6B6B),
    accentSoft = Color(0xFF1D3C2D),
    surfaceAlt = Color(0xFF242C35),
    line = Color(0xFF2A323B),
    muted = Color(0xFF8B98A3),
    barStart = Color(0xFF2F7A5B),
    barEnd = Color(0xFF3F9670),
    tagBg = Color(0xC7000000),
    dark = true,
)

private val BaseTypography = Typography().let { base ->
    base.copy(
        titleLarge = base.titleLarge.copy(fontWeight = FontWeight.Bold),
        titleMedium = base.titleMedium.copy(fontWeight = FontWeight.SemiBold),
        labelLarge = base.labelLarge.copy(fontWeight = FontWeight.SemiBold),
        // So do man hinh phai doc duoc tu xa, nen tach rieng mot kieu chu so.
        headlineSmall = TextStyle(fontSize = 22.sp, fontWeight = FontWeight.Bold),
    )
}

// Nhan ca bo chu len theo be ngang man hinh. Tablet ngang thi chu to hon 20%,
// khong thi dung cach may nua met la khong doc noi so lieu.
private fun TextStyle.scaled(by: Float): TextStyle = copy(
    fontSize = fontSize * by,
    lineHeight = if (lineHeight.isSpecified) lineHeight * by else lineHeight,
)

private fun typographyFor(scale: Float): Typography {
    if (scale == 1f) return BaseTypography
    return with(BaseTypography) {
        Typography(
            displayLarge = displayLarge.scaled(scale),
            displayMedium = displayMedium.scaled(scale),
            displaySmall = displaySmall.scaled(scale),
            headlineLarge = headlineLarge.scaled(scale),
            headlineMedium = headlineMedium.scaled(scale),
            headlineSmall = headlineSmall.scaled(scale),
            titleLarge = titleLarge.scaled(scale),
            titleMedium = titleMedium.scaled(scale),
            titleSmall = titleSmall.scaled(scale),
            bodyLarge = bodyLarge.scaled(scale),
            bodyMedium = bodyMedium.scaled(scale),
            bodySmall = bodySmall.scaled(scale),
            labelLarge = labelLarge.scaled(scale),
            labelMedium = labelMedium.scaled(scale),
            labelSmall = labelSmall.scaled(scale),
        )
    }
}

@Composable
fun TraySortTheme(mode: ThemeMode, scale: Float = 1f, content: @Composable () -> Unit) {
    val dark = when (mode) {
        ThemeMode.SYSTEM -> isSystemInDarkTheme()
        ThemeMode.LIGHT -> false
        ThemeMode.DARK -> true
    }

    CompositionLocalProvider(LocalBrand provides if (dark) DarkBrand else LightBrand) {
        MaterialTheme(
            colorScheme = if (dark) DarkScheme else LightScheme,
            typography = typographyFor(scale),
            content = content,
        )
    }
}
