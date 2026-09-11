// Ban jog: giu la chay, nha la dung. PLC tu cat sau JogMaxTime neu mat song.
//
// Nut jog khong dung Button thuong: Button chi bao "da bam xong", con o day
// phai biet dung luc ngon tay cham xuong va dung luc no roi ra.
package vn.hasaki.traysort.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.ui.AppViewModel
import vn.hasaki.traysort.ui.parts.Panel
import vn.hasaki.traysort.ui.theme.LocalBrand

@Composable
fun JogPanel(vm: AppViewModel, modifier: Modifier = Modifier) {
    val brand = LocalBrand.current

    // Roi man hinh trong luc dang giu nut thi phai nha ra, khong may chay tiep.
    DisposableEffect(Unit) { onDispose { vm.releaseAllJog() } }

    Panel("Jog tay", modifier = modifier, subtitle = "giữ để chạy") {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Spacer(Modifier.weight(1f))
            JogKey("▲", "z_pos", vm, Modifier.weight(1f))
            Spacer(Modifier.weight(1f))
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            JogKey("◀", "x_neg", vm, Modifier.weight(1f))
            JogKey("▼", "z_neg", vm, Modifier.weight(1f))
            JogKey("▶", "x_pos", vm, Modifier.weight(1f))
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            JogKey("↺ lật trái", "y_neg", vm, Modifier.weight(1f))
            JogKey("lật phải ↻", "y_pos", vm, Modifier.weight(1f))
        }
    }
}

@Composable
private fun RowScope.JogKey(
    label: String,
    direction: String,
    vm: AppViewModel,
    modifier: Modifier = Modifier,
) {
    val brand = LocalBrand.current
    var held by remember { mutableStateOf(false) }

    Box(
        modifier
            .height(54.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(if (held) MaterialTheme.colorScheme.primary else brand.surfaceAlt)
            .border(1.dp, brand.line, RoundedCornerShape(12.dp))
            .pointerInput(direction) {
                detectTapGestures(
                    onPress = {
                        held = true
                        vm.jog(direction, true)
                        // Cho toi khi ngon tay roi ra - ke ca khi keo ra ngoai nut.
                        tryAwaitRelease()
                        held = false
                        vm.jog(direction, false)
                    },
                )
            },
        contentAlignment = Alignment.Center,
    ) {
        Text(
            label,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            color = if (held) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface,
        )
    }
}
