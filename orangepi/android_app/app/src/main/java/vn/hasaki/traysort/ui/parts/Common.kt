// May manh giao dien dung lai o nhieu man hinh. Khong cai nao biet ve API hay
// ViewModel - chi nhan du lieu vao va ve ra.
package vn.hasaki.traysort.ui.parts

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.ui.theme.LocalBrand

/** Mot khoi noi dung co vien va tieu de - tuong duong .panel ben web. */
@Composable
fun Panel(
    title: String,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    action: (@Composable () -> Unit)? = null,
    contentPadding: PaddingValues = PaddingValues(14.dp),
    content: @Composable ColumnScope.() -> Unit,
) {
    val brand = LocalBrand.current
    Column(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(MaterialTheme.colorScheme.surface)
            .border(1.dp, brand.line, RoundedCornerShape(16.dp))
            .padding(contentPadding),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier
                    .size(3.dp, 16.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(MaterialTheme.colorScheme.primary),
            )
            Spacer(Modifier.width(8.dp))
            Text(
                title,
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onSurface,
            )
            if (subtitle != null) {
                Spacer(Modifier.width(8.dp))
                Text(
                    subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = brand.muted,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f, fill = false),
                )
            }
            if (action != null) {
                Spacer(Modifier.weight(1f))
                action()
            }
        }
        Spacer(Modifier.height(10.dp))
        Column(verticalArrangement = Arrangement.spacedBy(8.dp), content = content)
    }
}

/** Vien tron nho co cham mau - dung cho trang thai ket noi. */
@Composable
fun Pill(text: String, color: Color, modifier: Modifier = Modifier) {
    Row(
        modifier
            .clip(CircleShape)
            .background(color.copy(alpha = 0.14f))
            .padding(horizontal = 10.dp, vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(color))
        Spacer(Modifier.width(6.dp))
        Text(
            text,
            style = MaterialTheme.typography.labelMedium,
            color = color,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

/** O so lieu nho: nhan mo + tri so dam. Dung cho X / Y / Z / Tồn. */
@Composable
fun Readout(label: String, value: String, unit: String? = null, modifier: Modifier = Modifier) {
    val brand = LocalBrand.current
    Column(
        modifier
            .clip(RoundedCornerShape(10.dp))
            .background(brand.surfaceAlt)
            .padding(horizontal = 10.dp, vertical = 6.dp),
    ) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = brand.muted)
        Row(verticalAlignment = Alignment.Bottom) {
            Text(value, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurface)
            if (unit != null) {
                Spacer(Modifier.width(2.dp))
                Text(unit, style = MaterialTheme.typography.labelSmall, color = brand.muted)
            }
        }
    }
}

/** Dai bao mau: canh bao vang, loi do. Khong co gi thi khong ve. */
@Composable
fun Banner(text: String, level: LogLevelTone, modifier: Modifier = Modifier) {
    val brand = LocalBrand.current
    val color = when (level) {
        LogLevelTone.ERROR -> brand.danger
        LogLevelTone.WARN -> brand.warn
        LogLevelTone.OK -> brand.ok
    }
    Row(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(color.copy(alpha = 0.13f))
            .border(1.dp, color.copy(alpha = 0.45f), RoundedCornerShape(12.dp))
            .padding(12.dp),
    ) {
        Text(text, style = MaterialTheme.typography.bodySmall, color = color)
    }
}

enum class LogLevelTone { OK, WARN, ERROR }
