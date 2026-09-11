// Man hinh chinh: quet ma, chon khay, chay chu trinh, sua ton kho.
// Cung bo chuc nang voi tab "Vận hành" ben web.
package vn.hasaki.traysort.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.ui.AppViewModel
import vn.hasaki.traysort.ui.LocalPane
import vn.hasaki.traysort.ui.UiState
import vn.hasaki.traysort.ui.parts.Banner
import vn.hasaki.traysort.ui.parts.Panel
import vn.hasaki.traysort.ui.parts.StageBar
import vn.hasaki.traysort.ui.parts.StateCard
import vn.hasaki.traysort.ui.parts.TrayGrid
import vn.hasaki.traysort.ui.parts.alertFor
import vn.hasaki.traysort.ui.theme.LocalBrand

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun OperateScreen(
    state: UiState,
    vm: AppViewModel,
    onOpenScanner: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val pane = LocalPane.current

    if (pane.wide) {
        // Tablet ngang: gian khay ben trai (no to nhat), bang dieu khien ben
        // phai. Hai cot cuon doc lap - dang xem cuoi luoi khay ma van bam
        // duoc nut Dung.
        Row(
            modifier.fillMaxSize().padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            LazyColumn(
                Modifier.weight(1.35f),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                item { TrayPanel(state, vm, onOpenScanner) }
            }
            LazyColumn(
                Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                item { CyclePanel(state, vm) }
                item { StockPanel(state, vm) }
            }
        }
        return
    }

    LazyColumn(
        modifier.fillMaxWidth(),
        contentPadding = PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { CyclePanel(state, vm) }
        item { TrayPanel(state, vm, onOpenScanner) }
        item { StockPanel(state, vm) }
    }
}

/* ----------------------------------------------------------------- chu trinh */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CyclePanel(state: UiState, vm: AppViewModel) {
    val brand = LocalBrand.current
    val status = state.snapshot.status
    val hasSlot = state.selectedSlot != null
    val idle = state.running == null

    Panel(
        title = "Chu trình",
        subtitle = state.selectedSlot?.let { "khay số $it" } ?: "chưa chọn khay",
    ) {
        StateCard(state.snapshot, state.slots)
        StageBar(status)

        status?.let { alertFor(it) }?.let { (text, tone) -> Banner(text, tone) }

        Spacer(Modifier.height(2.dp))

        Button(
            onClick = vm::runSlot,
            enabled = hasSlot && idle,
            modifier = Modifier.fillMaxWidth().height(64.dp),
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text("Chạy tự động", fontWeight = FontWeight.Bold)
                Text("tới khay → lật đổ → về chỗ chờ", style = MaterialTheme.typography.labelSmall)
            }
        }

        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            FilledTonalButton(onClick = vm::home, enabled = idle, modifier = Modifier.weight(1f).height(50.dp)) {
                Text("Lấy gốc tọa độ")
            }
            FilledTonalButton(onClick = vm::park, enabled = idle, modifier = Modifier.weight(1f).height(50.dp)) {
                Text("Về chỗ chờ")
            }
        }
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedButton(onClick = vm::resetFault, enabled = idle, modifier = Modifier.weight(1f).height(50.dp)) {
                Text("Xóa lỗi")
            }
            Button(
                onClick = vm::emergencyStop,
                colors = ButtonDefaults.buttonColors(containerColor = brand.danger),
                modifier = Modifier.weight(1f).height(50.dp),
            ) {
                Text("DỪNG", fontWeight = FontWeight.Bold)
            }
        }
    }
}

/* ----------------------------------------------------------------- gian khay */
@Composable
private fun TrayPanel(state: UiState, vm: AppViewModel, onOpenScanner: () -> Unit) {
    val brand = LocalBrand.current
    val status = state.snapshot.status

    Panel(
        title = "Giàn khay",
        subtitle = with(state.summary) { "$totalItems/$totalCapacity vật · $fullSlots đầy · $emptySlots trống" },
    ) {
        ScanBar(onScan = { vm.scan(it) }, onCamera = onOpenScanner, enabled = state.running == null)

        TrayGrid(
            slots = state.slots,
            selected = state.selectedSlot,
            active = if (status?.busy == true) status.slot else null,
            onSelect = vm::selectSlot,
        )

        Text(
            "Chọn khay rồi bấm Chạy tự động, hoặc quét mã để máy tự tìm khay. " +
                "Xanh lá còn chỗ, vàng gần đầy, đỏ đã đầy.",
            style = MaterialTheme.typography.labelSmall,
            color = brand.muted,
        )
    }
}

/* ------------------------------------------------------------------- ton kho */
@Composable
private fun StockPanel(state: UiState, vm: AppViewModel) {
    val hasSlot = state.selectedSlot != null
    val idle = state.running == null

    Panel(
        title = "Tồn kho khay đang chọn",
        subtitle = state.selected?.let { "${it.count}/${it.capacity} vật" },
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilledTonalButton(
                onClick = vm::addItem, enabled = hasSlot && idle,
                modifier = Modifier.weight(1f).height(50.dp),
            ) { Text("+1 vật") }
            FilledTonalButton(
                onClick = vm::removeItem, enabled = hasSlot && idle,
                modifier = Modifier.weight(1f).height(50.dp),
            ) { Text("−1 vật") }
            OutlinedButton(
                onClick = vm::clearSlot, enabled = hasSlot && idle,
                modifier = Modifier.weight(1f).height(50.dp),
            ) { Text("Đổ hết") }
        }
    }
}

@Composable
private fun ScanBar(onScan: (String) -> Unit, onCamera: () -> Unit, enabled: Boolean) {
    var code by remember { mutableStateOf("") }

    fun submit() {
        val text = code.trim()
        if (text.isEmpty()) return
        code = ""
        onScan(text)
    }

    Row(verticalAlignment = Alignment.CenterVertically) {
        OutlinedTextField(
            value = code,
            onValueChange = { code = it },
            singleLine = true,
            enabled = enabled,
            placeholder = { Text("Quét mã hoặc gõ tay…") },
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
            keyboardActions = KeyboardActions(onDone = { submit() }),
            modifier = Modifier.weight(1f),
        )
        Spacer(Modifier.width(6.dp))
        IconButton(onClick = onCamera, enabled = enabled) {
            Icon(Icons.Filled.QrCodeScanner, contentDescription = "Quét bằng camera")
        }
        Button(onClick = ::submit, enabled = enabled && code.isNotBlank()) { Text("Quét") }
    }
}
