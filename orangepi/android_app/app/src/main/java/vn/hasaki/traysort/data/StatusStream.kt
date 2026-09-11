// Duong nhan trang thai: mot ket noi SSE giu mo suot, tu noi lai khi rot song.
//
// Vi sao SSE chu khong phai hoi vong: PLC duoc doc moi 200 ms, hoi vong voi
// nhip do la hang nghin request mot phut tren mang xuong. SSE giu dung mot ket
// noi, server day xuong khi co gi moi. Man hinh muot hon ma pin va song deu do.
//
// Ba loai su kien khop voi app/api/sse.py ben server:
//   status     moi vong poll PLC
//   inventory  khi bang ro doi
//   layout     khi cau hinh doi
package vn.hasaki.traysort.data

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.isActive
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import kotlin.coroutines.coroutineContext

sealed interface StreamEvent {
    data class Status(val snapshot: Snapshot) : StreamEvent
    data class Inventory(val payload: SlotsPayload) : StreamEvent
    data class Layout(val payload: GeometryPayload) : StreamEvent
    /** Duong truyen vua len hay vua dut. note co chu khi dut, de ghi nhat ky. */
    data class Link(val connected: Boolean, val note: String? = null) : StreamEvent
}

private const val FIRST_RETRY_MS = 1_000L
private const val MAX_RETRY_MS = 10_000L

class StatusStream(
    private val client: OkHttpClient,
    private val json: Json,
    private val baseUrl: () -> String,
) {
    fun events(): Flow<StreamEvent> = callbackFlow {
        var retry = FIRST_RETRY_MS
        var source: EventSource? = null

        // Moi vong lap la mot lan noi. Rot thi cho roi noi lai, cho lau dan
        // de khong nen server khi no dang tat.
        while (coroutineContext.isActive) {
            val ended = CompletableDeferred<String?>()

            val request = Request.Builder()
                .url(baseUrl().trimEnd('/') + "/api/events")
                .header("Accept", "text/event-stream")
                .header("Cache-Control", "no-cache")
                .build()

            source = EventSources.createFactory(client).newEventSource(
                request,
                object : EventSourceListener() {
                    override fun onOpen(eventSource: EventSource, response: Response) {
                        retry = FIRST_RETRY_MS
                        trySend(StreamEvent.Link(true))
                    }

                    override fun onEvent(
                        eventSource: EventSource,
                        id: String?,
                        type: String?,
                        data: String,
                    ) {
                        val parsed = runCatching {
                            when (type) {
                                "status" -> StreamEvent.Status(json.decodeFromString<Snapshot>(data))
                                "inventory" -> StreamEvent.Inventory(json.decodeFromString<SlotsPayload>(data))
                                "layout" -> StreamEvent.Layout(json.decodeFromString<GeometryPayload>(data))
                                else -> null
                            }
                        }.getOrNull()
                        if (parsed != null) trySend(parsed)
                    }

                    override fun onClosed(eventSource: EventSource) {
                        ended.complete(null)
                    }

                    override fun onFailure(
                        eventSource: EventSource,
                        t: Throwable?,
                        response: Response?,
                    ) {
                        ended.complete(
                            when {
                                response != null && !response.isSuccessful -> "server trả lỗi ${response.code}"
                                t != null -> networkText(t)
                                else -> "mất kết nối"
                            }
                        )
                    }
                },
            )

            val note = ended.await()
            source.cancel()
            source = null
            trySend(StreamEvent.Link(false, note))

            delay(retry)
            retry = (retry * 2).coerceAtMost(MAX_RETRY_MS)
        }

        awaitClose { source?.cancel() }
    }
}
