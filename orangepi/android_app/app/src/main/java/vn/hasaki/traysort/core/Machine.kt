// Doi ma so cua PLC ra chu tieng Viet, va mo ta form cau hinh.
//
// Ban dich buoc phai khop CASE #StepNo trong 04_FB_XY_Tray.scl. Sua ben SCL thi
// sua ca o day - hai ban dich nay va app/static/js/ui.js phai noi giong nhau.
package vn.hasaki.traysort.core

/** Mot buoc trong chu trinh: chu de doc, va no thuoc giai doan nao tren thanh tien trinh. */
data class Step(val text: String, val stage: Int?)

val STEPS: Map<Int, Step> = mapOf(
    0 to Step("chờ lệnh", null),
    5 to Step("đang lấy gốc tọa độ", null),
    10 to Step("chạy ngang tới khay", 0),
    20 to Step("lên xuống tới khay", 1),
    30 to Step("dừng ổn định tại khay", 2),
    100 to Step("chuẩn bị lật", 3),
    170 to Step("đang lật ra", 3),
    175 to Step("giữ ở góc lật", 3),
    180 to Step("lật về giữa", 3),
    190 to Step("lật xong", 3),
    195 to Step("đưa trục lật về giữa", 4),
    200 to Step("nâng hạ về HOME", 4),
    210 to Step("chạy ngang về HOME", 4),
    220 to Step("hoàn tất chu trình", 4),
    300 to Step("lật tay tới góc đặt", null),
    900 to Step("DỪNG VÌ LỖI", null),
    950 to Step("đang xóa lỗi…", null),
)

fun stepOf(number: Int): Step = STEPS[number] ?: Step("bước $number", null)

val RESULT_TEXT: Map<Int, String> = mapOf(
    0 to "chưa chạy lệnh nào",
    1 to "đang chạy",
    2 to "hoàn thành",
    3 to "bị dừng giữa chừng",
    4 to "lỗi",
    5 to "lệnh không hợp lệ",
    // Cham vach gioi han: khong phai loi, may lam dung viec cua no. Tach rieng
    // khoi ma 3 (nut DUNG khan) de nhat ky khong day chu "that bai".
    6 to "dừng vì chạm vạch giới hạn",
)

val STAGE_NAMES = listOf("Chạy ngang", "Lên xuống", "Dừng ổn định", "Lật đổ", "Về HOME")

/** mm. Lech nho hon nay coi nhu da toi noi - dung de doan dang dung o ro nao. */
const val POSITION_TOLERANCE = 3.0f

/* ------------------------------------------------------------------ form cau hinh */

/* ------------------------------------------------------------------ form cau hinh */

// Nhan song ngu. Giu thang trong day chu khong tach sang S: nhan gan chat voi
// tung truong, tach ra hai file thi sua mot cai phai nho sua ca hai.
data class Field(
    val key: String,
    val vi: String,
    val en: String,
    val integer: Boolean = false,
    // Khong cho sua, chi hien thanh dong chu. Van nam trong danh sach vi con
    // phai gui len server: bo han khoi GEOMETRY_GROUPS thi payload thieu o do,
    // va server lay mac dinh cua schema - ghi de mat so that ma khong ai biet.
    val readOnly: Boolean = false,
) {
    fun label(lang: Lang): String = if (lang == Lang.VI) vi else en
}

data class FieldGroup(
    val vi: String,
    val en: String,
    val fields: List<Field>,
    val noteVi: String? = null,
    val noteEn: String? = null,
    // >0: xep theo COT, moi cot bay nhieu o. Dung khi cac o di theo tung cum co
    // nghia - vi du moi truc mot cot: X tren X duoi, roi Z, roi Y.
    val stackBy: Int = 0,
) {
    fun legend(lang: Lang): String = if (lang == Lang.VI) vi else en
    fun note(lang: Lang): String? = if (lang == Lang.VI) noteVi else noteEn
}

// Xep theo do "dinh lien" giam dan: thong so truyen dong gan voi chinh dong co
// va hop so, chi doi khi thay thiet bi; con vi tri cho thi lap xong van co the
// doi. Cai nao it doi nhat len truoc.
val SETUP_GROUPS: List<FieldGroup> = listOf(
    FieldGroup(
        "Thông số truyền động", "Drive parameters",
        listOf(
            Field("x_pulses_per_rev", "X: xung/vòng", "X: pulses/rev", integer = true),
            Field("x_mm_per_rev", "X: mm/vòng", "X: mm/rev"),
            Field("z_pulses_per_rev", "Z: xung/vòng", "Z: pulses/rev", integer = true),
            Field("z_mm_per_rev", "Z: mm/vòng", "Z: mm/rev"),
            Field("y_pulses_per_rev", "Y: xung/vòng", "Y: pulses/rev", integer = true),
            Field("y_deg_per_rev", "Y: độ/vòng", "Y: degrees/rev"),
        ),
        noteVi = "Mỗi trục một cột. Phải trùng với Technology Object trong TIA — " +
            "server không ghi được xuống PLC.",
        noteEn = "One column per axis. Must match the Technology Object in TIA — " +
            "the server cannot write these to the PLC.",
        stackBy = 2,
    ),
    FieldGroup(
        "Vị trí giàn rổ", "Rack position",
        listOf(
            Field("x_first", "X tâm rổ cột đầu (mm)", "X of first column centre (mm)"),
            Field("z_first", "Z miệng rổ hàng dưới (mm)", "Z of bottom row mouth (mm)"),
            Field("rack_offset", "Ray → mép trong rổ (mm)", "Rail to inner basket edge (mm)"),
        ),
    ),
    FieldGroup(
        "Khay đầu công tác", "Head tray",
        listOf(
            Field("tray_length", "Chiều dài, theo X (mm)", "Length, along X (mm)"),
            Field("tray_width", "Chiều rộng, theo chiều lật (mm)", "Width, along the tipping axis (mm)"),
            Field("drop_lift", "Nâng cao hơn miệng rổ (mm)", "Lift above the basket mouth (mm)"),
        ),
    ),
    FieldGroup(
        "Hành trình ba trục", "Axis travel",
        listOf(
            Field("x_travel", "X: hành trình ngang (mm)", "X: horizontal travel (mm)"),
            Field("z_travel", "Z: hành trình lên xuống (mm)", "Z: vertical travel (mm)"),
            Field("tilt_angle", "Y: góc lật khi đổ (°)", "Y: tipping angle (°)"),
            Field("y_max_angle", "Y: giới hạn phần mềm (±°)", "Y: software limit (±°)", readOnly = true),
        ),
        noteVi = "Góc lật khi đổ không được vượt giới hạn phần mềm của Axis_Y.",
        noteEn = "The tipping angle must stay under the Axis_Y software limit.",
    ),
    FieldGroup(
        "Vị trí chờ", "Park position",
        listOf(
            Field("park_x", "X ngang (mm)", "X horizontal (mm)"),
            Field("park_z", "Z cao (mm)", "Z vertical (mm)"),
            Field("park_y", "Y góc lật (°)", "Y tipping angle (°)"),
        ),
        noteVi = "Nơi máy đứng giữa hai chu trình, chỗ gắn cảm biến.",
        noteEn = "Where the machine rests between cycles, where the sensors sit.",
    ),
)

// Nhung so nguoi van hanh that su mo ra sua. Dat gan nut Luu.
val TUNING_GROUPS: List<FieldGroup> = listOf(
    FieldGroup(
        "Kích thước rổ", "Basket dimensions",
        listOf(
            Field("basket_length", "Chiều dài, theo X (mm)", "Length, along X (mm)"),
            Field("basket_depth", "Chiều sâu, hướng ra ngoài (mm)", "Depth, outward (mm)"),
            Field("basket_height", "Chiều cao thành rổ (mm)", "Wall height (mm)"),
            Field("basket_gap", "Khe hở tối thiểu giữa 2 rổ (mm)", "Minimum gap between baskets (mm)"),
        ),
        noteVi = "Đổi mấy số này là cả bố cục xếp lại.",
        noteEn = "Changing these re-computes the whole layout.",
    ),
    FieldGroup(
        "Tốc độ và thời gian", "Speed and timing",
        listOf(
            Field("vel_x", "X: tốc độ ngang (mm/s)", "X: horizontal speed (mm/s)"),
            Field("vel_z", "Z: tốc độ lên xuống (mm/s)", "Z: vertical speed (mm/s)"),
            Field("tilt_vel", "Y: tốc độ lật (°/s)", "Y: tipping speed (°/s)"),
            Field("dwell_ms", "Dừng ổn định tại rổ (ms)", "Settle time at the basket (ms)", integer = true),
            Field("tilt_hold_ms", "Giữ ở góc lật (ms)", "Hold at the tipping angle (ms)", integer = true),
            Field("tilt_count", "Số lần lật mỗi chu trình", "Tips per cycle", integer = true),
        ),
        noteVi = "Đồng bộ thẳng xuống máy, không phải mở TIA.",
        noteEn = "Synced straight to the machine — no need to open TIA.",
    ),
)

// Ca hai gop lai - dung cho cho nao can duyet het moi o, nhu luc doc/ghi ban nhap.
val GEOMETRY_GROUPS: List<FieldGroup> = SETUP_GROUPS + TUNING_GROUPS

// Nhan cua bang quy doi. Nhan cua tung truc da bo tien to "X — " vi bang xep
// moi truc mot cot, tieu de cot noi ro roi.
val DERIVED_LABELS: Map<String, Pair<String, String>> = mapOf(
    "so_ro" to ("Số rổ máy xếp được" to "Baskets in the layout"),
    "buoc_ngang_mm" to ("Bước ngang giữa 2 rổ (mm)" to "Column pitch (mm)"),
    "khe_ho_that_mm" to ("Khe hở thật sau khi trải đều (mm)" to "Actual gap after spreading (mm)"),
    "buoc_hang_mm" to ("Bước giữa 2 hàng (mm)" to "Row pitch (mm)"),
    "x_pulses_per_mm" to ("xung mỗi mm" to "pulses per mm"),
    "z_pulses_per_mm" to ("xung mỗi mm" to "pulses per mm"),
    "y_pulses_per_degree" to ("xung mỗi độ" to "pulses per degree"),
    "x_pulses_full_travel" to ("xung hết hành trình" to "pulses, full travel"),
    "z_pulses_full_travel" to ("xung hết hành trình" to "pulses, full travel"),
    "y_pulses_full_range" to ("xung hết góc lật" to "pulses, full tipping range"),
    "x_max_velocity_mm_s" to ("tốc độ trần (mm/s)" to "top speed (mm/s)"),
    "z_max_velocity_mm_s" to ("tốc độ trần (mm/s)" to "top speed (mm/s)"),
    "y_max_velocity_deg_s" to ("tốc độ trần (°/s)" to "top speed (°/s)"),
)

fun derivedLabel(key: String, lang: Lang): String {
    val pair = DERIVED_LABELS[key] ?: return key
    return if (lang == Lang.VI) pair.first else pair.second
}

/** So thuc -> chuoi de dat vao o nhap: bo duoi ".0" cho o so nguyen va cho ca
 *  nhung so tron, khong ai muon nhin "200.0" trong o dai rong. */
fun formatValue(value: Double, integer: Boolean): String = when {
    integer -> value.toLong().toString()
    value == value.toLong().toDouble() -> value.toLong().toString()
    else -> value.toString()
}
