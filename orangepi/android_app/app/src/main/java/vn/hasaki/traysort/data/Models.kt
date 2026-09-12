// Hinh dang du lieu server tra ve. Chi khai bao, khong xu ly gi.
//
// Moi truong deu co gia tri mac dinh: server them mot khoa moi thi app cu van
// doc duoc, khong phai cap nhat cung luc hai ben.
package vn.hasaki.traysort.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonPrimitive

@Serializable
data class PlcStatus(
    val ready: Boolean = false,
    val busy: Boolean = false,
    val done: Boolean = false,
    val homed: Boolean = false,
    val error: Boolean = false,
    val step: Int = 0,
    @SerialName("error_id") val errorId: Int = 0,
    @SerialName("ack_seq") val ackSeq: Int = 0,
    @SerialName("done_seq") val doneSeq: Int = 0,
    val result: Int = 0,
    val x: Float = 0f,
    val y: Float = 0f,
    val z: Float = 0f,
    val slot: Int = 0,
    @SerialName("result_text") val resultText: String = "",
    @SerialName("error_id_hex") val errorIdHex: String = "0x0000",
    /** Trang thai cac chan cam bien, khoa la ten chan: "I0.0", "I0.1", "I0.7"... */
    val inputs: Map<String, Boolean> = emptyMap(),
)

@Serializable
data class Snapshot(
    val online: Boolean = false,
    val endpoint: String = "",
    @SerialName("last_error") val lastError: String? = null,
    @SerialName("slot_count") val slotCount: Int = 0,
    val status: PlcStatus? = null,
)

// Mot ro: toa do do hinh hoc sinh ra, so vat do ton kho giu. Server ghep san.
@Serializable
data class Slot(
    val slot: Int = 0,
    val x: Float = 0f,
    val z: Float = 0f,
    @SerialName("rack_z") val rackZ: Float = 0f,
    val dir: Int = 1,
    val row: Int = 0,
    val column: Int = 0,
    val side: String = "phai",
    val code: String = "",
    val count: Int = 0,
    val capacity: Int = 0,
    val full: Boolean = false,
    @SerialName("updated_at") val updatedAt: String? = null,
) {
    val ratio: Float get() = if (capacity > 0) count.toFloat() / capacity else 0f
}

@Serializable
data class Summary(
    @SerialName("total_items") val totalItems: Int = 0,
    @SerialName("total_capacity") val totalCapacity: Int = 0,
    @SerialName("slot_count") val slotCount: Int = 0,
    @SerialName("full_slots") val fullSlots: Int = 0,
    @SerialName("empty_slots") val emptySlots: Int = 0,
    @SerialName("fill_percent") val fillPercent: Float = 0f,
)

@Serializable
data class SlotsPayload(
    val slots: List<Slot> = emptyList(),
    val summary: Summary = Summary(),
)

@Serializable
data class LayoutPlan(
    val rows: Int = 0,
    val columns: Int = 0,
    val slots: Int = 0,
    @SerialName("columns_by_travel") val columnsByTravel: Int = 0,
    val capped: Boolean = false,
)

// Cau hinh hinh hoc: toan so, nen giu nguyen dang ban do ten -> gia tri.
//
// Giao dien dung bang mo ta truong (xem ui/GeometryFields.kt) de ve form, nen
// server them mot thong so moi chi phai sua mot dong o day, khong phai them
// truong vao lop du lieu roi sua tiep cho doc, cho ghi.
typealias GeometryMap = Map<String, Double>

@Serializable
data class GeometryPayload(
    val geometry: GeometryMap = emptyMap(),
    val layout: LayoutPlan = LayoutPlan(),
    val positions: List<Slot> = emptyList(),
    val derived: Map<String, JsonElement> = emptyMap(),
    val problems: List<String> = emptyList(),
    @SerialName("speed_warnings") val speedWarnings: List<String> = emptyList(),
) {
    // derived tron chuoi va so - lay ra dang chu de hien thang len man hinh.
    fun derivedText(): List<Pair<String, String>> = derived.map { (key, value) ->
        key to ((value as? JsonPrimitive)?.content ?: value.toString())
    }
}

// Mot don hang dang nam o mot ro: gom nhung SKU nao, da vao duoc may mon.
@Serializable
data class OrderItem(val sku: String = "", val scanned: Boolean = false)

@Serializable
data class OrderDetail(
    val order: String = "",
    val slot: Int = 0,
    val count: Int = 0,
    val capacity: Int = 0,
    val items: List<OrderItem> = emptyList(),
    val done: Int = 0,
    val total: Int = 0,
    val complete: Boolean = false,
)

@Serializable
data class OrderEnvelope(val order: OrderDetail = OrderDetail())

@Serializable
data class Orphan(val slot: Int = 0, val count: Int = 0, val code: String = "")

// Ket qua mot lan hieu chinh truc: ti le dang dung, ti le de nghi, va cau chu
// bao phai go gi sang TIA.
//
// current/proposed la ban do ten -> so vi ten o doi theo truc (x_mm_per_rev hay
// y_deg_per_rev). Truong "field" noi ro o nao, nen giao dien khong phai doan.
@Serializable
data class ScaleSide(
    @SerialName("pulses_per_unit") val pulsesPerUnit: Double = 0.0,
    @SerialName("pulses_full_range") val pulsesFullRange: Long = 0,
    @SerialName("max_velocity") val maxVelocity: Double = 0.0,
)

@Serializable
data class Calibration(
    val axis: String = "",
    val unit: String = "",
    val commanded: Double = 0.0,
    val measured: Double = 0.0,
    @SerialName("error_factor") val errorFactor: Double = 1.0,
    val field: String = "",
    val current: ScaleSide = ScaleSide(),
    val proposed: ScaleSide = ScaleSide(),
    @SerialName("gear_ratio") val gearRatio: Double? = null,
    @SerialName("tia_note") val tiaNote: String = "",
    val warnings: List<String> = emptyList(),
) {
    /** Truc chay dung ti le thi he so bang 1 - lech duoi 0.5% coi nhu dung. */
    val onTarget: Boolean get() = kotlin.math.abs(errorFactor - 1.0) < 0.005
}

@Serializable
data class CalibrationApplied(
    val ok: Boolean = true,
    val geometry: GeometryMap = emptyMap(),
    val pushed: String? = null,
    @SerialName("push_ok") val pushOk: Boolean? = null,
    @SerialName("speed_warnings") val speedWarnings: List<String> = emptyList(),
    val calibration: Calibration = Calibration(),
)

@Serializable
data class GeometrySaved(
    val ok: Boolean = true,
    val geometry: GeometryMap = emptyMap(),
    val layout: LayoutPlan = LayoutPlan(),
    val problems: List<String> = emptyList(),
    val pushed: String? = null,
    // Co boolean tu server. Truoc day app phai do chuoi pushed co bat dau bang
    // "CHUA" hay khong - doi mot chu trong cau la app bao thanh cong sai.
    @SerialName("push_ok") val pushOk: Boolean? = null,
    @SerialName("speed_warnings") val speedWarnings: List<String> = emptyList(),
    val orphans: List<Orphan> = emptyList(),
)

@Serializable
data class CommandOut(
    val ok: Boolean = true,
    val message: String = "",
    val status: PlcStatus? = null,
)

@Serializable
data class ScanOut(
    val ok: Boolean = true,
    val code: String = "",
    val slot: Int = 0,
    val message: String = "",
    val status: PlcStatus? = null,
)

@Serializable
data class JogBits(
    @SerialName("x_pos") val xPos: Boolean = false,
    @SerialName("x_neg") val xNeg: Boolean = false,
    @SerialName("y_pos") val yPos: Boolean = false,
    @SerialName("y_neg") val yNeg: Boolean = false,
    @SerialName("z_pos") val zPos: Boolean = false,
    @SerialName("z_neg") val zNeg: Boolean = false,
) {
    val anyHeld: Boolean get() = xPos || xNeg || yPos || yNeg || zPos || zNeg

    fun with(direction: String, held: Boolean): JogBits = when (direction) {
        "x_pos" -> copy(xPos = held)
        "x_neg" -> copy(xNeg = held)
        "y_pos" -> copy(yPos = held)
        "y_neg" -> copy(yNeg = held)
        "z_pos" -> copy(zPos = held)
        "z_neg" -> copy(zNeg = held)
        else -> this
    }
}

@Serializable
private data class ErrorBody(val detail: String? = null)

// Server tra loi bang {"detail": "..."} - moi lop tren chi thay cau chu.
class ApiException(message: String, val code: Int) : Exception(message)

internal fun detailOf(json: kotlinx.serialization.json.Json, body: String, code: Int): String =
    runCatching { json.decodeFromString<ErrorBody>(body).detail }.getOrNull()
        ?: body.take(200).ifBlank { "lỗi HTTP $code" }
