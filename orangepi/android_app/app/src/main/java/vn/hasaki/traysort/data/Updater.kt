// Tu cap nhat qua WiFi. Khong co Play Store trong nha xuong, nen server tu lam
// noi phat ban moi: mot file APK va mot to khai ben canh.
//
// Ba buoc, khong buoc nao duoc bo:
//   1. Hoi /api/app/latest xem so hieu ban tren server la bao nhieu
//   2. Lon hon ban dang cai thi tai APK ve thu muc rieng cua app
//   3. Doi chieu SHA-256 roi moi goi trinh cai dat cua Android
//
// Buoc 3 la cho khong duoc cat: tai qua HTTP tran trong mang noi bo thi khong
// co gi bao dam goi tin khong bi sua doc duong. Ma bam khop moi cai.
package vn.hasaki.traysort.data

import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import okhttp3.Request
import java.io.File
import java.security.MessageDigest

@Serializable
data class AppRelease(
    @SerialName("version_code") val versionCode: Int = 0,
    @SerialName("version_name") val versionName: String = "",
    @SerialName("sha256") val sha256: String = "",
    @SerialName("size") val size: Long = 0,
    val notes: String = "",
    @SerialName("published_at") val publishedAt: String = "",
    /** Duong dan tuong doi toi file APK tren chinh server nay. */
    val url: String = "/api/app/download",
)

sealed interface UpdateStage {
    data object Idle : UpdateStage
    data object Checking : UpdateStage
    data class Available(val release: AppRelease) : UpdateStage
    data class Downloading(val percent: Int) : UpdateStage
    data class Ready(val file: File, val release: AppRelease) : UpdateStage
    data class Failed(val reason: String) : UpdateStage
    data object UpToDate : UpdateStage
}

class Updater(
    private val context: Context,
    private val api: TraySortApi,
    private val baseUrl: () -> String,
) {
    /** Ban tren server co moi hon ban dang chay khong. */
    suspend fun check(currentCode: Int): AppRelease? {
        val body = api.raw("GET", "/api/app/latest", null)
        val release = Net.json.decodeFromString<AppRelease>(body)
        return release.takeIf { it.versionCode > currentCode }
    }

    // Tai ve thu muc cache rieng cua app roi doi chieu ma bam. Sai mot bit la
    // xoa file va bao loi - khong bao gio dua mot goi cai dat dang ngo cho
    // he thong.
    suspend fun download(release: AppRelease, onProgress: (Int) -> Unit): File =
        withContext(Dispatchers.IO) {
            val target = File(context.cacheDir, "update.apk")
            target.delete()

            val request = Request.Builder()
                .url(baseUrl().trimEnd('/') + release.url)
                .build()

            Net.rest.newBuilder()
                .readTimeout(5, java.util.concurrent.TimeUnit.MINUTES)
                .build()
                .newCall(request).execute().use { response ->
                    if (!response.isSuccessful) error("server trả lỗi ${response.code}")
                    val body = response.body ?: error("server không gửi nội dung")
                    val total = if (release.size > 0) release.size else body.contentLength()

                    body.byteStream().use { input ->
                        target.outputStream().use { output ->
                            val buffer = ByteArray(64 * 1024)
                            var done = 0L
                            var last = -1
                            while (true) {
                                val read = input.read(buffer)
                                if (read <= 0) break
                                output.write(buffer, 0, read)
                                done += read
                                if (total > 0) {
                                    val percent = (done * 100 / total).toInt().coerceIn(0, 100)
                                    if (percent != last) { last = percent; onProgress(percent) }
                                }
                            }
                        }
                    }
                }

            val actual = sha256(target)
            if (release.sha256.isNotBlank() && !actual.equals(release.sha256, ignoreCase = true)) {
                target.delete()
                error("mã băm không khớp — file tải về có thể hỏng")
            }
            target
        }

    // Android 8 tro len bat buoc nguoi dung tu bam dong y cai. App chi mo duoc
    // man hinh cai dat, phan quyet dinh van la cua ho.
    fun install(file: File) {
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.updates", file)
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    /** Android 8+ moi co man hinh "cho phep cai app tu nguon nay". */
    fun canInstall(): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.O ||
            context.packageManager.canRequestPackageInstalls()

    fun installPermissionIntent(): Intent =
        Intent(android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)
            .setData(android.net.Uri.parse("package:${context.packageName}"))

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val read = input.read(buffer)
                if (read <= 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
