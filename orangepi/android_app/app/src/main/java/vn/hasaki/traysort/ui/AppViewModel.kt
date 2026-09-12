// Noi duy nhat giu trang thai giao dien va goi lenh. Doi xung voi app.js ben web.
//
// Man hinh chi doc UiState va bam nut; khong man hinh nao tu goi API, nen khong
// co chuyen hai cho cung sua mot thu ma khong biet nhau.
package vn.hasaki.traysort.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import vn.hasaki.traysort.BuildConfig
import vn.hasaki.traysort.core.Prefs
import vn.hasaki.traysort.core.Lang
import vn.hasaki.traysort.data.OrderDetail
import vn.hasaki.traysort.core.ThemeMode
import vn.hasaki.traysort.data.ApiException
import vn.hasaki.traysort.data.Calibration
import vn.hasaki.traysort.data.GeometryMap
import vn.hasaki.traysort.data.JogBits
import vn.hasaki.traysort.data.LayoutPlan
import vn.hasaki.traysort.data.Repository
import vn.hasaki.traysort.data.Slot
import vn.hasaki.traysort.data.Snapshot
import vn.hasaki.traysort.data.StreamEvent
import vn.hasaki.traysort.data.Summary
import vn.hasaki.traysort.data.UpdateStage
import vn.hasaki.traysort.data.networkText
import java.time.LocalTime
import java.time.format.DateTimeFormatter

enum class LogLevel { INFO, OK, WARN, ERROR }

data class LogEntry(val time: String, val text: String, val level: LogLevel)

// Mot lan chay thu de hieu chinh: truc nao, dung o dau truoc khi chay, va da
// bao chay toi dau.
//
// Giu ca diem XUAT PHAT chu khong chi cai dich: lenh chay la toa do tuyet doi,
// nhung cai dem duoc bang thuoc la QUANG DUONG. Truc dang o 10 ma bao di toi 60
// thi no chi chay 50 - lay thang 60 lam so ra lenh la ti le tinh ra sai ngay.
data class CalTest(val axis: String, val from: Double, val target: Double) {
    val commanded: Double get() = target - from
}

data class UiState(
    val bootstrapped: Boolean = false,
    val serverUrl: String = "",
    val theme: ThemeMode = ThemeMode.SYSTEM,
    val lang: Lang = Lang.VI,
    val order: OrderDetail? = null,
    // Ket qua lan Luu cau hinh gan nhat: da day xuong PLC duoc chua.
    val pushOk: Boolean? = null,
    val pushNote: String? = null,
    val linked: Boolean = false,
    val snapshot: Snapshot = Snapshot(),
    val slots: List<Slot> = emptyList(),
    val summary: Summary = Summary(),
    val geometry: GeometryMap = emptyMap(),
    val plan: LayoutPlan = LayoutPlan(),
    val derived: List<Pair<String, String>> = emptyList(),
    val problems: List<String> = emptyList(),
    val speedWarnings: List<String> = emptyList(),
    // Hieu chinh truc: lan chay thu gan nhat, va ket qua tinh nguoc ra tu no.
    val calTest: CalTest? = null,
    val calibration: Calibration? = null,
    val calApplied: Boolean = false,
    val selectedSlot: Int? = null,
    val running: String? = null,
    val jog: JogBits = JogBits(),
    val log: List<LogEntry> = emptyList(),
    val update: UpdateStage = UpdateStage.Idle,
) {
    val selected: Slot? get() = slots.firstOrNull { it.slot == selectedSlot }
    val configured: Boolean get() = serverUrl.isNotBlank()
}

private const val LOG_LIMIT = 200
private val CLOCK: DateTimeFormatter = DateTimeFormatter.ofPattern("HH:mm:ss")

class AppViewModel(app: Application) : AndroidViewModel(app) {

    private val prefs = Prefs(app.applicationContext)
    private val repo = Repository(prefs)
    private val api get() = repo.api

    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    // Loi can dap vao mat nguoi dung ngay, khong doi ho mo tab Nhat ky.
    private val _alerts = MutableSharedFlow<String>(
        extraBufferCapacity = 4,
        onBufferOverflow = BufferOverflow.DROP_OLDEST,
    )
    val alerts: SharedFlow<String> = _alerts

    private val updater = repo.updater(app.applicationContext)
    private var jogJob: Job? = null

    init {
        viewModelScope.launch {
            prefs.theme.collect { mode -> _state.update { it.copy(theme = mode) } }
        }
        viewModelScope.launch {
            prefs.lang.collect { value -> _state.update { it.copy(lang = value) } }
        }
        viewModelScope.launch {
            repo.serverUrl.collect { url ->
                _state.update { it.copy(serverUrl = url, bootstrapped = true) }
            }
        }
        viewModelScope.launch { listen() }
    }

    /* =================================================================== tu cap nhat */

    // Hoi mot lan luc mo app, va bat cu khi nao nguoi dung bam trong Cai dat.
    // Im lang khi mang chua san sang: lan mo app dau tien o cho khong co song
    // ma dap mot dong bao do vao mat thi khong giup duoc gi.
    fun checkUpdate(loud: Boolean) {
        if (_state.value.serverUrl.isBlank()) return
        if (_state.value.update is UpdateStage.Downloading) return

        _state.update { it.copy(update = UpdateStage.Checking) }
        viewModelScope.launch {
            try {
                val release = updater.check(BuildConfig.VERSION_CODE)
                if (release == null) {
                    _state.update { it.copy(update = UpdateStage.UpToDate) }
                    if (loud) log("đang chạy bản mới nhất (${BuildConfig.VERSION_NAME})", LogLevel.OK)
                } else {
                    _state.update { it.copy(update = UpdateStage.Available(release)) }
                    log("có bản mới ${release.versionName} trên server", LogLevel.OK)
                }
            } catch (e: Exception) {
                _state.update { it.copy(update = UpdateStage.Idle) }
                if (loud) fail("không hỏi được bản mới: ${networkText(e)}")
            }
        }
    }

    fun downloadUpdate() {
        val release = (_state.value.update as? UpdateStage.Available)?.release ?: return
        _state.update { it.copy(update = UpdateStage.Downloading(0)) }

        viewModelScope.launch {
            try {
                val file = updater.download(release) { percent ->
                    _state.update { it.copy(update = UpdateStage.Downloading(percent)) }
                }
                _state.update { it.copy(update = UpdateStage.Ready(file, release)) }
                log("đã tải xong bản ${release.versionName}", LogLevel.OK)
            } catch (e: Exception) {
                val reason = e.message ?: networkText(e)
                _state.update { it.copy(update = UpdateStage.Failed(reason)) }
                fail("tải bản mới thất bại: $reason")
            }
        }
    }

    fun installUpdate() {
        val ready = _state.value.update as? UpdateStage.Ready ?: return
        if (!updater.canInstall()) {
            _alerts.tryEmit("cần bật \"cho phép cài đặt từ nguồn này\" trong Cài đặt Android")
            return
        }
        runCatching { updater.install(ready.file) }
            .onFailure { fail("không mở được trình cài đặt: ${it.message}") }
    }

    fun updaterCanInstall(): Boolean = updater.canInstall()

    fun installPermissionIntent() = updater.installPermissionIntent()

    fun dismissUpdate() = _state.update { it.copy(update = UpdateStage.Idle) }

    /* ================================================================ dong su kien */

    // Ba loai su kien tu SSE do vao dung ba manh cua UiState. Khong cho nao goi
    // them REST de "lam moi" - server day xuong la du.
    private suspend fun listen() = repo.events().collectLatest { event ->
        when (event) {
            is StreamEvent.Status -> _state.update { it.copy(snapshot = event.snapshot) }

            is StreamEvent.Inventory -> _state.update {
                it.copy(slots = event.payload.slots, summary = event.payload.summary)
            }

            is StreamEvent.Layout -> _state.update {
                it.copy(
                    geometry = event.payload.geometry,
                    plan = event.payload.layout,
                    derived = event.payload.derivedText(),
                    problems = event.payload.problems,
                    speedWarnings = event.payload.speedWarnings,
                )
            }

            is StreamEvent.Link -> {
                _state.update { it.copy(linked = event.connected) }
                if (event.connected) log("đã nối được server", LogLevel.OK)
                else log("mất kết nối server${event.note?.let { n -> " — $n" }.orEmpty()}, đang thử lại", LogLevel.WARN)
            }
        }
    }

    /* ===================================================================== lenh may */

    // Moi nut deu di qua day nen hanh vi giong nhau va khong cho nao quen bat loi.
    private fun command(label: String, block: suspend () -> String?) {
        if (_state.value.running != null) {
            log("bỏ qua \"$label\" — đang có lệnh chạy dở", LogLevel.WARN)
            return
        }
        _state.update { it.copy(running = label) }
        log("$label…")

        viewModelScope.launch {
            try {
                val note = block()
                log(note?.ifBlank { null } ?: "$label xong", LogLevel.OK)
            } catch (e: ApiException) {
                fail("$label thất bại: ${e.message}")
            } catch (e: Exception) {
                fail("$label thất bại: ${networkText(e)}")
            } finally {
                _state.update { it.copy(running = null) }
            }
        }
    }

    private fun fail(text: String) {
        log(text, LogLevel.ERROR)
        _alerts.tryEmit(text)
    }

    fun selectSlot(slot: Int?) {
        _state.update { it.copy(selectedSlot = slot, order = null) }
        if (slot == null) return
        // Ro chua gan don nao thi server tra 404 - khong phai loi, chi la khong
        // co gi de hien.
        viewModelScope.launch {
            val detail = runCatching { repo.api.orderAt(slot).order }.getOrNull()
            _state.update {
                if (it.selectedSlot == slot) it.copy(order = detail) else it
            }
        }
    }

    fun home() = command("Về LIMIT (dò cảm biến)") { api.home().message }
    fun park() = command("Về HOME") { api.park().message }
    fun parkHere() = command("Đặt HOME tại chỗ đang đứng") { api.parkHere().message }
    fun resetFault() = command("Xóa lỗi") { api.reset().message }

    fun runSlot() = withSlot { slot -> command("Chạy tự động khay $slot") { api.runSlot(slot).message } }
    fun gotoSlot() = withSlot { slot -> command("Tới khay $slot") { api.gotoSlot(slot).message } }
    fun tiltSlot() = withSlot { slot -> command("Lật tại khay $slot") { api.tiltSlot(slot).message } }
    fun teachSlot() = withSlot { slot -> command("Teach khay $slot") { api.teachSlot(slot).message } }

    fun moveTo(x: Double, z: Double) =
        command("Đi tới ngang $x cao $z") { api.moveTo(x, z).message }

    fun tiltTo(angle: Double) = command("Lật tới $angle°") { api.tiltTo(angle).message }

    // Dung khan di duong rieng: khong qua khoa, khong cho lenh dang chay xong.
    fun emergencyStop() {
        viewModelScope.launch {
            try {
                api.stop()
                log("ĐÃ GỬI LỆNH DỪNG", LogLevel.WARN)
            } catch (e: Exception) {
                fail("gửi lệnh dừng thất bại: ${networkText(e)}")
            }
        }
    }

    /* ====================================================================== ton kho */

    fun addItem() = withSlot { slot -> command("Thêm 1 vật vào khay $slot") { api.addItems(slot); null } }

    fun removeItem() = withSlot { slot -> command("Bớt 1 vật khỏi khay $slot") { api.removeItems(slot); null } }

    fun clearSlot() = withSlot { slot ->
        val row = _state.value.selected
        if (row == null || row.count == 0) {
            log("khay $slot đang trống", LogLevel.WARN)
        } else {
            command("Đổ hết khay $slot") { api.removeItems(slot, row.count); null }
        }
    }

    fun resetInventory() = command("Xóa toàn bộ tồn kho") { api.resetInventory(); null }

    fun assignCode(slot: Int, code: String, capacity: Int?) =
        command("Lưu mã cho khay $slot") { api.setSlotConfig(slot, code, capacity); null }

    /* ======================================================================= quet ma */

    fun scan(code: String, run: Boolean = true) {
        val trimmed = code.trim()
        if (trimmed.isEmpty()) return

        command("Quét mã $trimmed") {
            val result = api.scan(trimmed, run)
            _state.update { it.copy(selectedSlot = result.slot) }
            result.message
        }
    }

    /* ======================================================================= jog tay */

    // Giu nut -> gui bit len; nha -> gui bit xuong. Lenh nao cung phai toi noi,
    // ke ca khi ngon tay nha nhanh hon mang, nen khong bo qua lan gui nao.
    fun jog(direction: String, held: Boolean) {
        val next = _state.value.jog.with(direction, held)
        if (next == _state.value.jog) return
        _state.update { it.copy(jog = next) }
        sendJog(next)
    }

    fun releaseAllJog() {
        if (!_state.value.jog.anyHeld) return
        val cleared = JogBits()
        _state.update { it.copy(jog = cleared) }
        sendJog(cleared)
    }

    private fun sendJog(bits: JogBits) {
        jogJob?.cancel()
        jogJob = viewModelScope.launch {
            // Nha nut ma loi thi PLC van tu cat jog sau JogMaxTime - khong doa
            // nguoi van hanh bang mot dong bao do.
            runCatching { api.jog(bits) }.onFailure {
                if (bits.anyHeld) fail("jog thất bại: ${networkText(it)}")
            }
        }
    }

    /* ====================================================================== cau hinh */

    // Dai bao THANH CONG tu tat sau vai giay - viec da xong thi khong can nam
    // mai tren man. Dai bao THAT BAI thi giu lai, vi nguoi dung con phai bam
    // Day lai; tu tat la mat luon thong tin can hanh dong.
    fun clearPushResult() = _state.update { it.copy(pushOk = null, pushNote = null) }

    fun saveGeometry(values: GeometryMap) = command("Lưu cấu hình") {
        _state.update { it.copy(pushOk = null, pushNote = null) }
        // Goi hong (mat mang, server khong tra loi kip) thi cung phai ra bang do,
        // khong thi banner tat ngam, nguoi dung khong biet xong hay loi.
        val result = try {
            api.saveGeometry(values)
        } catch (e: Exception) {
            _state.update { it.copy(pushOk = false, pushNote = networkText(e)) }
            throw e
        }
        _state.update { it.copy(pushOk = result.pushOk, pushNote = result.pushed) }

        result.layout.let { plan ->
            log("bố cục mới: ${plan.slots} rổ — ${plan.rows} hàng × ${plan.columns} cột × 2 bên")
        }
        // Bo cuc co lai thi may ro cuoi bien mat - phai noi ro cai nao con vat ben trong.
        if (result.orphans.isNotEmpty()) {
            val list = result.orphans.joinToString(", ") { "${it.slot} (${it.count} vật)" }
            log("bố cục nhỏ lại, rổ $list không còn trong bố cục — nhớ lấy vật ra", LogLevel.WARN)
        }
        result.pushed?.let { pushed ->
            log(pushed, if (result.pushOk == false) LogLevel.ERROR else LogLevel.OK)
        }
        if (result.problems.isNotEmpty()) {
            log("cấu hình có ${result.problems.size} chỗ chưa hợp lý, chưa đẩy xuống PLC", LogLevel.WARN)
        }
        "đã lưu cấu hình"
    }

    fun pushTable() = command("Đẩy tọa độ xuống PLC") { api.pushTable().message }

    /* ================================================================= hieu chinh */

    // Chay mot doan da biet de lat co do duoc. Ghi lai diem xuat phat NGAY
    // TRUOC khi ban lenh: doc lai sau khi chay xong thi lay phai vi tri dich,
    // va quang duong ra 0.
    fun calibrationTest(axis: String, target: Double) {
        val status = _state.value.snapshot.status
        if (status == null) {
            log("chưa đọc được vị trí trục — kiểm tra kết nối PLC", LogLevel.WARN)
            return
        }
        val from = when (axis) {
            "x" -> status.x
            "z" -> status.z
            else -> status.y
        }.toDouble()

        val unit = if (axis == "y") "°" else "mm"
        command("Chạy thử trục ${axis.uppercase()} tới $target$unit") {
            // Ban nhap cu la cua lan do truoc - de lai thi nguoi dung bam Tinh
            // thu roi doc phai ket qua cua doan chay khac.
            _state.update { it.copy(calibration = null, calApplied = false) }
            val note = when (axis) {
                "y" -> api.tiltTo(target)
                "x" -> api.moveTo(target, status.z.toDouble())
                else -> api.moveTo(status.x.toDouble(), target)
            }.message
            _state.update { it.copy(calTest = CalTest(axis, from, target)) }
            note
        }
    }

    fun calibrationPreview(measured: Double) {
        val test = _state.value.calTest ?: return
        command("Tính tỉ lệ trục ${test.axis.uppercase()}") {
            val result = api.calibratePreview(test.axis, test.commanded, measured)
            _state.update { it.copy(calibration = result, calApplied = false) }
            if (result.onTarget) "tỉ lệ trục ${test.axis.uppercase()} đang đúng"
            else "trục ${test.axis.uppercase()} lệch ${result.errorFactor} lần — " +
                "đề nghị ${result.field} = ${result.proposed.pulsesPerUnit} xung/đơn vị"
        }
    }

    fun calibrationApply(measured: Double) {
        val test = _state.value.calTest ?: return
        command("Lưu tỉ lệ trục ${test.axis.uppercase()}") {
            val result = api.calibrateApply(test.axis, test.commanded, measured)
            _state.update {
                it.copy(
                    calibration = result.calibration,
                    calApplied = true,
                    pushOk = result.pushOk,
                    pushNote = result.pushed,
                )
            }
            result.calibration.warnings.forEach { log(it, LogLevel.WARN) }
            // Cau nay phai vao nhat ky: sua so ben server KHONG lam may chay
            // khac di, va do dung la cho de tuong da xong.
            log(result.calibration.tiaNote, LogLevel.WARN)
            result.pushed
        }
    }

    fun clearCalibration() =
        _state.update { it.copy(calTest = null, calibration = null, calApplied = false) }

    /* ======================================================================= cai dat */

    fun setServer(url: String) {
        viewModelScope.launch {
            prefs.setServerUrl(url)
            log("đổi địa chỉ server sang ${Prefs.normalizeUrl(url)}")
        }
    }

    fun setTheme(mode: ThemeMode) = viewModelScope.launch { prefs.setTheme(mode) }

    fun toggleLang() = viewModelScope.launch {
        prefs.setLang(if (_state.value.lang == Lang.VI) Lang.EN else Lang.VI)
    }

    fun clearLog() = _state.update { it.copy(log = emptyList()) }

    /* ======================================================================== noi bo */

    private inline fun withSlot(block: (Int) -> Unit) {
        val slot = _state.value.selectedSlot
        if (slot == null) log("chưa chọn khay nào", LogLevel.WARN) else block(slot)
    }

    private fun log(text: String, level: LogLevel = LogLevel.INFO) {
        val entry = LogEntry(LocalTime.now().format(CLOCK), text, level)
        _state.update { it.copy(log = (listOf(entry) + it.log).take(LOG_LIMIT)) }
    }
}
