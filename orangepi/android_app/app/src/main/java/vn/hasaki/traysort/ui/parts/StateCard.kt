// Doi con so PLC tra ve thanh cau chu: dang o dau, dang lam gi, lenh cuoi ra sao.
// Cung mot cach dien dat voi renderStateCard() ben app/static/js/ui.js.
package vn.hasaki.traysort.ui.parts

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.core.POSITION_TOLERANCE
import vn.hasaki.traysort.core.RESULT_TEXT
import vn.hasaki.traysort.core.STAGE_NAMES
import vn.hasaki.traysort.core.LocalS
import vn.hasaki.traysort.core.S
import vn.hasaki.traysort.core.stepOf
import vn.hasaki.traysort.data.PlcStatus
import vn.hasaki.traysort.data.Slot
import vn.hasaki.traysort.data.Snapshot
import vn.hasaki.traysort.ui.theme.LocalBrand
import kotlin.math.abs

/** Doi tri so X-Z thanh cau chu: dang o khay nao, o cho cho, hay dang chay. */
fun describeWhere(status: PlcStatus, slots: List<Slot>, s: S): String {
    if (status.busy) {
        return if (status.slot > 0) s.movingToSlot(status.slot) else s.moving
    }

    val near = slots.firstOrNull {
        abs(it.x - status.x) <= POSITION_TOLERANCE && abs(it.z - status.z) <= POSITION_TOLERANCE
    }
    if (near != null) return s.slotNo(near.slot)

    if (abs(status.x) <= POSITION_TOLERANCE && abs(status.z) <= POSITION_TOLERANCE) {
        return s.atPark
    }
    return s.atXZ(status.x.toInt(), status.z.toInt())
}

/** Cau canh bao dang treo tren dau. Null la khong co gi phai noi. */
fun alertFor(status: PlcStatus, s: S): Pair<String, LogLevelTone>? = when {
    status.error -> s.faultBanner(status.errorIdHex, s.errorHint(status.errorIdHex)) to
        LogLevelTone.ERROR
    // Ma 3 chi con danh cho nut DUNG khan.
    status.result == 3 -> s.abortedBanner to LogLevelTone.WARN
    status.result == 6 -> s.hitLimitBanner to LogLevelTone.WARN
    !status.homed -> s.notHomedBanner to LogLevelTone.WARN
    else -> null
}

/** Cau ngan hien canh cham mau tren thanh tieu de. */
fun connectionText(snapshot: Snapshot, s: S): String {
    val status = snapshot.status
    if (!snapshot.online || status == null) {
        return snapshot.lastError?.let { s.lostLink(it) } ?: s.plcOffline
    }
    return when {
        status.error -> s.faultCode(status.errorIdHex)
        status.busy -> s.runningStep(status.step)
        !status.homed -> s.notHomed
        status.ready -> s.ready
        else -> s.noServoPower
    }
}

@Composable
fun StateCard(
    snapshot: Snapshot,
    slots: List<Slot>,
    modifier: Modifier = Modifier,
    compact: Boolean = false,
) {
    val brand = LocalBrand.current
    // Mat ket noi thi ban tin cuoi cung khong con dung nua - coi nhu khong co,
    // de khong cho nao ben duoi lo hien mot con so da cu.
    val status = snapshot.status?.takeIf { snapshot.online }

    val tone = when {
        status == null -> brand.danger
        status.error -> brand.danger
        status.busy -> brand.warn
        status.homed -> brand.ok
        else -> brand.muted
    }

    Column(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(tone.copy(alpha = 0.10f))
            .padding(if (compact) 9.dp else 12.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        val s = LocalS.current
        val where = status?.let { describeWhere(it, slots, s) } ?: "—"
        val phase = status?.let { stepOf(it.step).text } ?: s.lostLinkShort
        val last = status?.let { RESULT_TEXT[it.result] ?: s.resultCode(it.result) } ?: "—"

        // Ban gon: ba muc nam mot dong. Dung trong khung dieu khien thap, cho
        // moi thu vua trong tam mat va bam duoc ma khong phai cuon.
        if (compact) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                InlineState(s.atPosition, where, tone)
                InlineState(s.phase, phase, tone)
                InlineState(s.lastCommand, last, tone)
            }
            return@Column
        }

        StateRow(s.atPosition, where, tone)
        StateRow(s.phase, phase, tone)
        StateRow(s.lastCommand, last, tone)
    }
}

@Composable
private fun InlineState(label: String, value: String, tone: androidx.compose.ui.graphics.Color) {
    val brand = LocalBrand.current
    Column {
        Text(label, style = MaterialTheme.typography.labelSmall, color = brand.muted)
        Text(
            value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            color = tone,
            maxLines = 1,
        )
    }
}

@Composable
private fun StateRow(label: String, value: String, tone: androidx.compose.ui.graphics.Color) {
    val brand = LocalBrand.current
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = brand.muted)
        Spacer(Modifier.width(10.dp))
        Text(
            value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            color = tone,
            textAlign = TextAlign.End,
            modifier = Modifier.weight(1f),
        )
    }
}

/** Nam giai doan cua chu trinh. Xong thi xanh, dang chay thi vang, loi thi do. */
@Composable
fun StageBar(status: PlcStatus?, modifier: Modifier = Modifier) {
    val brand = LocalBrand.current
    val step = stepOf(status?.step ?: 0)
    val activeStage = step.stage

    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        STAGE_NAMES.forEachIndexed { index, name ->
            val state = when {
                status?.error == true -> StageState.ERROR
                activeStage == null -> if (status?.result == 2 && status.busy.not()) StageState.DONE else StageState.TODO
                index < activeStage -> StageState.DONE
                index == activeStage -> StageState.ACTIVE
                else -> StageState.TODO
            }
            val color by animateColorAsState(
                when (state) {
                    StageState.ERROR -> brand.danger
                    StageState.DONE -> brand.ok
                    StageState.ACTIVE -> brand.warn
                    StageState.TODO -> brand.line
                },
                label = "stage-$index",
            )

            Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                Box(
                    Modifier
                        .fillMaxWidth()
                        .height(4.dp)
                        .clip(RoundedCornerShape(2.dp))
                        .background(color),
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    name,
                    style = MaterialTheme.typography.labelSmall,
                    color = if (state == StageState.TODO) brand.muted else color,
                    textAlign = TextAlign.Center,
                    maxLines = 2,
                )
            }
        }
    }
}

private enum class StageState { TODO, ACTIVE, DONE, ERROR }
