// Luoi ro. So hang va so cot khong co dinh - server tinh ra bao nhieu thi ve
// bay nhieu, giong ben web.
package vn.hasaki.traysort.ui.parts

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.data.Slot
import vn.hasaki.traysort.ui.theme.LocalBrand

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun TrayGrid(
    slots: List<Slot>,
    selected: Int?,
    active: Int?,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val brand = LocalBrand.current

    if (slots.isEmpty()) {
        Text(
            "chưa có bố cục — kiểm tra kết nối hoặc cấu hình kích thước giàn khay",
            style = MaterialTheme.typography.bodySmall,
            color = brand.muted,
            modifier = modifier,
        )
        return
    }

    // Gom theo (hang, ben) dung thu tu server tra ve - khong sap xep lai.
    val groups = slots.groupBy { it.row to it.side }

    Column(modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        groups.forEach { (key, rows) ->
            val (rowIndex, side) = key
            Column(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(brand.surfaceAlt)
                    .padding(8.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text(
                    "${if (side == "phai") "Phải" else "Trái"} — hàng ${rowIndex + 1}",
                    style = MaterialTheme.typography.labelSmall,
                    color = brand.muted,
                )
                // O ro CHIA DEU het be ngang thay vi an mot con so co dinh.
                // An so thi hoac chua khit ngon tay tren dien thoai, hoac de lai
                // mot dai trong chet o cuoi hang tren tablet - va roi so cot lai
                // do cau hinh quyet dinh nen khong the doan truoc.
                BoxWithConstraints {
                    val gap = 6.dp
                    val minChip = 92.dp
                    // Nhet het mot hang duoc thi nhet; khong thi chia thanh may
                    // hang deu nhau, hang nao cung day be ngang.
                    val perLine = if (minChip * rows.size + gap * (rows.size - 1) <= maxWidth) {
                        rows.size
                    } else {
                        (((maxWidth + gap) / (minChip + gap)).toInt()).coerceAtLeast(1)
                    }
                    val chipWidth = (maxWidth - gap * (perLine - 1)) / perLine

                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(gap),
                        verticalArrangement = Arrangement.spacedBy(gap),
                        maxItemsInEachRow = perLine,
                    ) {
                        rows.forEach { row ->
                            SlotChip(
                                row = row,
                                selected = row.slot == selected,
                                active = row.slot == active,
                                onClick = { onSelect(row.slot) },
                                modifier = Modifier.width(chipWidth),
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SlotChip(
    row: Slot,
    selected: Boolean,
    active: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val brand = LocalBrand.current
    // Xanh la con cho, vang gan day, do da day - dung nguong voi ben web.
    val tone = when {
        row.ratio >= 1f -> brand.danger
        row.ratio >= 0.7f -> brand.warn
        else -> brand.ok
    }
    val border by animateColorAsState(
        when {
            active -> brand.warn
            selected -> MaterialTheme.colorScheme.primary
            else -> brand.line
        },
        label = "slot-border",
    )

    Column(
        modifier
            .clip(RoundedCornerShape(10.dp))
            .background(MaterialTheme.colorScheme.surface)
            .border(if (selected || active) 2.dp else 1.dp, border, RoundedCornerShape(10.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 8.dp, vertical = 7.dp),
        verticalArrangement = Arrangement.spacedBy(3.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                row.slot.toString(),
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Spacer(Modifier.weight(1f))
            Text(
                "${row.count}/${row.capacity}",
                style = MaterialTheme.typography.labelSmall,
                color = tone,
                fontWeight = FontWeight.SemiBold,
            )
        }

        Text(
            row.code.ifBlank { "—" },
            style = MaterialTheme.typography.labelSmall,
            color = brand.muted,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )

        FillBar(row.ratio, tone)
    }
}

@Composable
private fun FillBar(ratio: Float, color: Color) {
    val brand = LocalBrand.current
    Box(
        Modifier
            .fillMaxWidth()
            .height(4.dp)
            .clip(RoundedCornerShape(2.dp))
            .background(brand.line),
    ) {
        Box(
            Modifier
                .fillMaxWidth(ratio.coerceIn(0f, 1f))
                .height(4.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(color),
        )
    }
}
