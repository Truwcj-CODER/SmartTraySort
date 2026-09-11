// Nhat ky: moi lenh gui di va ket qua tra ve, moi nhat len tren.
package vn.hasaki.traysort.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.ui.AppViewModel
import vn.hasaki.traysort.ui.LogLevel
import vn.hasaki.traysort.ui.UiState
import vn.hasaki.traysort.ui.theme.LocalBrand

@Composable
fun LogScreen(state: UiState, vm: AppViewModel, modifier: Modifier = Modifier) {
    val brand = LocalBrand.current

    LazyColumn(
        modifier.fillMaxWidth(),
        contentPadding = PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        item {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "${state.log.size} dòng",
                    style = MaterialTheme.typography.labelSmall,
                    color = brand.muted,
                    modifier = Modifier.weight(1f),
                )
                TextButton(onClick = vm::clearLog, enabled = state.log.isNotEmpty()) { Text("Xóa") }
            }
        }

        if (state.log.isEmpty()) {
            item {
                Text(
                    "chưa có gì — mỗi lệnh gửi đi sẽ ghi lại ở đây",
                    style = MaterialTheme.typography.bodySmall,
                    color = brand.muted,
                )
            }
        }

        items(state.log.size) { index ->
            val entry = state.log[index]
            val tone = when (entry.level) {
                LogLevel.OK -> brand.ok
                LogLevel.WARN -> brand.warn
                LogLevel.ERROR -> brand.danger
                LogLevel.INFO -> brand.muted
            }
            Row(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .background(MaterialTheme.colorScheme.surface)
                    .padding(horizontal = 10.dp, vertical = 8.dp),
                verticalAlignment = Alignment.Top,
            ) {
                Box(Modifier.padding(top = 5.dp).size(7.dp).clip(CircleShape).background(tone))
                Spacer(Modifier.width(8.dp))
                Text(entry.time, style = MaterialTheme.typography.labelSmall, color = brand.muted)
                Spacer(Modifier.width(8.dp))
                Text(
                    entry.text,
                    style = MaterialTheme.typography.bodySmall,
                    color = if (entry.level == LogLevel.INFO) MaterialTheme.colorScheme.onSurface else tone,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}
