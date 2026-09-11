// So do may nhin tu truoc, ve bang toa do that cua ba truc.
//
// Ben web dung mo hinh 3D; tren dien thoai man hinh nho va pin co han, nen ve
// mot mat cat 2D: giup nguoi van hanh doi chieu "may dang o dau" voi "ro nao
// dang sang" trong mot cai liec, ma khong ton GPU.
//
// Truc X chay ngang, truc Z chay doc, truc Y la goc lat cua khay - ve bang mot
// thanh xoay quanh dau cong tac.
package vn.hasaki.traysort.ui.parts

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import vn.hasaki.traysort.data.GeometryMap
import vn.hasaki.traysort.data.PlcStatus
import vn.hasaki.traysort.data.Slot
import vn.hasaki.traysort.ui.LocalPane
import vn.hasaki.traysort.ui.theme.LocalBrand

private const val PAD = 26f

@Composable
fun MachineDiagram(
    geometry: GeometryMap,
    slots: List<Slot>,
    status: PlcStatus?,
    selected: Int?,
    modifier: Modifier = Modifier,
) {
    val brand = LocalBrand.current
    val scheme = MaterialTheme.colorScheme
    val measurer = rememberTextMeasurer()
    // Man rong thi khung ve to ra, so ro phai to theo khong thi khong doc noi.
    val labelSize = if (LocalPane.current.wide) 13.sp else 9.sp

    val xTravel = (geometry["x_travel"] ?: 1300.0).toFloat().coerceAtLeast(1f)
    val zTravel = (geometry["z_travel"] ?: 400.0).toFloat().coerceAtLeast(1f)
    val basketLength = (geometry["basket_length"] ?: 90.0).toFloat()
    val basketHeight = (geometry["basket_height"] ?: 90.0).toFloat()
    val trayLength = (geometry["tray_length"] ?: 200.0).toFloat()

    // Chay theo vi tri that nhung co lam muot, khong thi moi ban tin la giat mot cai.
    val headX by animateFloatAsState(
        (status?.x ?: 0f).coerceIn(0f, xTravel), tween(220), label = "head-x",
    )
    val headZ by animateFloatAsState(
        (status?.z ?: 0f).coerceIn(0f, zTravel), tween(220), label = "head-z",
    )
    val tilt by animateFloatAsState(status?.y ?: 0f, tween(220), label = "head-y")

    val activeSlot = if (status?.busy == true && status.slot > 0) status.slot else null

    Box(
        modifier
            .fillMaxWidth()
            .aspectRatio(1.55f)
            .clip(RoundedCornerShape(12.dp))
            .background(brand.surfaceAlt),
    ) {
        Canvas(Modifier.fillMaxWidth().aspectRatio(1.55f)) {
            val plotW = size.width - PAD * 2
            val plotH = size.height - PAD * 2
            // Mot he quy chieu duy nhat cho ca hinh: mm -> pixel.
            val sx = plotW / xTravel
            val sz = plotH / zTravel
            fun px(mmX: Float) = PAD + mmX * sx
            fun py(mmZ: Float) = PAD + plotH - mmZ * sz

            drawFrame(brand.line, scheme.outline)

            // --- gian ro ---
            slots.forEach { row ->
                val w = basketLength * sx
                val h = basketHeight * sz
                val left = px(row.x) - w / 2
                val top = py(row.rackZ)
                val fill = when {
                    row.slot == activeSlot -> brand.warn
                    row.slot == selected -> scheme.primary
                    row.ratio >= 1f -> brand.danger
                    row.ratio >= 0.7f -> brand.warn
                    else -> brand.ok
                }

                // Hai day ro nam truoc va sau duong ray - nhin tu phia truoc thi
                // chung che nhau. Nen moi o chia doi theo chieu cao: nua tren la
                // day phai, nua duoi la day trai. Khong dung ve hinh hoc, nhung
                // doc duoc ca hai so ro trong mot cai liec.
                val half = h / 2 - 1f
                val boxTop = if (row.dir > 0) top else top + h / 2 + 1f
                val strong = row.slot == activeSlot || row.slot == selected

                drawRect(
                    color = fill.copy(alpha = 0.18f),
                    topLeft = Offset(left, boxTop),
                    size = Size(w, half),
                )
                // Muc day: to dan tu day ro len.
                if (row.ratio > 0f) {
                    val fh = half * row.ratio.coerceIn(0f, 1f)
                    drawRect(
                        color = fill.copy(alpha = 0.55f),
                        topLeft = Offset(left, boxTop + half - fh),
                        size = Size(w, fh),
                    )
                }
                drawRect(
                    color = fill,
                    topLeft = Offset(left, boxTop),
                    size = Size(w, half),
                    style = Stroke(width = if (strong) 2.5f else 1.0f),
                )
                label(measurer, row.slot.toString(), Offset(left + w / 2, boxTop + half / 2),
                      brand.muted, labelSize)
            }

            // --- ray truc X va cot truc Z ---
            val hx = px(headX)
            val hz = py(headZ)
            drawLine(scheme.outline, Offset(PAD, PAD + plotH), Offset(PAD + plotW, PAD + plotH), 3f)
            drawLine(scheme.outline.copy(alpha = 0.6f), Offset(hx, PAD), Offset(hx, PAD + plotH), 2f)

            // --- dau cong tac + khay dang mang ---
            val trayW = trayLength * sx
            rotate(degrees = -tilt, pivot = Offset(hx, hz)) {
                drawRect(
                    color = scheme.primary,
                    topLeft = Offset(hx - trayW / 2, hz - 7f),
                    size = Size(trayW, 14f),
                )
            }
            drawCircle(scheme.primary, radius = 7f, center = Offset(hx, hz))
            drawCircle(scheme.onSurface.copy(alpha = 0.35f), radius = 7f, center = Offset(hx, hz), style = Stroke(1.5f))
        }
    }
}

private fun DrawScope.drawFrame(line: Color, outline: Color) {
    drawRect(
        color = line,
        topLeft = Offset(PAD, PAD),
        size = Size(size.width - PAD * 2, size.height - PAD * 2),
        style = Stroke(width = 1f),
    )
    drawLine(outline.copy(alpha = 0.35f), Offset(PAD, PAD), Offset(PAD, size.height - PAD), 1f)
}

private fun DrawScope.label(
    measurer: TextMeasurer,
    text: String,
    center: Offset,
    color: Color,
    size: androidx.compose.ui.unit.TextUnit,
) {
    val layout = measurer.measure(text, TextStyle(fontSize = size, color = color))
    drawText(layout, topLeft = Offset(center.x - layout.size.width / 2, center.y - layout.size.height / 2))
}
