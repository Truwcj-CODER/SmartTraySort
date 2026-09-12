// Ve mot ma QR. ML Kit trong app chi DOC duoc ma, khong ve ra duoc - nen phan
// sinh ma dung ZXing, roi tu ve tung o vuong len Canvas.
//
// Ve bang Canvas thay vi dung Bitmap: mo hoi thoai ra la ve lai o dung kich
// thuoc man dang co, khong phai doan truoc bao nhieu pixel roi phong to len cho
// mo. May quet doc mot ma sac net de hon nhieu.
package vn.hasaki.traysort.ui.parts

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.google.zxing.BarcodeFormat
import com.google.zxing.EncodeHintType
import com.google.zxing.common.BitMatrix
import com.google.zxing.qrcode.QRCodeWriter
import com.google.zxing.qrcode.decoder.ErrorCorrectionLevel

@Composable
fun QrCode(
    text: String,
    modifier: Modifier = Modifier,
    dark: Color = Color.Black,
    light: Color = Color.White,
) {
    // Ma chi doi khi noi dung doi - khong tinh lai moi khung ve.
    val matrix: BitMatrix? = remember(text) {
        if (text.isBlank()) {
            null
        } else {
            runCatching {
                QRCodeWriter().encode(
                    text,
                    BarcodeFormat.QR_CODE,
                    // Kich thuoc thuc do Canvas quyet dinh; o day chi can so o.
                    1,
                    1,
                    mapOf(
                        // Muc M: chiu duoc ban va xuoc mot phan ma van doc duoc,
                        // ma khong lam ma ray qua muc.
                        EncodeHintType.ERROR_CORRECTION to ErrorCorrectionLevel.M,
                        // Tu chua vien trang - vien do Box ben ngoai lo.
                        EncodeHintType.MARGIN to 0,
                        EncodeHintType.CHARACTER_SET to "UTF-8",
                    ),
                )
            }.getOrNull()
        }
    }

    Box(
        modifier
            .clip(RoundedCornerShape(12.dp))
            .background(light)
            // Vien trang quanh ma la bat buoc de may quet tach duoc ma khoi nen.
            .padding(12.dp),
    ) {
        if (matrix == null) return@Box
        Canvas(Modifier.fillMaxSize()) {
            val cells = matrix.width
            // Lam tron xuong pixel nguyen: o le nua pixel thi cac o vuong day
            // nhau, ma bi ray va may quet doc chap chon.
            val cell = kotlin.math.floor(minOf(size.width, size.height) / cells)
            if (cell < 1f) return@Canvas
            val side = cell * cells
            val left = (size.width - side) / 2f
            val top = (size.height - side) / 2f
            for (y in 0 until cells) {
                for (x in 0 until cells) {
                    if (!matrix[x, y]) continue
                    drawRect(
                        color = dark,
                        topLeft = Offset(left + x * cell, top + y * cell),
                        size = Size(cell, cell),
                    )
                }
            }
        }
    }
}
