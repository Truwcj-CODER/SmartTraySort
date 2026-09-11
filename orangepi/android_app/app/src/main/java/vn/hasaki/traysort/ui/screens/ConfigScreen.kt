// Tab cai dat may: kich thuoc gian kho, quy doi doi chieu voi TIA, chay tay, jog.
// Cung noi dung voi tab "Cài đặt" ben web.
package vn.hasaki.traysort.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.staggeredgrid.LazyVerticalStaggeredGrid
import androidx.compose.foundation.lazy.staggeredgrid.StaggeredGridCells
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.core.DERIVED_LABELS
import vn.hasaki.traysort.core.GEOMETRY_GROUPS
import vn.hasaki.traysort.core.formatValue
import vn.hasaki.traysort.ui.AppViewModel
import vn.hasaki.traysort.ui.UiState
import vn.hasaki.traysort.ui.parts.Banner
import vn.hasaki.traysort.ui.parts.LogLevelTone
import vn.hasaki.traysort.ui.parts.Panel
import vn.hasaki.traysort.ui.theme.LocalBrand

@Composable
fun ConfigScreen(state: UiState, vm: AppViewModel, modifier: Modifier = Modifier) {
    val brand = LocalBrand.current
    val idle = state.running == null

    // Ban nhap tai cho. Chi dong bo lai khi server gui bo cuc moi ve, khong thi
    // moi ban tin trang thai lai xoa mat con so nguoi dung dang go do.
    val draft = remember { mutableStateMapOf<String, String>() }
    LaunchedEffect(state.geometry) {
        if (state.geometry.isNotEmpty()) {
            GEOMETRY_GROUPS.flatMap { it.fields }.forEach { field ->
                state.geometry[field.key]?.let { draft[field.key] = formatValue(it, field.integer) }
            }
        }
    }

    var confirmReset by remember { mutableStateOf(false) }

    // Cac nhom cau hinh cao thap khac nhau, nen dung luoi so le: no tu xep cho
    // trong chu khong de mot cot dai ngoang canh mot cot ngan. Adaptive(340dp)
    // tu ra 1 cot tren dien thoai va 2-3 cot tren tablet - khong phai viet hai
    // nhanh layout rieng. Cung y voi "columns: 2 340px" ben CSS cua web.
    LazyVerticalStaggeredGrid(
        columns = StaggeredGridCells.Adaptive(340.dp),
        modifier = modifier.fillMaxWidth(),
        contentPadding = PaddingValues(12.dp),
        verticalItemSpacing = 12.dp,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Panel("Kích thước giàn khay", subtitle = "${state.plan.slots} rổ") {
                Text(
                    "Chỉ khai kích thước một cái rổ và hành trình hai trục. Số rổ, độ cao " +
                        "từng hàng và tọa độ từng rổ đều do server tính ra rồi ghi thẳng xuống PLC.",
                    style = MaterialTheme.typography.labelSmall,
                    color = brand.muted,
                )
            }
        }

        GEOMETRY_GROUPS.forEach { group ->
            item(key = group.legend) {
                Panel(group.legend) {
                    group.note?.let {
                        Text(it, style = MaterialTheme.typography.labelSmall, color = brand.muted)
                    }
                    group.fields.forEach { field ->
                        OutlinedTextField(
                            value = draft[field.key].orEmpty(),
                            onValueChange = { draft[field.key] = it },
                            label = { Text(field.label) },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(
                                keyboardType = if (field.integer) KeyboardType.Number else KeyboardType.Decimal,
                            ),
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
            }
        }

        item {
            Panel("Ghi xuống máy") {
                Button(
                    onClick = { readDraft(draft)?.let(vm::saveGeometry) },
                    enabled = idle,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Lưu cấu hình") }

                OutlinedButton(
                    onClick = vm::pushTable,
                    enabled = idle,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Đẩy tọa độ xuống PLC") }

                Text(
                    "Lưu xong là server tự đẩy bảng tọa độ xuống PLC. Nút dưới chỉ dùng khi " +
                        "vừa nạp lại khối trong TIA.",
                    style = MaterialTheme.typography.labelSmall,
                    color = brand.muted,
                )
            }
        }

        if (state.problems.isNotEmpty()) {
            item {
                Panel("Cấu hình chưa hợp lý") {
                    state.problems.forEach { Banner(it, LogLevelTone.WARN) }
                }
            }
        }

        item {
            Panel("Quy đổi — kiểm tra chéo với TIA") {
                state.derived.forEach { (key, value) ->
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            DERIVED_LABELS[key] ?: key,
                            style = MaterialTheme.typography.bodySmall,
                            color = brand.muted,
                            modifier = Modifier.weight(1f),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(value, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }

        /* ------------------------------------------------------------- chay tay */
        item { ManualPanel(state, vm) }
        item { JogPanel(vm) }

        item {
            Panel("Nguy hiểm") {
                OutlinedButton(
                    onClick = { confirmReset = true },
                    enabled = idle,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Xóa toàn bộ tồn kho", color = brand.danger) }
            }
            Spacer(Modifier.height(8.dp))
        }
    }

    if (confirmReset) {
        AlertDialog(
            onDismissRequest = { confirmReset = false },
            title = { Text("Xóa toàn bộ tồn kho?") },
            text = { Text("Số liệu của tất cả ${state.summary.slotCount} khay sẽ về 0. Không hoàn lại được.") },
            confirmButton = {
                TextButton(onClick = { confirmReset = false; vm.resetInventory() }) {
                    Text("Xóa hết", color = brand.danger)
                }
            },
            dismissButton = { TextButton(onClick = { confirmReset = false }) { Text("Thôi") } },
        )
    }
}

@Composable
private fun ManualPanel(state: UiState, vm: AppViewModel) {
    val brand = LocalBrand.current
    val idle = state.running == null
    val hasSlot = state.selectedSlot != null

    var moveX by remember { mutableStateOf("0") }
    var moveZ by remember { mutableStateOf("0") }
    var angle by remember { mutableStateOf("0") }

    Panel("Chạy tay", subtitle = "chỉ dùng khi căn chỉnh máy") {
        Text(
            "Mấy nút này bỏ qua chu trình tự động. Dùng để dò tọa độ và kiểm tra cơ cấu, " +
                "không dùng lúc sản xuất.",
            style = MaterialTheme.typography.labelSmall,
            color = brand.muted,
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilledTonalButton(onClick = vm::gotoSlot, enabled = hasSlot && idle, modifier = Modifier.weight(1f)) {
                Text("Chỉ tới khay")
            }
            FilledTonalButton(onClick = vm::tiltSlot, enabled = hasSlot && idle, modifier = Modifier.weight(1f)) {
                Text("Chỉ lật")
            }
            OutlinedButton(onClick = vm::teachSlot, enabled = hasSlot && idle, modifier = Modifier.weight(1f)) {
                Text("Teach")
            }
        }
        Text(
            state.selectedSlot?.let { "Đang thao tác trên khay $it." } ?: "Chọn khay bên tab Vận hành trước.",
            style = MaterialTheme.typography.labelSmall,
            color = brand.muted,
        )

        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            NumberBox("X ngang", moveX, { moveX = it }, Modifier.weight(1f))
            NumberBox("Z cao", moveZ, { moveZ = it }, Modifier.weight(1f))
            Button(
                onClick = { vm.moveTo(moveX.toDoubleOrNull() ?: return@Button, moveZ.toDoubleOrNull() ?: return@Button) },
                enabled = idle,
            ) { Text("Đi tới") }
        }

        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            NumberBox("Y góc lật", angle, { angle = it }, Modifier.weight(1f))
            Button(
                onClick = { vm.tiltTo(angle.toDoubleOrNull() ?: return@Button) },
                enabled = idle,
            ) { Text("Lật tới góc") }
        }
    }
}

@Composable
private fun NumberBox(label: String, value: String, onChange: (String) -> Unit, modifier: Modifier = Modifier) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label, style = MaterialTheme.typography.labelSmall) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
        modifier = modifier,
    )
}

// Chi doc duoc so. Bo trong hoac go nham chu thi khong gui gi ca - tha khong
// chay con hon chay toi mot toa do doan mo.
private fun readDraft(draft: Map<String, String>): Map<String, Double>? {
    val out = HashMap<String, Double>()
    GEOMETRY_GROUPS.flatMap { it.fields }.forEach { field ->
        val value = draft[field.key]?.trim()?.replace(',', '.')?.toDoubleOrNull() ?: return null
        out[field.key] = value
    }
    return out
}
