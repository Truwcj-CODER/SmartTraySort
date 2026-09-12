// Chuoi hien thi theo ngon ngu. Tu viet thay vi dung resource strings.xml +
// values-en vi app chi co hai tieng va vai chuc chuoi - va vi cach nay cho doi
// tieng ngay trong app khong can dung lai Activity. Cung kieu lam voi
// lib/l10n/strings.dart cua app ble_lock, de hai app doc ra la mot loi.
//
// Chua bao gom: core/Machine.kt (mo ta buoc PLC) va ConfigScreen (tham so may).
// Hai cho do van tieng Viet - them sau thi them vao day, khong lam cach khac.
package vn.hasaki.traysort.core

import androidx.compose.runtime.staticCompositionLocalOf

class S(val lang: Lang) {

    private fun t(vi: String, en: String): String = if (lang == Lang.VI) vi else en

    // ---- Chung ----
    val later get() = t("Để sau", "Later")
    val install get() = t("Cài đặt", "Install")
    val clear get() = t("Xóa", "Clear")
    val close get() = t("Đóng", "Close")

    // ---- Tab ----
    val tabOperate get() = t("Vận hành", "Operate")
    val tabDiagram get() = t("Sơ đồ", "Diagram")
    val tabConfig get() = t("Cài đặt", "Settings")
    val tabLog get() = t("Nhật ký", "Log")
    val tabSystem get() = t("Hệ thống", "System")

    // ---- Thanh tren ----
    val offline get() = t("mất mạng", "no network")
    val stock get() = t("Tồn", "Stock")

    // ---- Trang thai ----
    val ready get() = t("sẵn sàng", "ready")
    val notHomed get() = t("chưa lấy gốc tọa độ", "not homed")
    val noServoPower get() = t("chưa cấp điện trục", "drives not powered")
    val plcOffline get() = t("mất kết nối PLC", "PLC offline")
    fun lostLink(reason: String) = t("mất kết nối — $reason", "connection lost — $reason")
    fun faultCode(code: String) = t("lỗi — $code", "fault — $code")
    fun runningStep(step: Int) = t("đang chạy — bước $step", "running — step $step")
    val moving get() = t("đang di chuyển", "moving")
    fun movingToSlot(slot: Int) = t("đang chạy → khay $slot", "moving → tray $slot")
    val atPark get() = t("vị trí chờ (home)", "park position (home)")
    val lostLinkShort get() = t("mất kết nối", "link lost")
    fun atXZ(x: Int, z: Int) = t("ngang $x · cao $z", "across $x · up $z")

    // ---- The trang thai ----
    val atPosition get() = t("Đang ở", "Position")
    val phase get() = t("Giai đoạn", "Phase")
    val lastCommand get() = t("Lệnh cuối", "Last command")
    fun resultCode(code: Int) = t("mã $code", "code $code")
    fun faultBanner(code: String, hint: String) = t(
        "MÁY DỪNG VÌ LỖI — mã $code. ${hint}Kiểm tra cơ cấu rồi bấm Xóa lỗi, sau đó Về LIMIT.",
        "MACHINE STOPPED — fault $code. ${hint}Check the mechanism, tap Clear fault, then Go to LIMIT.",
    )

    // Ma loi Motion Control hay gap, dich sang cau noi duoc viec phai lam.
    //
    // 16#8402 la cai de dinh nhat: dat toc do cao hon Max velocity cua truc
    // trong TIA thi MC_MoveAbsolute tu choi ngay, FB nhay buoc 900 va may dung
    // im - nhin ma hex tran thi khong ai doan ra. Giu khop voi cac khoa hint.*
    // trong static/lang/*.json ben web.
    fun errorHint(code: String): String = when (code.uppercase().replace("0X", "0x")) {
        "0x8400" -> t(
            "Sai tham số lệnh chạy — kiểm tra lại tọa độ gửi xuống. ",
            "Bad motion command parameter — check the coordinates sent down. ",
        )
        "0x8402" -> t(
            "Tốc độ vượt trần Max velocity của trục trong TIA. Giảm tốc độ ở trang " +
                "Cài đặt, hoặc nâng Dynamics → Max velocity trong TIA rồi nạp lại. ",
            "Speed is over the axis Max velocity set in TIA. Lower the speed on the " +
                "Settings page, or raise Dynamics → Max velocity in TIA and reload. ",
        )
        "0x8403" -> t(
            "Gia tốc vượt trần Max acceleration của trục trong TIA. ",
            "Acceleration is over the axis Max acceleration set in TIA. ",
        )
        "0x8404" -> t(
            "Giật (jerk) vượt trần khai báo trong TIA. ",
            "Jerk is over the limit declared in TIA. ",
        )
        else -> ""
    }

    val hitLimitBanner get() = t(
        "Trục chạm vạch giới hạn nên dừng. Chu trình chưa chạy hết — dọn vật cản rồi chạy lại.",
        "An axis stopped at a limit switch. The cycle did not finish — clear the " +
            "obstruction and run again.",
    )
    val abortedBanner get() = t(
        "Chu trình trước bị dừng giữa chừng. Kiểm tra vị trí rồi chạy lại.",
        "The previous cycle was interrupted. Check the position and run again.",
    )
    val notHomedBanner get() = t(
        "Chưa lấy gốc tọa độ — bấm \"Về LIMIT\" trước khi chạy.",
        "Not homed — tap \"Go to LIMIT\" before running.",
    )

    // ---- Chu trinh ----
    val cycle get() = t("Chu trình", "Cycle")
    val noSlotPicked get() = t("chưa chọn khay", "no tray picked")
    fun slotNo(slot: Int) = t("khay số $slot", "tray $slot")
    val autoRun get() = t("Chạy tự động", "Run auto")
    val autoRunHint get() = t(
        "tới khay → lật đổ → về HOME",
        "to tray → tip → back to HOME",
    )
    // LIMIT la diem cam bien, co dinh theo co khi. HOME la cho may dung nghi,
    // nguoi van hanh tu dat bang nut parkHere. Truoc day hai cai nay dung chung
    // mot toa do trong PLC nen bam nut nao cung ve mot cho.
    val home get() = t("Về LIMIT", "Go to LIMIT")
    val park get() = t("Về HOME", "Go to HOME")
    val parkHere get() = t("Đặt HOME tại đây", "Set HOME here")
    val clearFault get() = t("Xóa lỗi", "Clear fault")
    val stop get() = t("DỪNG", "STOP")

    // ---- Gian khay ----
    val trayRack get() = t("Giàn khay", "Tray rack")
    fun rackSummary(items: Int, capacity: Int, full: Int, empty: Int) = t(
        "$items/$capacity vật · $full đầy · $empty trống",
        "$items/$capacity items · $full full · $empty empty",
    )
    val rackHint get() = t(
        "Chọn khay rồi bấm Chạy tự động, hoặc quét mã để máy tự tìm khay. " +
            "Xanh lá còn chỗ, vàng gần đầy, đỏ đã đầy.",
        "Pick a tray then tap Run auto, or scan a code to let the machine find one. " +
            "Green has room, amber nearly full, red full.",
    )
    val noLayout get() = t(
        "chưa có bố cục — kiểm tra kết nối hoặc cấu hình kích thước giàn khay",
        "no layout yet — check the connection or the rack dimensions",
    )
    fun rowLabel(side: String, row: Int) = t("$side — hàng $row", "$side — row $row")
    val sideRight get() = t("Phải", "Right")
    val sideLeft get() = t("Trái", "Left")
    val sideRightLower get() = t("phải", "right")
    val sideLeftLower get() = t("trái", "left")

    // ---- Ton kho ----
    val slotStock get() = t("Tồn kho khay đang chọn", "Stock in the picked tray")
    fun slotStockCount(count: Int, capacity: Int) = t(
        "$count/$capacity vật",
        "$count/$capacity items",
    )
    val plusOne get() = t("+1 vật", "+1 item")
    val minusOne get() = t("−1 vật", "−1 item")
    val emptyAll get() = t("Đổ hết", "Empty all")

    // ---- Don hang ----
    val order get() = t("Đơn hàng", "Order")
    val noOrder get() = t("rổ chưa gán đơn nào", "no order on this tray")
    fun orderProgress(done: Int, total: Int) = t("$done/$total món", "$done/$total items")
    val orderComplete get() = t("đã đủ", "complete")
    fun orderMissing(n: Int) = t("còn thiếu $n", "$n missing")
    val skuIn get() = t("đã vào", "in")
    val skuWaiting get() = t("chờ", "waiting")
    val showQr get() = t("Mã QR đơn", "Order QR")
    val qrHint get() = t(
        "Quét mã này để lấy thông tin đơn và danh sách SKU.",
        "Scan this to pull the order and its SKU list.",
    )

    // ---- Quet ma ----
    val scanHint get() = t("Quét mã hoặc gõ tay…", "Scan a code or type it…")
    val scanWithCamera get() = t("Quét bằng camera", "Scan with the camera")
    val scan get() = t("Quét", "Scan")

    // ---- Cai dat may ----
    val saveConfig get() = t("Lưu cấu hình", "Save configuration")
    val saveNote get() = t(
        "Bấm Lưu là xong: server ghi cấu hình, tính lại bảng tọa độ rồi tự đồng bộ " +
            "xuống máy. Không phải bấm thêm gì.",
        "Save is all it takes: the server stores the configuration, re-computes the " +
            "coordinate table and syncs it to the machine. Nothing else to press.",
    )
    val pushAgain get() = t("Đồng bộ lại", "Sync again")
    val saving get() = t("Đang đồng bộ…", "Syncing…")
    val pushDone get() = t("✓ Đã đồng bộ", "✓ In sync")
    fun pushFailed(reason: String) = t(
        "Chưa đồng bộ — $reason. Bấm Đồng bộ lại.",
        "Not in sync — $reason. Tap Sync again.",
    )
    val pushAgainNote get() = t(
        "Đồng bộ tự động thất bại (máy đang chạy hoặc mất kết nối), hoặc vừa nạp lại khối trong TIA:",
        "The automatic sync failed (machine busy or offline), or the block was just reloaded in TIA:",
    )
    val badConfig get() = t("Cấu hình chưa hợp lý", "Configuration is not valid")
    val derivedTitle get() = t("Quy đổi — kiểm tra chéo với TIA", "Conversions — cross-check with TIA")
    fun axisName(axis: String) = t("Trục ${axis.uppercase()}", "${axis.uppercase()} axis")
    val setInTia get() = t("khai trong TIA, chỉ để đối chiếu", "set in TIA, shown for reference")

    // ---- Hieu chinh truc ----
    val calTitle get() = t("Hiệu chỉnh trục", "Axis calibration")
    val calSubtitle get() = t("đo trước, lưu sau", "measure first, save after")
    val calNote get() = t(
        "Bảo trục chạy một đoạn đã biết, đo bằng thước rồi gõ số thật vào. Server " +
            "tính ngược ra tỉ lệ đúng. Bấm Tính thử bao nhiêu lần cũng được — chỉ " +
            "khi bấm Đưa vào cài đặt mới có gì bị ghi.",
        "Tell an axis to travel a known amount, measure it with a rule, and type the " +
            "real figure in. The server works the true scale back out. Preview as many " +
            "times as you like — nothing is written until you tap Apply.",
    )
    val calPickAxis get() = t("Trục", "Axis")
    val calTarget get() = t("Chạy thử tới", "Test move to")
    val calRun get() = t("Chạy thử", "Run test")
    val calMeasured get() = t("Đo được thật", "Measured")
    val calPreview get() = t("Tính thử", "Preview")
    val calApply get() = t("Đưa vào cài đặt", "Apply to settings")
    val calNotYet get() = t(
        "Gõ quãng chạy thử rồi bấm Chạy thử. Ô nhập số đo hiện ra sau đó.",
        "Type a test distance and tap Run test. The measurement box appears after that.",
    )
    fun calCommanded(from: String, to: String, delta: String, unit: String) = t(
        "Đã ra lệnh: $from → $to, tức $delta $unit",
        "Commanded: $from → $to, i.e. $delta $unit",
    )
    val calNow get() = t("Đang dùng", "Now")
    val calProposed get() = t("Đề nghị", "Proposed")
    val calPerUnit get() = t("xung mỗi đơn vị", "pulses per unit")
    val calFullRange get() = t("xung hết hành trình", "pulses, full range")
    val calCeiling get() = t("tốc độ trần", "top speed")
    fun calOffBy(factor: String) = t(
        "Trục chạy THIẾU $factor lần so với lệnh.",
        "The axis travels $factor× less than commanded.",
    )
    fun calOverBy(factor: String) = t(
        "Trục chạy QUÁ $factor lần so với lệnh.",
        "The axis travels $factor× more than commanded.",
    )
    val calOnTarget get() = t(
        "✓ Khớp — tỉ lệ đang dùng đã đúng, không cần sửa gì.",
        "✓ Matches — the current scale is right, nothing to change.",
    )
    fun calGearRatio(ratio: String) = t("Tỉ số truyền: $ratio:1", "Gear ratio: $ratio:1")
    val calApplied get() = t("✓ Đã lưu tỉ lệ mới và đồng bộ xuống máy", "✓ New scale saved and synced")

    // ---- Chay tay ----
    val manual get() = t("Chạy tay", "Manual")
    val manualSubtitle get() = t("chỉ dùng khi căn chỉnh máy", "for machine set-up only")
    val manualNote get() = t(
        "Mấy nút này bỏ qua chu trình tự động. Dùng để dò tọa độ và kiểm tra cơ cấu, " +
            "không dùng lúc sản xuất.",
        "These bypass the automatic cycle. Use them to find coordinates and check the " +
            "mechanism, not during production.",
    )
    val gotoSlot get() = t("Chỉ tới khay", "Move to tray only")
    val tiltOnly get() = t("Chỉ lật", "Tip only")
    fun workingOnSlot(slot: Int) = t("Đang thao tác trên khay $slot.", "Working on tray $slot.")
    val pickSlotFirst get() = t(
        "Chọn khay bên tab Vận hành trước.",
        "Pick a tray on the Operate tab first.",
    )
    val goTo get() = t("Đi tới", "Go to")
    val tiltTo get() = t("Lật tới góc", "Tip to angle")
    val tiltAngleBox get() = t("Y góc lật", "Y tipping angle")
    val colX get() = t("X ngang", "X horizontal")
    val colZ get() = t("Z cao", "Z vertical")
    val jogNote get() = t("Jog — giữ để chạy, nhả là dừng", "Jog — hold to move, release to stop")
    val jogLeft get() = t("↺ lật trái", "↺ tip left")
    val jogRight get() = t("lật phải ↻", "tip right ↻")

    // ---- Nguy hiem ----
    val danger get() = t("Nguy hiểm", "Danger")
    val wipeStock get() = t("Xóa toàn bộ tồn kho", "Wipe all stock")
    val wipeAsk get() = t("Xóa toàn bộ tồn kho?", "Wipe all stock?")
    fun wipeWarn(slots: Int) = t(
        "Số liệu của tất cả $slots khay sẽ về 0. Không hoàn lại được.",
        "Every one of the $slots trays goes back to 0. This cannot be undone.",
    )
    val wipeYes get() = t("Xóa hết", "Wipe everything")
    val cancel get() = t("Thôi", "Cancel")

    // ---- So do ----
    val machineDiagram get() = t("Sơ đồ máy", "Machine diagram")
    val diagramSubtitle get() = t(
        "chạy theo vị trí thật của 3 trục",
        "follows the real position of all three axes",
    )
    val diagramNote get() = t(
        "Kéo để xoay. Ngang là trục X, cao là trục Z, thanh ở đầu công tác là góc " +
            "lật trục Y. Hai dãy rổ nằm trước và sau ray, mỗi rổ là một hộp hở " +
            "miệng hướng lên. Rổ máy đang chạy tới sáng vàng, rổ đang chọn viền " +
            "xanh đậm, ô nét đứt là chỗ chờ.",
        "Drag to rotate. Across is the X axis, up is the Z axis, the bar on the head " +
            "is the Y tipping angle. The two tray rows sit in front of and behind the " +
            "rail, each tray an open box with the mouth facing up. The tray the " +
            "machine is heading for glows amber, the picked one is outlined green, " +
            "the dashed pad is the park position.",
    )
    val show3d get() = t("Hiện mô hình 3D", "Show the 3D model")
    val hide3d get() = t("Ẩn mô hình 3D", "Hide the 3D model")
    val model3d get() = t("Mô hình 3D", "3D model")
    val dragToRotate get() = t("kéo để xoay", "drag to rotate")
    val coordTable get() = t("Bảng tọa độ", "Coordinate table")
    fun slotCount(count: Int) = t("$count rổ", "$count trays")
    val colSlot get() = t("Rổ", "Tray")
    val colMouth get() = t("Miệng rổ", "Mouth")
    val colSide get() = t("Bên", "Side")

    // ---- Ban moi ----
    fun updateTitle(version: String) = t("Có bản $version", "Version $version is out")
    val updateFallback get() = t(
        "Bản mới đã sẵn trên máy chủ.",
        "A new build is waiting on the server.",
    )
    fun updateSize(mb: Long) = t("Dung lượng $mb MB", "$mb MB")
    val updateDownload get() = t("Tải và cài", "Download and install")
    fun updateReady(version: String) = t("Đã tải xong $version", "$version downloaded")

    // ---- Ngon ngu ----
    val otherLangCode get() = if (lang == Lang.VI) "EN" else "VI"
    val switchLang get() = t("Chuyển sang English", "Đổi sang tiếng Việt")
}

val LocalS = staticCompositionLocalOf { S(Lang.VI) }
