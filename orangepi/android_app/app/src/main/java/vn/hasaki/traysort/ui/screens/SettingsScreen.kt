// Dia chi server, kieu giao dien, va nut hoi ban moi.
package vn.hasaki.traysort.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.BuildConfig
import vn.hasaki.traysort.core.Prefs
import vn.hasaki.traysort.core.ThemeMode
import vn.hasaki.traysort.data.UpdateStage
import vn.hasaki.traysort.ui.AppViewModel
import vn.hasaki.traysort.ui.UiState
import vn.hasaki.traysort.ui.parts.Banner
import vn.hasaki.traysort.ui.parts.LogLevelTone
import vn.hasaki.traysort.ui.parts.Panel
import vn.hasaki.traysort.ui.parts.installOrAskPermission
import vn.hasaki.traysort.ui.theme.LocalBrand

@Composable
fun SettingsScreen(state: UiState, vm: AppViewModel, modifier: Modifier = Modifier) {
    val brand = LocalBrand.current
    val context = LocalContext.current

    var draft by remember { mutableStateOf(state.serverUrl.ifBlank { Prefs.SUGGESTED }) }
    LaunchedEffect(state.serverUrl) {
        if (state.serverUrl.isNotBlank()) draft = state.serverUrl
    }

    // O nhap dai 1200 px thi khong ai doc duoc no bat dau tu dau. Kep lai.
    LazyColumn(
        modifier.fillMaxWidth(),
        contentPadding = PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        item {
            Panel(modifier = Modifier.widthIn(max = 620.dp), title = "Máy chủ", subtitle = if (state.linked) "đang nối" else "chưa nối") {
                OutlinedTextField(
                    value = draft,
                    onValueChange = { draft = it },
                    label = { Text("Địa chỉ Orange Pi") },
                    placeholder = { Text(Prefs.SUGGESTED) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Text(
                    "Gõ IP là đủ — app tự thêm http:// và cổng 8000. " +
                        "Đang dùng: ${state.serverUrl.ifBlank { "chưa đặt" }}",
                    style = MaterialTheme.typography.labelSmall,
                    color = brand.muted,
                )
                Button(
                    onClick = { vm.setServer(draft) },
                    enabled = draft.isNotBlank() && Prefs.normalizeUrl(draft) != state.serverUrl,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Lưu và nối lại") }

                if (state.snapshot.endpoint.isNotBlank()) {
                    Text(
                        "PLC: ${state.snapshot.endpoint} — ${if (state.snapshot.online) "online" else "offline"}",
                        style = MaterialTheme.typography.labelSmall,
                        color = if (state.snapshot.online) brand.ok else brand.danger,
                    )
                }
            }
        }

        item {
            Panel("Giao diện", modifier = Modifier.widthIn(max = 620.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    ThemeMode.entries.forEach { mode ->
                        FilterChip(
                            selected = state.theme == mode,
                            onClick = { vm.setTheme(mode) },
                            label = {
                                Text(
                                    when (mode) {
                                        ThemeMode.SYSTEM -> "Theo máy"
                                        ThemeMode.LIGHT -> "Sáng"
                                        ThemeMode.DARK -> "Tối"
                                    }
                                )
                            },
                        )
                    }
                }
            }
        }

        item {
            Panel("Phiên bản", modifier = Modifier.widthIn(max = 620.dp), subtitle = "${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})") {
                UpdateBlock(state, vm, context)
            }
        }
    }
}

@Composable
private fun UpdateBlock(state: UiState, vm: AppViewModel, context: android.content.Context) {
    val brand = LocalBrand.current

    when (val stage = state.update) {
        is UpdateStage.Downloading -> {
            Text("Đang tải… ${stage.percent}%", style = MaterialTheme.typography.bodySmall)
            LinearProgressIndicator(
                progress = { stage.percent / 100f },
                modifier = Modifier.fillMaxWidth().height(6.dp),
            )
        }

        is UpdateStage.Available -> {
            Banner("Có bản ${stage.release.versionName} trên server.", LogLevelTone.OK)
            if (stage.release.notes.isNotBlank()) {
                Text(stage.release.notes, style = MaterialTheme.typography.bodySmall, color = brand.muted)
            }
            Button(onClick = vm::downloadUpdate, modifier = Modifier.fillMaxWidth()) {
                Text("Tải bản ${stage.release.versionName}")
            }
        }

        is UpdateStage.Ready -> {
            Banner("Đã tải xong bản ${stage.release.versionName}.", LogLevelTone.OK)
            Button(
                onClick = { installOrAskPermission(context, vm) },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Cài đặt ngay") }
        }

        is UpdateStage.Failed -> {
            Banner(stage.reason, LogLevelTone.ERROR)
            OutlinedButton(onClick = { vm.checkUpdate(loud = true) }, modifier = Modifier.fillMaxWidth()) {
                Text("Thử lại")
            }
        }

        UpdateStage.Checking -> Text("Đang hỏi server…", style = MaterialTheme.typography.bodySmall)

        UpdateStage.UpToDate, UpdateStage.Idle -> {
            if (stage == UpdateStage.UpToDate) {
                Text(
                    "Đang chạy bản mới nhất.",
                    style = MaterialTheme.typography.bodySmall,
                    color = brand.ok,
                )
            }
            OutlinedButton(
                onClick = { vm.checkUpdate(loud = true) },
                enabled = state.serverUrl.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Kiểm tra bản mới") }
            Text(
                "App tự hỏi server một lần mỗi khi mở. Không cần cáp, không cần Play Store.",
                style = MaterialTheme.typography.labelSmall,
                color = brand.muted,
            )
        }
    }
    Spacer(Modifier.width(0.dp))
}
