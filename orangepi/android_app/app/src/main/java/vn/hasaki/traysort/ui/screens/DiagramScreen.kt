// So do may + bang toa do tung ro. Chi de nhin, khong bam duoc gi.
package vn.hasaki.traysort.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.data.Slot
import vn.hasaki.traysort.ui.LocalPane
import vn.hasaki.traysort.ui.UiState
import vn.hasaki.traysort.ui.parts.MachineDiagram
import vn.hasaki.traysort.ui.parts.Panel
import vn.hasaki.traysort.ui.theme.LocalBrand

@Composable
fun DiagramScreen(state: UiState, modifier: Modifier = Modifier) {
    val brand = LocalBrand.current
    val status = state.snapshot.status

    // Man ngang: so do ben trai, bang toa do ben phai. Doi chieu "may dang o
    // dau" voi "ro nao o toa do nao" khong phai cuon qua cuon lai.
    if (LocalPane.current.wide) {
        Row(
            modifier.fillMaxSize().padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Column(Modifier.weight(1.4f)) { DiagramPanel(state) }
            LazyColumn(Modifier.weight(1f)) {
                item { TableHeader(state.slots.size) }
                items(state.slots.size, key = { state.slots[it].slot }) { CoordRow(state.slots[it]) }
            }
        }
        return
    }

    LazyColumn(
        modifier.fillMaxWidth(),
        contentPadding = PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { DiagramPanel(state) }
        item { TableHeader(state.slots.size) }
        items(state.slots.size, key = { state.slots[it].slot }) { CoordRow(state.slots[it]) }
    }
}

@Composable
private fun DiagramPanel(state: UiState) {
    val brand = LocalBrand.current
    val status = state.snapshot.status

    Panel("Sơ đồ máy", subtitle = "chạy theo vị trí thật của 3 trục") {
        MachineDiagram(
            geometry = state.geometry,
            slots = state.slots,
            status = status,
            selected = state.selectedSlot,
        )
        Text(
            "Nhìn từ phía trước: ngang là trục X, dọc là trục Z, thanh xoay ở đầu " +
                "công tác là góc lật trục Y. Mỗi ô chia đôi — nửa trên là dãy phải, " +
                "nửa dưới là dãy trái. Rổ đang chạy tới sáng vàng, rổ đang chọn viền xanh.",
            style = MaterialTheme.typography.labelSmall,
            color = brand.muted,
        )
    }
}

@Composable
private fun TableHeader(count: Int) {
    Panel("Bảng tọa độ", subtitle = "$count rổ") {
        Row(Modifier.fillMaxWidth()) {
            HeadCell("Rổ", 0.9f)
            HeadCell("X (mm)", 1.4f)
            HeadCell("Z (mm)", 1.4f)
            HeadCell("Miệng rổ", 1.4f)
            HeadCell("Bên", 1f)
        }
    }
}

@Composable
private fun CoordRow(row: Slot) {
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 3.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        BodyCell(row.slot.toString(), 0.9f, bold = true)
        BodyCell(row.x.toString(), 1.4f)
        BodyCell(row.z.toString(), 1.4f)
        BodyCell(row.rackZ.toString(), 1.4f)
        BodyCell(if (row.side == "phai") "phải" else "trái", 1f)
    }
}

@Composable
private fun androidx.compose.foundation.layout.RowScope.HeadCell(text: String, weight: Float) {
    Text(
        text,
        style = MaterialTheme.typography.labelSmall,
        color = LocalBrand.current.muted,
        modifier = Modifier.weight(weight),
    )
}

@Composable
private fun androidx.compose.foundation.layout.RowScope.BodyCell(
    text: String,
    weight: Float,
    bold: Boolean = false,
) {
    Text(
        text,
        style = MaterialTheme.typography.bodySmall,
        fontWeight = if (bold) FontWeight.SemiBold else FontWeight.Normal,
        modifier = Modifier.weight(weight),
    )
}
