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
    200 to Step("nâng hạ về chỗ chờ", 4),
    210 to Step("chạy ngang về chỗ chờ", 4),
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
)

val STAGE_NAMES = listOf("Chạy ngang", "Lên xuống", "Dừng ổn định", "Lật đổ", "Về chỗ chờ")

/** mm. Lech nho hon nay coi nhu da toi noi - dung de doan dang dung o ro nao. */
const val POSITION_TOLERANCE = 3.0f

/* ------------------------------------------------------------------ form cau hinh */

data class Field(val key: String, val label: String, val integer: Boolean = false)
data class FieldGroup(val legend: String, val note: String? = null, val fields: List<Field>)

// Cung thu tu, cung cau chu voi app/templates/index.html. Server them mot thong
// so moi thi them mot dong o day la form tu moc them o nhap.
val GEOMETRY_GROUPS: List<FieldGroup> = listOf(
    FieldGroup(
        "Cái rổ",
        "Đổi mấy số này là cả bố cục xếp lại.",
        listOf(
            Field("basket_length", "Dài, dọc trục X (mm)"),
            Field("basket_depth", "Sâu, hướng ra ngoài (mm)"),
            Field("basket_height", "Cao thành rổ (mm)"),
            Field("basket_gap", "Khe hở tối thiểu giữa 2 rổ (mm)"),
        ),
    ),
    FieldGroup(
        "Giàn rổ đặt ở đâu",
        null,
        listOf(
            Field("x_first", "Tâm rổ cột đầu, X (mm)"),
            Field("z_first", "Miệng rổ hàng dưới cùng, Z (mm)"),
            Field("rack_offset", "Ray → mép trong rổ (mm)"),
        ),
    ),
    FieldGroup(
        "Khay đựng trên đầu công tác",
        null,
        listOf(
            Field("tray_length", "Dài, dọc trục X (mm)"),
            Field("tray_width", "Rộng, theo chiều lật (mm)"),
            Field("drop_lift", "Đứng cao hơn miệng rổ (mm)"),
        ),
    ),
    FieldGroup(
        "Ba trục chạy tới đâu",
        "Góc lật phải nhỏ hơn giới hạn phần mềm của Axis_Y ở nhóm cuối.",
        listOf(
            Field("x_travel", "X: hành trình ngang (mm)"),
            Field("z_travel", "Z: hành trình lên xuống (mm)"),
            Field("tilt_angle", "Y: góc lật khi đổ (độ)"),
        ),
    ),
    FieldGroup(
        "Chạy nhanh chậm",
        "Đẩy thẳng xuống PLC, không phải mở TIA.",
        listOf(
            Field("vel_x", "X: tốc độ ngang (mm/s)"),
            Field("vel_z", "Z: tốc độ lên xuống (mm/s)"),
            Field("tilt_vel", "Y: tốc độ lật (độ/s)"),
            Field("dwell_ms", "Dừng ổn định tại rổ (ms)", integer = true),
            Field("tilt_hold_ms", "Giữ ở góc lật (ms)", integer = true),
            Field("tilt_count", "Số lần lật mỗi chu trình", integer = true),
        ),
    ),
    FieldGroup(
        "Vị trí chờ",
        "Nơi máy đứng giữa hai chu trình, chỗ gắn cảm biến.",
        listOf(
            Field("park_x", "X ngang (mm)"),
            Field("park_z", "Z cao (mm)"),
            Field("park_y", "Y góc lật (độ)"),
        ),
    ),
    FieldGroup(
        "Thông số cơ khí",
        "Phải nhập trùng với Technology Object trong TIA — server không ghi được xuống PLC.",
        listOf(
            Field("x_pulses_per_rev", "X: xung/vòng", integer = true),
            Field("x_mm_per_rev", "X: mm/vòng"),
            Field("z_pulses_per_rev", "Z: xung/vòng", integer = true),
            Field("z_mm_per_rev", "Z: mm/vòng"),
            Field("y_pulses_per_rev", "Y: xung/vòng", integer = true),
            Field("y_deg_per_rev", "Y: độ/vòng"),
            Field("y_max_angle", "Y: giới hạn phần mềm (±độ)"),
        ),
    ),
)

val DERIVED_LABELS: Map<String, String> = mapOf(
    "so_ro" to "Số rổ máy xếp được",
    "buoc_ngang_mm" to "Bước ngang giữa 2 rổ (mm)",
    "khe_ho_that_mm" to "Khe hở thật sau khi trải đều (mm)",
    "buoc_hang_mm" to "Bước giữa 2 hàng (mm)",
    "x_pulses_per_mm" to "X — xung mỗi mm",
    "z_pulses_per_mm" to "Z — xung mỗi mm",
    "y_pulses_per_degree" to "Y — xung mỗi độ",
    "x_pulses_full_travel" to "X — xung hết hành trình",
    "z_pulses_full_travel" to "Z — xung hết hành trình",
    "y_pulses_full_range" to "Y — xung hết góc lật",
    "x_max_velocity_mm_s" to "X — tốc độ trần (mm/s)",
    "z_max_velocity_mm_s" to "Z — tốc độ trần (mm/s)",
    "y_max_velocity_deg_s" to "Y — tốc độ trần (°/s)",
)

// So nguyen thi bo duoi ".0" cho o nhap sach, so le thi giu nguyen.
fun formatValue(value: Double, integer: Boolean): String =
    if (integer || value == value.toLong().toDouble()) value.toLong().toString()
    else value.toString()
