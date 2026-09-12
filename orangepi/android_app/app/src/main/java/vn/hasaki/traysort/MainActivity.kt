// Mot Activity duy nhat. Compose lo phan con lai.
package vn.hasaki.traysort

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.ui.Modifier
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.LocalConfiguration
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import vn.hasaki.traysort.core.LocalS
import vn.hasaki.traysort.core.S
import vn.hasaki.traysort.ui.AppRoot
import vn.hasaki.traysort.ui.AppViewModel
import vn.hasaki.traysort.ui.LocalPane
import vn.hasaki.traysort.ui.paneFor
import vn.hasaki.traysort.ui.theme.TraySortTheme

class MainActivity : ComponentActivity() {

    private val vm: AppViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)

        setContent {
            val state by vm.state.collectAsStateWithLifecycle()

            // Do be ngang mot lan o day roi ca app bam theo. Xoay may la
            // LocalConfiguration doi, moi thu tu xep lai.
            val pane = paneFor(LocalConfiguration.current.screenWidthDp)

            // enableEdgeToEdge() cho app ve tran ra sau thanh he thong, va tu
            // do app phai TU chua cho ban phim. Khong chua thi ban phim bung
            // len de len o dang go - hoac tren may ao la khong ve ra gi ca.
            TraySortTheme(state.theme, pane.scale) {
                CompositionLocalProvider(
                    LocalPane provides pane,
                    LocalS provides S(state.lang),
                ) {
                    Box(
                        Modifier
                            .fillMaxSize()
                            .imePadding()
                            .navigationBarsPadding(),
                    ) {
                        AppRoot(vm, state)
                    }
                }
            }
        }
    }

    // Roi app trong luc dang giu nut jog thi may phai dung lai ngay.
    override fun onStop() {
        vm.releaseAllJog()
        super.onStop()
    }
}
