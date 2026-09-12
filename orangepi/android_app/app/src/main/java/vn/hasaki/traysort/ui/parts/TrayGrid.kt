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
import androidx.compose.foundation.layout.aspectRatio
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
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.data.Slot
import vn.hasaki.traysort.core.LocalS
import vn.hasaki.traysort.ui.LocalPane
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
    val s = LocalS.current

    if (slots.isEmpty()) {
        Text(
            s.noLayout,
            style = MaterialTheme.typography.bodySmall,
            color = brand.muted,
            modifier = modifier,
        )
        return
    }

    // Gom theo (hang, ben) dung thu tu server tra ve - khong sap xep lai.
    val groups = slots.groupBy { it.row to it.side }

    // O ro tren man phai co ti le giong o ro that: be ngang la buoc theo truc X,
    // be cao la buoc theo truc Z. Hai buoc nay khong nam trong cau hinh - chung
    // la so suy ra - nen do thang tu toa do server tra ve. Truoc day o ro la mot
    // hop det 3.3:1 nen trong nhu mot dong danh sach, khong ra cai ro nao.
    val aspect = remember(slots) { cellAspect(slots) }

    // Man ngang: hai nhom canh nhau (Phai hang 1 | Trai hang 1), giong luoi
    // "tray" ben web. Xep bon nhom thanh mot cot doc thi gian khay cao gap doi
    // can thiet - tren tablet la nhom cuoi bi cat mat duoi day man.
    val perRow = if (LocalPane.current.wide) 2 else 1
    val entries = groups.entries.toList()

    Column(modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        entries.chunked(perRow).forEach { line ->
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        line.forEach { (key, rows) ->
            val (rowIndex, side) = key
            Column(
                Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(12.dp))
                    .background(brand.surfaceAlt)
                    .padding(8.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text(
                    s.rowLabel(if (side == "phai") s.sideRight else s.sideLeft, rowIndex + 1),
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

                    // Chia bang weight chu khong dat chieu rong co dinh. Cach cu
                    // tinh chipWidth = (maxWidth - gap*(n-1))/n, cong lai dung
                    // bang maxWidth - lam tron sang pixel le 1 px la FlowRow day
                    // the cuoi xuong dong, thanh ra hang 5 ro hien 4 + 1.
                    Column(verticalArrangement = Arrangement.spacedBy(gap)) {
                        rows.chunked(perLine).forEach { chipLine ->
                            Row(horizontalArrangement = Arrangement.spacedBy(gap)) {
                                chipLine.forEach { row ->
                                    SlotChip(
                                        row = row,
                                        selected = row.slot == selected,
                                        active = row.slot == active,
                                        onClick = { onSelect(row.slot) },
                                        modifier = Modifier.weight(1f).aspectRatio(aspect),
                                    )
                                }
                                // Hang cuoi thieu the thi chen cho trong cho
                                // the con lai khong bi keo gian ra.
                                repeat(perLine - chipLine.size) {
                                    Spacer(Modifier.weight(1f))
                                }
                            }
                        }
                    }
                }
            }
        }
        // Hang cuoi le mot nhom thi chen cho trong, khong keo nhom do rong doi.
        repeat(perRow - line.size) { Spacer(Modifier.weight(1f)) }
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
    // Xanh la con cho, vang gan day, do da day - dung nguong voi ben web, va
    // dung cau chu giai ngay duoi luoi khay. Da co luc doi "day = du don = xanh"
    // nhung the thi chu giai noi nguoc lai voi cai mat nhin thay.
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

/**
 * Ti le be ngang / be cao cua mot o ro, do tu chinh toa do cac ro.
 *
 * buoc X = khoang cach nho nhat giua hai ro khac hoanh do (237.5 mm o cau hinh
 * dang chay), buoc Z = khoang cach nho nhat giua hai hang (180 mm). Chi co mot
 * hang hoac mot cot thi khong do duoc, luc do lay 1.3 - vao khoang ti le cua
 * may nay, va du vuong de con ra hinh cai ro.
 */
private fun cellAspect(slots: List<Slot>): Float {
    fun pitch(values: List<Float>): Float? {
        val sorted = values.distinct().sorted()
        return sorted.zipWithNext { a, b -> b - a }.filter { it > 0.5f }.minOrNull()
    }
    val px = pitch(slots.map { it.x })
    val pz = pitch(slots.map { it.rackZ })
    if (px == null || pz == null) return 1.3f
    return (px / pz).coerceIn(0.8f, 2.4f)
}
