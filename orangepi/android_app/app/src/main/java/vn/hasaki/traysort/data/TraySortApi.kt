// Lop goi REST duy nhat cua app. Khong cham toi Compose, khong giu trang thai.
//
// Doi xung voi app/static/js/api.js ben web: cung mot danh sach endpoint, cung
// mot cach doi loi HTTP thanh ApiException. Them lenh moi thi them mot ham o
// day, khong sua cho nao khac.
package vn.hasaki.traysort.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.IOException
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

private val JSON_TYPE = "application/json; charset=utf-8".toMediaType()

@Serializable private data class MoveBody(val x: Double, val z: Double)
@Serializable private data class TiltBody(val angle: Double)
@Serializable private data class AmountBody(val amount: Int)
@Serializable private data class ScanBody(val code: String, val run: Boolean)
@Serializable private data class SlotConfigBody(val code: String? = null, val capacity: Int? = null)
@Serializable private data class CalibrateBody(
    val axis: String,
    val commanded: Double,
    val measured: Double,
)

class TraySortApi(
    private val client: OkHttpClient,
    private val json: Json,
    private val baseUrl: () -> String,
) {
    /* ------------------------------------------------------------- trang thai */
    suspend fun status(): Snapshot = fetch("GET", "/api/status", null)

    suspend fun slots(): SlotsPayload = fetch("GET", "/api/slots", null)

    /* ------------------------------------------------------- lenh theo tung ro */
    suspend fun runSlot(slot: Int): CommandOut = fetch("POST", "/api/slots/$slot/run", "{}")
    suspend fun gotoSlot(slot: Int): CommandOut = fetch("POST", "/api/slots/$slot/goto", "{}")
    suspend fun tiltSlot(slot: Int): CommandOut = fetch("POST", "/api/slots/$slot/tilt", "{}")
    suspend fun teachSlot(slot: Int): CommandOut = fetch("POST", "/api/slots/$slot/teach", "{}")

    /* ---------------------------------------------------------------- lenh chung */
    suspend fun home(): CommandOut = fetch("POST", "/api/home", "{}")
    suspend fun park(): CommandOut = fetch("POST", "/api/park", "{}")

    // LIMIT la diem cam bien, co dinh theo co khi. HOME la cho may dung nghi,
    // nguoi van hanh tu dat bang parkHere(). Truoc day hai cai nay dung chung
    // mot toa do trong PLC nen bam nut nao cung ve mot cho.
    suspend fun parkHere(): CommandOut = fetch("POST", "/api/park/here", "{}")
    suspend fun stop(): CommandOut = fetch("POST", "/api/stop", "{}")
    suspend fun reset(): CommandOut = fetch("POST", "/api/reset", "{}")

    suspend fun moveTo(x: Double, z: Double): CommandOut =
        fetch("POST", "/api/move", encode(MoveBody(x, z)))

    suspend fun tiltTo(angle: Double): CommandOut =
        fetch("POST", "/api/tilt", encode(TiltBody(angle)))

    // Giu nut jog ban lien tuc, khong doc noi dung tra ve lam gi.
    suspend fun jog(bits: JogBits) {
        raw("POST", "/api/jog", encode(bits))
    }

    /* ------------------------------------------------------------------ ton kho */
    // Ba ham duoi khong tra ve bang moi: duong SSE se day su kien inventory
    // ngay sau do. Doc them mot lan nua chi lam hai ban ghi da nhau.
    suspend fun addItems(slot: Int, amount: Int = 1) {
        raw("POST", "/api/slots/$slot/items", encode(AmountBody(amount)))
    }

    suspend fun removeItems(slot: Int, amount: Int = 1) {
        raw("DELETE", "/api/slots/$slot/items?amount=$amount", null)
    }

    suspend fun resetInventory() {
        raw("POST", "/api/inventory/reset", "{}")
    }

    suspend fun setSlotConfig(slot: Int, code: String?, capacity: Int?) {
        raw("PUT", "/api/slots/$slot/config", encode(SlotConfigBody(code, capacity)))
    }

    /* ------------------------------------------------------------------- quet ma */
    suspend fun scan(code: String, run: Boolean = true): ScanOut =
        fetch("POST", "/api/scan", encode(ScanBody(code, run)))

    /* ------------------------------------------------------------------ cau hinh */
    // Don hang dang gan o mot ro: tung SKU da vao hay chua.
    suspend fun orderAt(slot: Int): OrderEnvelope = fetch("GET", "/api/orders/$slot", null)

    suspend fun geometry(): GeometryPayload = fetch("GET", "/api/config/geometry", null)

    suspend fun saveGeometry(values: GeometryMap): GeometrySaved =
        fetch("PUT", "/api/config/geometry", json.encodeToString(values))

    suspend fun pushTable(): CommandOut = fetch("POST", "/api/config/push", "{}")

    /* ---------------------------------------------------------------- hieu chinh */
    // Tinh thu, khong ghi gi. Bam bao nhieu lan cung duoc.
    suspend fun calibratePreview(axis: String, commanded: Double, measured: Double): Calibration =
        fetch("POST", "/api/calibrate/preview", encode(CalibrateBody(axis, commanded, measured)))

    // Ghi ti le moi vao cau hinh roi day xuong PLC.
    suspend fun calibrateApply(axis: String, commanded: Double, measured: Double): CalibrationApplied =
        fetch("POST", "/api/calibrate/apply", encode(CalibrateBody(axis, commanded, measured)))

    /* --------------------------------------------------------------------- noi bo */
    private inline fun <reified T> encode(value: T): String = json.encodeToString(value)

    private suspend inline fun <reified T> fetch(method: String, path: String, body: String?): T =
        json.decodeFromString(raw(method, path, body))

    // Duy nhat mot cho ban goi tin di. Moi endpoint deu qua day nen cach bao loi
    // giong nhau tuyet doi, khong endpoint nao "quen" bat loi mang.
    suspend fun raw(method: String, path: String, body: String?): String = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url(baseUrl().trimEnd('/') + path)
            .method(method, body?.toRequestBody(JSON_TYPE))
            .header("Accept", "application/json")
            .build()

        client.newCall(request).await().use {
            val text = it.body?.string().orEmpty()
            if (!it.isSuccessful) throw ApiException(detailOf(json, text, it.code), it.code)
            text
        }
    }
}

// OkHttp goi lai bang callback; doi thanh suspend de goi tu coroutine cho gon.
private suspend fun Call.await(): Response = suspendCancellableCoroutine { cont ->
    cont.invokeOnCancellation { runCatching { cancel() } }
    enqueue(object : Callback {
        override fun onFailure(call: Call, e: IOException) {
            if (cont.isActive) cont.resumeWithException(ApiException(networkText(e), 0))
        }

        override fun onResponse(call: Call, response: Response) {
            if (cont.isActive) cont.resume(response) else response.close()
        }
    })
}

// Cau bao loi mang phai doc duoc ngoai xuong, khong phai ten lop Java.
internal fun networkText(e: Throwable): String = when (e) {
    is java.net.SocketTimeoutException -> "server không trả lời kịp"
    is java.net.ConnectException -> "không kết nối được tới server"
    is java.net.UnknownHostException -> "không tìm thấy địa chỉ server"
    else -> e.message ?: "lỗi mạng"
}
