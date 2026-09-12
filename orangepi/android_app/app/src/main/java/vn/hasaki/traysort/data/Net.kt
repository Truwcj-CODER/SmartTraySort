// Mot OkHttpClient duy nhat cho ca app, va bo doc JSON di kem.
//
// SSE can readTimeout = 0: duong truyen dung yen hang phut la chuyen binh
// thuong, cat di la sai. Lenh REST thi nguoc lai - phai co han, khong thi bam
// nut xong man hinh treo mai. Nen tach lam hai: chung connection pool, khac
// moi han doc.
package vn.hasaki.traysort.data

import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit

object Net {
    val json: Json = Json {
        ignoreUnknownKeys = true      // server them khoa moi, app cu khong vo
        isLenient = true
        encodeDefaults = true
        explicitNulls = false
    }

    private val base: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

    // Lenh: co han, hong thi bao ngay. Nhung "Luu cau hinh" day ca bang toa do
    // xuong PLC - moi ro mot lenh Modbus, cho PLC that xac nhan tung cai, 50 ro
    // la ngot 15 giay. De han 15s thi lan nao cung SocketTimeout giua chung roi
    // app im lim, khong biet xong hay hong. 90s du cho bang lon nhat.
    val rest: OkHttpClient = base.newBuilder()
        .readTimeout(90, TimeUnit.SECONDS)
        .writeTimeout(90, TimeUnit.SECONDS)
        .build()

    // Dong su kien: khong han doc, nhung van ping de biet duong da chet.
    val stream: OkHttpClient = base.newBuilder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(20, TimeUnit.SECONDS)
        .build()
}
