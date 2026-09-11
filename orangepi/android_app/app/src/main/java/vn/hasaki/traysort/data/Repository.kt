// Rap ba manh lai: dia chi server tu Prefs, lenh REST, va dong su kien SSE.
//
// Doi dia chi trong Cai dat thi flatMapLatest cat ket noi cu va mo ket noi moi
// - khong con cho nao con giu dia chi cu.
package vn.hasaki.traysort.data

import android.content.Context
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.onEach
import vn.hasaki.traysort.core.Prefs

class Repository(private val prefs: Prefs) {

    @Volatile
    private var current: String = ""

    val api = TraySortApi(Net.rest, Net.json) { current }
    private val stream = StatusStream(Net.stream, Net.json) { current }

    val serverUrl: Flow<String> = prefs.serverUrl.onEach { current = it }.distinctUntilChanged()

    fun updater(context: Context) = Updater(context, api) { current }

    @OptIn(ExperimentalCoroutinesApi::class)
    fun events(): Flow<StreamEvent> = serverUrl.flatMapLatest { url ->
        if (url.isBlank()) emptyFlow() else stream.events()
    }
}
