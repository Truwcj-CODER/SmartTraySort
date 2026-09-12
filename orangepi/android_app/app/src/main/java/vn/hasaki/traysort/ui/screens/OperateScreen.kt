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
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.QrCode2
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
import vn.hasaki.traysort.core.LocalS
import vn.hasaki.traysort.core.stepOf
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.TextButton
import vn.hasaki.traysort.data.OrderDetail
import vn.hasaki.traysort.ui.AppViewModel
import vn.hasaki.traysort.ui.LocalPane
import vn.hasaki.traysort.ui.UiState
import vn.hasaki.traysort.ui.parts.Banner
import vn.hasaki.traysort.ui.parts.Machine3D
import vn.hasaki.traysort.ui.parts.Panel
import vn.hasaki.traysort.ui.parts.QrCode
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
    show3d: Boolean,
    modifier: Modifier = Modifier,
) {
    val pane = LocalPane.current
    val s = LocalS.current
    val status = state.snapshot.status

    if (pane.wide) {
        // Tablet ngang: gian khay ben trai (no to nhat), bang dieu khien ben
        // phai. Hai cot cuon doc lap - dang xem cuoi luoi khay ma van bam
        // duoc nut Dung.
        // Ti le 70/30 la con so canonical supporting-pane cua Android cho khung
        // expanded: gian khay la noi dung chinh, bang dieu khien la khung phu.
        // Truoc day chia 1.35/1 (57/43) nen cot phai qua beo, con luoi khay -
        // thu nguoi van hanh nhin nhieu nhat - bi bop lai.
        //
        // Trong cot phai, nhom nut duoc day xuong DAY man: nguyen tac HMI la gom
        // nut dieu khien o duoi, va tay nguoi dung o duoi man khi cam tablet.
        // Gian khay nam ngang het be tren, an 3 phan chieu cao - do la thu
        // nguoi van hanh nhin nhieu nhat va can rong nhat. 2 phan con lai o
        // duoi: mo hinh 3D ben trai, bang dieu khien ben phai.
        Column(
            modifier.fillMaxSize().padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Canh bao ngang het be tren: day la thu nguoi van hanh phai thay
            // ngay, va o day no khong an cho cua nut lenh ben duoi.
            status?.let { alertFor(it, s) }?.let { (text, tone) -> Banner(text, tone) }

            LazyColumn(
                Modifier.weight(3f),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                // Ton kho tac dong len dung cai ro dang chon, nen no thuoc ve
                // canh luoi khay chu khong phai canh nut chay may.
                item { TrayPanel(state, vm) }
                            }

            Row(
                Modifier.weight(2f),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                if (show3d) {
                    Panel(
                        title = s.model3d,
                        subtitle = s.dragToRotate,
                        // 3D duoc phan rong hon: no la hinh cua ca cai may,
                        // 1250 mm ngang - cang rong cang de nhin ra hinh khoi.
                        modifier = Modifier.weight(2f).fillMaxHeight(),
                    ) {
                        Machine3D(
                            geometry = state.geometry,
                            slots = state.slots,
                            status = status,
                            selected = state.selectedSlot,
                            modifier = Modifier.fillMaxSize(),
                        )
                    }
                }

                // Cot dieu khien: phan doc duoc thi cuon, con Xoa loi + DUNG
                // ghim cung o day va KHONG cuon. Nut dung may khong bao gio
                // duoc phep troi ra ngoai man hay bi cat.
                // KHONG cuon. Truoc day cot nay la LazyColumn nen nut bi day
                // xuong duoi vung nhin, phai cuon moi thay - dung cai nguoi van
                // hanh can bam thi lai la cai bi che. Gio moi thu trong khung
                // dieu khien deu nam trong tam mat cung mot luc: thanh trang
                // thai gon mot dong, bon nut lenh xep luoi 2 cot, DUNG ca hang.
                CyclePanel(state, vm, modifier = Modifier.weight(1f).fillMaxHeight())
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
        item { StopBar(state, vm) }
        item { TrayPanel(state, vm) }
                if (show3d) {
            item {
                Panel(title = s.model3d, subtitle = s.dragToRotate) {
                    Machine3D(
                        geometry = state.geometry,
                        slots = state.slots,
                        status = status,
                        selected = state.selectedSlot,
                        modifier = Modifier.fillMaxWidth().height(320.dp),
                    )
                }
            }
        }
    }
}

/* ----------------------------------------------------------------- chu trinh */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CyclePanel(state: UiState, vm: AppViewModel, modifier: Modifier = Modifier) {
    val brand = LocalBrand.current
    val status = state.snapshot.status
    val hasSlot = state.selectedSlot != null
    val idle = state.running == null
    val wide = LocalPane.current.wide

    val s = LocalS.current

    // Ban rong: bo THE TRANG THAI. Ba tri so X/Y/Z va chip trang thai da nam
    // tren thanh xanh, ngay tam mat - ve lai o day la lap lai ma ton 52 dp,
    // dung bang mot hang nut. Phan rieng cua the la ten buoc thi don vao dong
    // phu cua tieu de, cho do khong ton them chieu cao nao.
    val phase = state.snapshot.status?.let { stepOf(it.step).text }
    val slotText = state.selectedSlot?.let { s.slotNo(it) } ?: s.noSlotPicked

    Panel(
        title = s.cycle,
        subtitle = if (wide && phase != null) "$slotText · $phase" else slotText,
        modifier = modifier,
        fillContentHeight = wide,
    ) {
        if (!wide) StateCard(state.snapshot, state.slots)
        // Dai nam buoc chi ve khi con cho: trong khung dieu khien thap no xuong
        // hai dong va an het cho cua nut.
        if (!wide) StageBar(status)

        // Ban rong: dai canh bao da ve o dau man, khong lap lai o day - no chiem
        // ~55 dp, dung bang mot nut lenh, ma khung nay khong con du cho.
        if (!wide) {
            status?.let { alertFor(it, s) }?.let { (text, tone) -> Banner(text, tone) }
        }

        if (wide) {
            // Nut co chieu cao CO DINH, khong chia weight. Da thu chia weight de
            // "khong bao gio tran": khi dai canh bao hien ra, moi hang co lai con
            // ~25 dp va chu bi cat sach - nam vien thuoc trang tron, khong ai
            // biet nut nao la nut nao.
            //
            // Doi lai: phan bon nut lenh duoc phep cuon khi dai qua thap, con
            // DUNG thi ghim ngoai vung cuon nen luon thay va luon bam duoc.
            Column(
                Modifier.weight(1f).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                // "Chay tu dong" phai o DAY, canh luoi khay. Da thu chuyen sang
                // khoi Chay tay ben Cai dat cho dung "duong phu", nhung nut nay
                // can CHON KHAY truoc - ma luoi khay lai nam o tab nay. Chon o
                // mot tab roi chay sang tab khac bam la vo ly.
                //
                // Chi ha xuong ngang hang cac nut khac, khong de to nhat nua:
                // ngoai san xuat quet ma la may tu chay, khong ai bam no.
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = vm::runSlot,
                        enabled = hasSlot && idle,
                        modifier = Modifier.weight(1f).height(TOUCH),
                    ) { Text(s.autoRun, maxLines = 1) }
                    FilledTonalButton(
                        onClick = vm::park,
                        enabled = idle,
                        modifier = Modifier.weight(1f).height(TOUCH),
                    ) { Text(s.park, maxLines = 1) }
                }
                // Hai nut HOME di lien nhau, LIMIT dung canh de thay ngay la hai
                // cho khac nhau: LIMIT co dinh theo co khi, HOME tu dat.
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilledTonalButton(
                        onClick = vm::parkHere,
                        enabled = idle,
                        modifier = Modifier.weight(1f).height(TOUCH),
                    ) { Text(s.parkHere, maxLines = 1) }
                    FilledTonalButton(
                        onClick = vm::home,
                        enabled = idle,
                        modifier = Modifier.weight(1f).height(TOUCH),
                    ) { Text(s.home, maxLines = 1) }
                }
                OutlinedButton(
                    onClick = vm::resetFault,
                    enabled = idle,
                    modifier = Modifier.fillMaxWidth().height(TOUCH),
                ) { Text(s.clearFault, maxLines = 1) }
            }
            // DUNG ghim rieng ca hang, ngoai vung cuon - luon thay, luon bam duoc.
            Button(
                onClick = vm::emergencyStop,
                colors = ButtonDefaults.buttonColors(containerColor = brand.danger),
                modifier = Modifier.fillMaxWidth().height(TOUCH),
            ) { Text(s.stop, fontWeight = FontWeight.Bold, maxLines = 1) }
            return@Panel
        }

        Spacer(Modifier.height(2.dp))

        FilledTonalButton(
            onClick = vm::park,
            enabled = idle,
            modifier = Modifier.fillMaxWidth().height(TOUCH),
        ) { Text(s.park, maxLines = 1) }
        FilledTonalButton(
            onClick = vm::parkHere,
            enabled = idle,
            modifier = Modifier.fillMaxWidth().height(TOUCH),
        ) { Text(s.parkHere, maxLines = 1) }
        FilledTonalButton(
            onClick = vm::home,
            enabled = idle,
            modifier = Modifier.fillMaxWidth().height(TOUCH),
        ) { Text(s.home, maxLines = 1) }
    }
}

/** Xoa loi + DUNG. Ghim day khung phai, khong nam trong vung cuon. */
@Composable
private fun StopBar(state: UiState, vm: AppViewModel) {
    val brand = LocalBrand.current
    val s = LocalS.current
    val idle = state.running == null

    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedButton(
            onClick = vm::resetFault,
            enabled = idle,
            modifier = Modifier.weight(1f).height(TOUCH),
        ) { Text(s.clearFault, maxLines = 1) }
        Button(
            onClick = vm::emergencyStop,
            colors = ButtonDefaults.buttonColors(containerColor = brand.danger),
            modifier = Modifier.weight(1f).height(TOUCH),
        ) { Text(s.stop, fontWeight = FontWeight.Bold, maxLines = 1) }
    }
}

/* ----------------------------------------------------------------- gian khay */
@Composable
private fun TrayPanel(state: UiState, vm: AppViewModel) {
    val brand = LocalBrand.current
    val status = state.snapshot.status

    val s = LocalS.current

    Panel(
        title = s.trayRack,
        subtitle = with(state.summary) {
            s.rackSummary(totalItems, totalCapacity, fullSlots, emptySlots)
        },
    ) {
        TrayGrid(
            slots = state.slots,
            selected = state.selectedSlot,
            active = if (status?.busy == true) status.slot else null,
            // An lan nua vao ro dang chon thi BO chon - bang ke don bien mat.
            // Khong co cach nao khac de go chon, ma dinh mai mot ro thi dong
            // duoi luoi khay khong bao gio quay lai duoc cau goi y.
            onSelect = { slot ->
                vm.selectSlot(if (state.selectedSlot == slot) null else slot)
            },
        )

        // Cho nay truoc la mot cau goi y chung chung. Khi da chon mot ro thi
        // cau do khong con viec gi lam, con thu nguoi van hanh CAN biet - don
        // o ro nay con thieu mon nao - thi lai khong co cho nao de. Nen doi
        // ngay tai cho: chua chon thi goi y, chon roi thi bang ke don.
        OrderLine(state, fallback = s.rackHint)
    }
}

/* ----------------------------------------------------------------- don hang */

// Bang ke don cua ro dang chon: tung SKU da vao hay con cho.
//
// Chi dem so luong thi khong tra loi duoc cau hoi "don nay du chua" - phai biet
// THIEU MON NAO moi di tim duoc.
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun OrderLine(state: UiState, fallback: String) {
    val brand = LocalBrand.current
    val s = LocalS.current
    val order = state.order

    if (state.selectedSlot == null || order == null || order.items.isEmpty()) {
        Text(fallback, style = MaterialTheme.typography.labelSmall, color = brand.muted)
        return
    }

    var showQr by remember { mutableStateOf(false) }
    if (showQr) OrderQrDialog(order, onClose = { showQr = false })

    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
    FlowRow(
        Modifier.weight(1f),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text(
            "${order.order} · ${s.orderProgress(order.done, order.total)} · " +
                if (order.complete) s.orderComplete else s.orderMissing(order.total - order.done),
            style = MaterialTheme.typography.labelLarge,
            color = if (order.complete) brand.ok else brand.warn,
        )
        order.items.forEach { item ->
            val tone = if (item.scanned) brand.ok else brand.muted
            Row(
                Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .background(tone.copy(alpha = 0.12f))
                    .padding(horizontal = 8.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    if (item.scanned) "✓" else "○",
                    style = MaterialTheme.typography.labelSmall,
                    color = tone,
                )
                Spacer(Modifier.width(5.dp))
                Text(
                    item.sku,
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = if (item.scanned) FontWeight.SemiBold else FontWeight.Normal,
                    color = if (item.scanned) MaterialTheme.colorScheme.onSurface else brand.muted,
                )
            }
        }
    }

        // Goc phai cua dong: mo ma QR cua don. Cho nay von la khoang trong.
        Spacer(Modifier.width(10.dp))
        FilledTonalButton(
            onClick = { showQr = true },
            contentPadding = PaddingValues(horizontal = 14.dp, vertical = 8.dp),
        ) {
            Icon(
                Icons.Filled.QrCode2,
                contentDescription = null,
                modifier = Modifier.size(18.dp),
            )
            Spacer(Modifier.width(8.dp))
            Text(s.showQr, maxLines = 1)
        }
    }
}

// Ma QR cua don, ve to het co. Quet no ra dung ma don, tu do tra duoc ca don:
// khay nao, gom nhung SKU nao, da vao duoc may mon.
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun OrderQrDialog(order: OrderDetail, onClose: () -> Unit) {
    val brand = LocalBrand.current
    val s = LocalS.current

    AlertDialog(
        onDismissRequest = onClose,
        confirmButton = { TextButton(onClick = onClose) { Text(s.close) } },
        title = { Text(order.order) },
        text = {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                QrCode(
                    text = order.order,
                    modifier = Modifier.size(300.dp),
                )
                Text(
                    "${s.slotNo(order.slot)} · ${s.orderProgress(order.done, order.total)} · " +
                        if (order.complete) s.orderComplete else s.orderMissing(order.total - order.done),
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = if (order.complete) brand.ok else brand.warn,
                )
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    order.items.forEach { item ->
                        val tone = if (item.scanned) brand.ok else brand.muted
                        Text(
                            (if (item.scanned) "✓ " else "○ ") + item.sku,
                            style = MaterialTheme.typography.labelSmall,
                            color = tone,
                            modifier = Modifier
                                .clip(RoundedCornerShape(6.dp))
                                .background(tone.copy(alpha = 0.12f))
                                .padding(horizontal = 8.dp, vertical = 4.dp),
                        )
                    }
                }
                Text(
                    s.qrHint,
                    style = MaterialTheme.typography.labelSmall,
                    color = brand.muted,
                )
            }
        },
    )
}

// Bang "Ton kho khay dang chon" (+1 vat / -1 vat / Do het) da bo. No co tu
// truoc khi co luong don hang, va gio thi vua thua vua sai: +1 cong count nhung
// KHONG danh dau SKU nao ca, nen the ro bao "4/6" trong khi checklist chi tick
// duoc 2 mon - hai con so noi hai chuyen khac nhau ve cung mot cai ro.
//
// Con thieu mot viec that: don lay di roi thi phai don ro cho don sau vao. Cho
// do thuoc ve panel Don hang, khong phai mot bang sua tay.

// Da thu keo len 72/88 dp theo huong dan HMI cong nghiep (2cm x 1.5cm cho tay
// deo gang), nhung trong khung phu chi rong 30% man thi nut to den muc lan at ca
// giao dien - nhin ra la mot cai bang dieu khien phong to, khong phai app. Ve
// lai muc cu: van tren nguong 48 dp cua Material, bam bang ngon tay thoai mai.
private val TOUCH = 52.dp
private val TOUCH_TALL = 64.dp
