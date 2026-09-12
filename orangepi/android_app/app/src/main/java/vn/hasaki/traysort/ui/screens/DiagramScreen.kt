// So do may + bang toa do tung ro. Chi de nhin, khong bam duoc gi.
//
// Truoc day day la mat cat 2D ve bang Canvas - dung nhung nhat, va khong ai
// buon mo ra xem. Gio dung dung mo hinh 3D nhu ben web: keo xoay duoc, thay ro
// hai day ro nam truoc/sau nhau chu khong phai mot o chia doi.
package vn.hasaki.traysort.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.core.LocalS
import vn.hasaki.traysort.data.Slot
import vn.hasaki.traysort.ui.LocalPane
import vn.hasaki.traysort.ui.UiState
import vn.hasaki.traysort.ui.parts.Machine3D
import vn.hasaki.traysort.ui.parts.Panel
import vn.hasaki.traysort.ui.theme.LocalBrand

@Composable
fun DiagramScreen(state: UiState, modifier: Modifier = Modifier) {
    val s = LocalS.current

    // Man ngang: mo hinh ben trai, bang toa do ben phai. Doi chieu "may dang o
    // dau" voi "ro nao o toa do nao" khong phai cuon qua cuon lai.
    if (LocalPane.current.wide) {
        Row(
            modifier.fillMaxSize().padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Khung KHONG keo cao het cot. May rong va thap (1250 x 400 mm)
            // nen he so thu nho luon bi be ngang chan; keo khung cao them chi
            // sinh ra mot dai trong duoi mo hinh. Dat ty le khung theo dung
            // hinh dang cua may roi de chu giai vao cho con lai.
            LazyColumn(
                Modifier.weight(1.5f),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                item {
                    Panel(title = s.machineDiagram, subtitle = s.dragToRotate) {
                        Machine3D(
                            geometry = state.geometry,
                            slots = state.slots,
                            status = state.snapshot.status,
                            selected = state.selectedSlot,
                            modifier = Modifier.fillMaxWidth().aspectRatio(1.75f),
                        )
                        Text(
                            s.diagramNote,
                            style = MaterialTheme.typography.labelSmall,
                            color = LocalBrand.current.muted,
                        )
                    }
                }
            }
            LazyColumn(Modifier.weight(1f)) {
                item { CoordTable(state.slots) }
            }
        }
        return
    }

    LazyColumn(
        modifier.fillMaxWidth(),
        contentPadding = PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Panel(title = s.machineDiagram, subtitle = s.dragToRotate) {
                Machine3D(
                    geometry = state.geometry,
                    slots = state.slots,
                    status = state.snapshot.status,
                    selected = state.selectedSlot,
                    modifier = Modifier.fillMaxWidth().aspectRatio(1.55f),
                )
                Text(
                    s.diagramNote,
                    style = MaterialTheme.typography.labelSmall,
                    color = LocalBrand.current.muted,
                )
            }
        }
        item { CoordTable(state.slots) }
    }
}

/**
 * Ca dau bang va than bang nam trong CUNG mot Panel, cung mot Column - nen
 * chung dung chung mot luoi cot, khong the lech nhau. Truoc day dau bang o
 * trong Panel con tung dong o ngoai, moi ben mot muc padding khac nhau, thanh
 * ra cot so khong bao gio thang hang.
 *
 * Cot so canh PHAI va dung chu so deu be (tabular figures): "1150.0" va "200.0"
 * moi thang cot voi nhau, mat quet doc mot phat la so sanh duoc.
 */
@Composable
private fun CoordTable(slots: List<Slot>) {
    val brand = LocalBrand.current
    val s = LocalS.current

    Panel(title = s.coordTable, subtitle = s.slotCount(slots.size)) {
        Column {
            Row(Modifier.fillMaxWidth().padding(bottom = 8.dp)) {
                HeadCell(s.colSlot, 0.7f, TextAlign.Start)
                HeadCell("X (mm)", 1.2f, TextAlign.End)
                HeadCell("Z (mm)", 1.2f, TextAlign.End)
                HeadCell(s.colMouth, 1.2f, TextAlign.End)
                HeadCell(s.colSide, 0.8f, TextAlign.End)
            }
            HorizontalDivider(color = brand.line)
            slots.forEach { row ->
                Row(
                    Modifier.fillMaxWidth().padding(vertical = 7.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    BodyCell(row.slot.toString(), 0.7f, TextAlign.Start, bold = true)
                    BodyCell(fmt(row.x), 1.2f, TextAlign.End)
                    BodyCell(fmt(row.z), 1.2f, TextAlign.End)
                    BodyCell(fmt(row.rackZ), 1.2f, TextAlign.End)
                    BodyCell(
                        if (row.side == "phai") s.sideRightLower else s.sideLeftLower,
                        0.8f,
                        TextAlign.End,
                    )
                }
                HorizontalDivider(color = brand.line.copy(alpha = 0.45f))
            }
        }
    }
}

private fun fmt(value: Float): String = "%.1f".format(value)

@Composable
private fun androidx.compose.foundation.layout.RowScope.HeadCell(
    text: String,
    weight: Float,
    align: TextAlign,
) {
    Text(
        text,
        style = MaterialTheme.typography.labelSmall,
        color = LocalBrand.current.muted,
        textAlign = align,
        modifier = Modifier.weight(weight),
    )
}

@Composable
private fun androidx.compose.foundation.layout.RowScope.BodyCell(
    text: String,
    weight: Float,
    align: TextAlign,
    bold: Boolean = false,
) {
    Text(
        text,
        style = MaterialTheme.typography.bodySmall,
        fontWeight = if (bold) FontWeight.SemiBold else FontWeight.Normal,
        textAlign = align,
        modifier = Modifier.weight(weight),
    )
}
