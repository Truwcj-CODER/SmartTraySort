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
import vn.hasaki.traysort.core.Lang
import vn.hasaki.traysort.core.LocalS
import vn.hasaki.traysort.core.derivedLabel
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.staggeredgrid.StaggeredGridItemSpan
import androidx.compose.material3.TextButton
import kotlinx.coroutines.delay
import vn.hasaki.traysort.core.Field
import vn.hasaki.traysort.core.FieldGroup
import vn.hasaki.traysort.core.GEOMETRY_GROUPS
import vn.hasaki.traysort.core.SETUP_GROUPS
import vn.hasaki.traysort.core.TUNING_GROUPS
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
    val s = LocalS.current
    val lang = s.lang
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
        // Thu tu: khung suon truoc, roi den kich thuoc ro va toc do - nhung
        // thu hay sua - dat sat ngay tren nut Luu. Khong dan tieu de "dat mot
        // lan" / "hay chinh" len man: do la cach XEP, khong phai lenh cho nguoi
        // dung; ai muon sua bao nhieu lan la viec cua ho.
        // Nhom nhieu o thi cho chiem tron dong - co du be ngang moi dan ngang
        // duoc. Nhom it o van nam trong luoi so le nhu cu.
        SETUP_GROUPS.forEach { group ->
            item(key = group.vi, span = StaggeredGridItemSpan.FullLine) {
                FieldPanel(group, draft)
            }
        }

        TUNING_GROUPS.forEach { group ->
            item(key = group.vi, span = StaggeredGridItemSpan.FullLine) {
                FieldPanel(group, draft)
            }
        }

        item(span = StaggeredGridItemSpan.FullLine) {
            Panel(s.saveConfig, subtitle = s.slotCount(state.plan.slots)) {
                // Cau giai thich dat TREN nut. De duoi nut thi khong ai doc, va
                // dung cai hieu nham can go - tuong phai bam them mot buoc nua
                // moi xuong toi PLC - lai nam o cau do.
                Text(
                    s.saveNote,
                    style = MaterialTheme.typography.labelSmall,
                    color = brand.muted,
                )
                Button(
                    onClick = { readDraft(draft)?.let(vm::saveGeometry) },
                    enabled = idle,
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                ) { Text(s.saveConfig, fontWeight = FontWeight.Bold) }

                // Ket qua lan Luu gan nhat, ngay tai cho bam. Truoc day no chi
                // vao tab Nhat ky - nguoi dung dang o day bam Luu roi khong biet
                // toa do co xuong toi PLC hay khong.
                // Thanh cong thi hien 4 giay roi tu tat. That bai thi giu.
                LaunchedEffect(state.pushOk) {
                    if (state.pushOk == true) {
                        delay(4000)
                        vm.clearPushResult()
                    }
                }

                when {
                    !idle -> Banner(s.saving, LogLevelTone.WARN)
                    state.pushOk == true -> Banner(s.pushDone, LogLevelTone.OK)
                    state.pushOk == false ->
                        Banner(s.pushFailed(state.pushNote.orEmpty()), LogLevelTone.ERROR)
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        s.pushAgainNote,
                        style = MaterialTheme.typography.labelSmall,
                        color = brand.muted,
                        modifier = Modifier.weight(1f),
                    )
                    Spacer(Modifier.width(8.dp))
                    TextButton(onClick = vm::pushTable, enabled = idle) {
                        Text(s.pushAgain)
                    }
                }
            }
        }

        // Toc do vuot tran PTO khong lam bo cuc sai nen server de rieng, nhung
        // nguoi dung chi can biet "co gi chua on" - hien chung mot cho.
        if (state.problems.isNotEmpty() || state.speedWarnings.isNotEmpty()) {
            item {
                Panel(s.badConfig) {
                    state.problems.forEach { Banner(it, LogLevelTone.WARN) }
                    state.speedWarnings.forEach { Banner(it, LogLevelTone.WARN) }
                }
            }
        }

        item(span = StaggeredGridItemSpan.FullLine) {
            Panel(s.derivedTitle) {
                // Bang nay co hai loai so tron lan: mot loai ta BO CUC (so ro,
                // buoc ngang...), mot loai la quy doi CUA TUNG TRUC. Truoc day
                // do het vao mot luoi chia deu, nen X/Z/Y roi moi hang mot cho,
                // doc phai do tim. Gio tach: bo cuc mot hang tren, con moi truc
                // MOT COT - doc doc mot cot la tron mot truc.
                val byKey = state.derived.toMap()
                val axes = listOf("x", "z", "y")
                val metrics = listOf(
                    listOf("x_pulses_per_mm", "z_pulses_per_mm", "y_pulses_per_degree"),
                    listOf("x_pulses_full_travel", "z_pulses_full_travel", "y_pulses_full_range"),
                    listOf("x_max_velocity_mm_s", "z_max_velocity_mm_s", "y_max_velocity_deg_s"),
                )
                val axisKeys = metrics.flatten().toSet()
                val layout = state.derived.filter { it.first !in axisKeys }

                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    // --- phan bo cuc ---
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        layout.forEach { (key, value) ->
                            DerivedTile(derivedLabel(key, lang), value, Modifier.weight(1f))
                        }
                    }

                    // --- phan tung truc, moi truc mot cot ---
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        axes.forEachIndexed { col, axis ->
                            Column(
                                Modifier.weight(1f),
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                Text(
                                    s.axisName(axis),
                                    style = MaterialTheme.typography.labelMedium,
                                    fontWeight = FontWeight.Bold,
                                    color = brand.muted,
                                )
                                metrics.forEach { line ->
                                    val key = line[col]
                                    DerivedTile(
                                        (derivedLabel(key, lang)).substringAfter("— "),
                                        byKey[key].orEmpty(),
                                        Modifier.fillMaxWidth(),
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        /* ---------------------------------------------------------- hieu chinh */
        // Dat NGAY DUOI bang quy doi: bang do la cho nguoi dung nhin ra con so
        // vo ly, va day la cho sua no. De xa nhau thi thay lech mot dang roi
        // phai di tim cho chinh.
        item(span = StaggeredGridItemSpan.FullLine) {
            CalibrationPanel(state, vm)
        }

        /* ------------------------------------------------------------- chay tay */
        // Chay tay va Jog la MOT viec: can chinh may bang tay. De hai panel roi
        // thi luoi so le nem chung sang hai cot khac nhau, moi ben mot khoang
        // trong. Gop lai, chiem tron dong, chia deu hai nua.
        item(span = StaggeredGridItemSpan.FullLine) {
            Panel(s.manual, subtitle = s.manualSubtitle) {
                Text(
                    s.manualNote,
                    style = MaterialTheme.typography.labelSmall,
                    color = brand.muted,
                )
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    Column(
                        Modifier.weight(1f),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) { ManualControls(state, vm) }
                    Column(
                        Modifier.weight(1f),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) { JogPad(vm) }
                }
            }
        }

        item {
            Panel(s.danger) {
                OutlinedButton(
                    onClick = { confirmReset = true },
                    enabled = idle,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(s.wipeStock, color = brand.danger) }
            }
            Spacer(Modifier.height(8.dp))
        }
    }

    if (confirmReset) {
        AlertDialog(
            onDismissRequest = { confirmReset = false },
            title = { Text(s.wipeAsk) },
            text = { Text(s.wipeWarn(state.summary.slotCount)) },
            confirmButton = {
                TextButton(onClick = { confirmReset = false; vm.resetInventory() }) {
                    Text(s.wipeYes, color = brand.danger)
                }
            },
            dismissButton = { TextButton(onClick = { confirmReset = false }) { Text(s.cancel) } },
        )
    }
}


// Do ti le that cua mot truc roi moi ghi vao cau hinh.
//
// Ba buoc tach han, va thu tu la co chu y: chon truc -> chay thu -> do -> tinh
// thu -> luu. Nut Luu chi sang len sau khi da co ket qua tinh, nen khong ai ghi
// duoc mot con so chua tung do.
@Composable
private fun CalibrationPanel(state: UiState, vm: AppViewModel) {
    val brand = LocalBrand.current
    val s = LocalS.current
    val idle = state.running == null

    var axis by remember { mutableStateOf("y") }
    var target by remember { mutableStateOf("") }
    var measured by remember { mutableStateOf("") }

    val test = state.calTest?.takeIf { it.axis == axis }
    val result = state.calibration?.takeIf { it.axis == axis }
    val unit = if (axis == "y") "°" else "mm"

    Panel(s.calTitle, subtitle = s.calSubtitle) {
        Text(s.calNote, style = MaterialTheme.typography.labelSmall, color = brand.muted)

        // --- chon truc ---
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("x", "z", "y").forEach { name ->
                val picked = name == axis
                val pick = {
                    axis = name
                    target = ""
                    measured = ""
                    vm.clearCalibration()
                }
                if (picked) {
                    Button(onClick = pick, modifier = Modifier.weight(1f)) { Text(s.axisName(name)) }
                } else {
                    OutlinedButton(onClick = pick, modifier = Modifier.weight(1f)) {
                        Text(s.axisName(name))
                    }
                }
            }
        }

        // --- buoc 1: chay thu mot doan da biet ---
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            NumberBox("${s.calTarget} ($unit)", target, { target = it }, Modifier.weight(1f))
            Button(
                onClick = { vm.calibrationTest(axis, target.toDoubleOrNull() ?: return@Button) },
                enabled = idle && target.toDoubleOrNull() != null,
            ) { Text(s.calRun) }
        }

        if (test == null) {
            Text(s.calNotYet, style = MaterialTheme.typography.labelSmall, color = brand.muted)
            return@Panel
        }

        Text(
            s.calCommanded(
                formatValue(test.from, false),
                formatValue(test.target, false),
                formatValue(test.commanded, false),
                unit,
            ),
            style = MaterialTheme.typography.labelSmall,
            color = brand.muted,
        )

        // --- buoc 2: go so do duoc, tinh thu ---
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            NumberBox("${s.calMeasured} ($unit)", measured, { measured = it }, Modifier.weight(1f))
            Button(
                onClick = { vm.calibrationPreview(measured.toDoubleOrNull() ?: return@Button) },
                enabled = idle && measured.toDoubleOrNull() != null,
            ) { Text(s.calPreview) }
        }

        if (result == null) return@Panel

        // --- ket qua ---
        if (result.onTarget) {
            Banner(s.calOnTarget, LogLevelTone.OK)
        } else {
            val factor = formatValue(
                if (result.errorFactor > 1) result.errorFactor else 1.0 / result.errorFactor,
                false,
            )
            Banner(
                if (result.errorFactor > 1) s.calOffBy(factor) else s.calOverBy(factor),
                LogLevelTone.WARN,
            )
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    s.calNow,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = brand.muted,
                )
                DerivedTile(s.calPerUnit, formatValue(result.current.pulsesPerUnit, false), Modifier.fillMaxWidth())
                DerivedTile(s.calFullRange, result.current.pulsesFullRange.toString(), Modifier.fillMaxWidth())
                DerivedTile(s.calCeiling, formatValue(result.current.maxVelocity, false), Modifier.fillMaxWidth())
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    s.calProposed,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = brand.muted,
                )
                DerivedTile(s.calPerUnit, formatValue(result.proposed.pulsesPerUnit, false), Modifier.fillMaxWidth())
                DerivedTile(s.calFullRange, result.proposed.pulsesFullRange.toString(), Modifier.fillMaxWidth())
                DerivedTile(s.calCeiling, formatValue(result.proposed.maxVelocity, false), Modifier.fillMaxWidth())
            }
        }

        result.gearRatio?.let {
            Text(
                s.calGearRatio(formatValue(it, false)),
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
            )
        }

        // Cau nay la ket qua THAT SU cua ca viec hieu chinh: so phai go sang
        // TIA. Server khong ghi ti le xuong PLC duoc, nen bo qua dong nay la
        // may van chay y nhu cu.
        Banner(result.tiaNote, LogLevelTone.WARN)
        result.warnings.forEach { Banner(it, LogLevelTone.WARN) }

        if (state.calApplied) {
            Banner(s.calApplied, LogLevelTone.OK)
        } else if (!result.onTarget) {
            Button(
                onClick = { vm.calibrationApply(measured.toDoubleOrNull() ?: return@Button) },
                enabled = idle && measured.toDoubleOrNull() != null,
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) { Text(s.calApply, fontWeight = FontWeight.Bold) }
        }
    }
}


// Mot nhom o nhap. Truoc day doan nay viet thang trong vong lap; tach ra vi gio
// co hai vong lap goi no (khai mot lan / hay chinh).
@Composable
private fun DerivedTile(label: String, value: String, modifier: Modifier = Modifier) {
    val brand = LocalBrand.current
    Column(
        modifier
            .clip(RoundedCornerShape(10.dp))
            .background(brand.surfaceAlt)
            .padding(horizontal = 10.dp, vertical = 8.dp),
    ) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = brand.muted, maxLines = 2)
        Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold, maxLines = 1)
    }
}

@Composable
private fun FieldBox(
    field: Field,
    draft: MutableMap<String, String>,
    modifier: Modifier = Modifier,
) {
    OutlinedTextField(
        value = draft[field.key].orEmpty(),
        onValueChange = { draft[field.key] = it },
        label = { Text(field.label(LocalS.current.lang), maxLines = 1) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(
            keyboardType = if (field.integer) KeyboardType.Number else KeyboardType.Decimal,
        ),
        modifier = modifier.fillMaxWidth(),
    )
}

@Composable
private fun FieldPanel(group: FieldGroup, draft: MutableMap<String, String>) {
    val brand = LocalBrand.current
    val s = LocalS.current
    val lang = s.lang
    Panel(group.legend(lang)) {
        group.note(lang)?.let {
            Text(it, style = MaterialTheme.typography.labelSmall, color = brand.muted)
        }

        // O nhap XEP NGANG CHIA DEU, khong phai moi o mot dong. Bay doc thi mot
        // nhom bay o (X xung/vong, X mm/vong, Z..., Y...) keo panel dai ngoang,
        // trong khi chung von la ba cot X | Z | Y doc ngang mot phat la xong.
        //
        // So cot do BE NGANG THAT quyet dinh, khong dat cung: cung mot panel
        // nam o cot hep hay chiem tron dong deu xep dung.
        val gap = 8.dp
        val editable = group.fields.filter { !it.readOnly }

        // Nhom co stackBy: xep theo COT, moi cot mot cum. Vi du Thong so co khi
        // la ba cot X | Z | Y, moi cot hai o tren duoi nhau - doc mot cot la
        // thay tron mot truc. De luoi tu chia ngang thi X va Z bi tron chung
        // hang, mat luon cai cum.
        if (group.stackBy > 0) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(gap),
            ) {
                editable.chunked(group.stackBy).forEach { column ->
                    Column(
                        Modifier.weight(1f),
                        verticalArrangement = Arrangement.spacedBy(gap),
                    ) {
                        column.forEach { field -> FieldBox(field, draft) }
                    }
                }
            }
            return@Panel
        }

        // Truong khong sua duoc: hien thanh mot dong chu ngay duoi cac o lien
        // quan, de nguoi nhap biet tran o dau ma khong go qua.
        group.fields.filter { it.readOnly }.forEach { field ->
            Text(
                "${field.label(lang)}: ${draft[field.key].orEmpty()} — " +
                    if (lang == Lang.VI) "khai trong TIA, chỉ để đối chiếu" else "set in TIA, shown for reference",
                style = MaterialTheme.typography.labelSmall,
                color = brand.muted,
            )
        }

        if (editable.isEmpty()) return@Panel

        BoxWithConstraints {
            // Do theo NHAN chu khong theo o nhap. Nhan la cau tieng Viet co
            // don vi ("X: tốc độ ngang (mm/s)"), dai hon o so nhieu; lay 168 dp
            // thi chia duoc 6 cot nhung nhan cut mat duoi.
            val minField = 230.dp
            val n = editable.size
            // Nhet toi da duoc bao nhieu o mot hang.
            val fit = (((maxWidth + gap) / (minField + gap)).toInt()).coerceIn(1, n)
            // Roi CHIA DEU ra tung do hang. Lay thang "fit" thi 7 o ra 6+1, 3 o
            // ra 2+1 - hang cuoi cut mot mau, chua mot lo trong canh no. Tinh so
            // hang truoc roi chia nguoc lai thi 7 o ra 4+3, 3 o ra 3, deu nhau.
            val rows = ((n + fit - 1) / fit).coerceAtLeast(1)
            val cols = (n + rows - 1) / rows

            Column(verticalArrangement = Arrangement.spacedBy(gap)) {
                editable.chunked(cols).forEach { line ->
                    Row(horizontalArrangement = Arrangement.spacedBy(gap)) {
                        line.forEach { field ->
                            FieldBox(field, draft, Modifier.weight(1f))
                        }
                        // Hang cuoi thieu o thi chen cho trong, de cac o con lai
                        // khong bi keo gian ra rong hon hang tren.
                        repeat(cols - line.size) { Spacer(Modifier.weight(1f)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun ColumnScope.ManualControls(state: UiState, vm: AppViewModel) {
    val brand = LocalBrand.current
    val idle = state.running == null
    val hasSlot = state.selectedSlot != null
    val s = LocalS.current

    var moveX by remember { mutableStateOf("0") }
    var moveZ by remember { mutableStateOf("0") }
    var angle by remember { mutableStateOf("0") }

    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilledTonalButton(onClick = vm::gotoSlot, enabled = hasSlot && idle, modifier = Modifier.weight(1f)) {
                Text(s.gotoSlot)
            }
            FilledTonalButton(onClick = vm::tiltSlot, enabled = hasSlot && idle, modifier = Modifier.weight(1f)) {
                Text(s.tiltOnly)
            }
            OutlinedButton(onClick = vm::teachSlot, enabled = hasSlot && idle, modifier = Modifier.weight(1f)) {
                Text("Teach")
            }
        }
        Text(
            state.selectedSlot?.let { s.workingOnSlot(it) } ?: s.pickSlotFirst,
            style = MaterialTheme.typography.labelSmall,
            color = brand.muted,
        )

        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            NumberBox(s.colX, moveX, { moveX = it }, Modifier.weight(1f))
            NumberBox(s.colZ, moveZ, { moveZ = it }, Modifier.weight(1f))
            Button(
                onClick = { vm.moveTo(moveX.toDoubleOrNull() ?: return@Button, moveZ.toDoubleOrNull() ?: return@Button) },
                enabled = idle,
            ) { Text(s.goTo) }
        }

        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            NumberBox(s.tiltAngleBox, angle, { angle = it }, Modifier.weight(1f))
            Button(
                onClick = { vm.tiltTo(angle.toDoubleOrNull() ?: return@Button) },
                enabled = idle,
        ) { Text(s.tiltTo) }
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
