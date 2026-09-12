// Khung ngoai: thanh tieu de, bon tab duoi cung, va may man hinh de len tren
// (quet ma, hoi dia chi server, bao co ban moi).
package vn.hasaki.traysort.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.MotionPhotosAuto
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material.icons.filled.ViewInAr
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.R
import vn.hasaki.traysort.core.LocalS
import vn.hasaki.traysort.core.S
import vn.hasaki.traysort.data.UpdateStage
import vn.hasaki.traysort.ui.parts.installOrAskPermission
import vn.hasaki.traysort.ui.parts.connectionText
import vn.hasaki.traysort.ui.screens.ConfigScreen
import vn.hasaki.traysort.ui.screens.DiagramScreen
import vn.hasaki.traysort.ui.screens.FirstRunScreen
import vn.hasaki.traysort.ui.screens.LogScreen
import vn.hasaki.traysort.ui.screens.OperateScreen
import vn.hasaki.traysort.ui.screens.SettingsScreen
import vn.hasaki.traysort.ui.theme.LocalBrand

private enum class Tab(val icon: androidx.compose.ui.graphics.vector.ImageVector) {
    OPERATE(Icons.Filled.MotionPhotosAuto),
    DIAGRAM(Icons.Filled.Dashboard),
    CONFIG(Icons.Filled.Tune),
    LOG(Icons.Filled.Description),
    SETTINGS(Icons.Filled.Settings),
    ;

    fun label(s: S): String = when (this) {
        OPERATE -> s.tabOperate
        DIAGRAM -> s.tabDiagram
        CONFIG -> s.tabConfig
        LOG -> s.tabLog
        SETTINGS -> s.tabSystem
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppRoot(vm: AppViewModel, state: UiState) {
    val brand = LocalBrand.current
    val s = LocalS.current
    var tab by remember { mutableStateOf(Tab.OPERATE) }
    // Mo hinh 3D bat/tat tu thanh tren, giong nut "Hiện / ẩn mô hình 3D" ben web.
    var show3d by remember { mutableStateOf(true) }
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(Unit) { vm.alerts.collect { snackbar.showSnackbar(it) } }

    // Hoi ban moi mot lan sau khi da biet dia chi server.
    LaunchedEffect(state.serverUrl) {
        if (state.serverUrl.isNotBlank()) vm.checkUpdate(loud = false)
    }

    if (!state.bootstrapped) return

    if (!state.configured) {
        FirstRunScreen(onSave = vm::setServer)
        return
    }

    // Man hinh quet bang camera da go: xuong dung sung quet ma, ma vao thang
    // nhu go ban phim. Giu mot duong quet bang camera tren tablet chi de day
    // them mot nut khong ai bam vao giao dien, va keo theo ca ML Kit + CameraX.
    val pane = LocalPane.current

    Scaffold(
        topBar = {
            TopBar(
                state = state,
                onToggleLang = vm::toggleLang,
                show3d = show3d,
                onToggle3d = { show3d = !show3d },
            )
        },
        // Man ngang thi thanh dieu huong nam doc ben trai: chieu cao la thu
        // hiem nhat tren tablet ngang, khong nen cat mot dai o duoi cung.
        bottomBar = {
            if (!pane.wide) {
                NavigationBar {
                    Tab.entries.forEach { entry ->
                        NavigationBarItem(
                            selected = tab == entry,
                            onClick = { tab = entry },
                            icon = { Icon(entry.icon, contentDescription = entry.label(s)) },
                            label = { Text(entry.label(s), style = MaterialTheme.typography.labelSmall) },
                        )
                    }
                }
            }
        },
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Row(Modifier.fillMaxSize().padding(padding)) {
            if (pane.wide) {
                NavigationRail(containerColor = MaterialTheme.colorScheme.surface) {
                    Spacer(Modifier.height(8.dp))
                    Tab.entries.forEach { entry ->
                        NavigationRailItem(
                            selected = tab == entry,
                            onClick = { tab = entry },
                            icon = { Icon(entry.icon, contentDescription = entry.label(s)) },
                            label = { Text(entry.label(s), style = MaterialTheme.typography.labelSmall) },
                        )
                    }
                }
            }

            Column(Modifier.weight(1f).fillMaxSize()) {
                if (state.running != null) {
                    LinearProgressIndicator(Modifier.fillMaxWidth().height(2.dp))
                }
                when (tab) {
                    Tab.OPERATE -> OperateScreen(
                        state = state,
                        vm = vm,
                        show3d = show3d,
                    )
                    Tab.DIAGRAM -> DiagramScreen(state)
                    Tab.CONFIG -> ConfigScreen(state, vm)
                    Tab.LOG -> LogScreen(state, vm)
                    Tab.SETTINGS -> SettingsScreen(state, vm)
                }
            }
        }
    }

    // Bao co ban moi ngay khi mo app. Bam "Để sau" thi khong hoi lai trong
    // phien nay - nhac lai o tab He thong la du.
    (state.update as? UpdateStage.Available)?.let { available ->
        AlertDialog(
            onDismissRequest = vm::dismissUpdate,
            title = { Text(s.updateTitle(available.release.versionName)) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(
                        available.release.notes.ifBlank { s.updateFallback },
                        style = MaterialTheme.typography.bodySmall,
                    )
                    if (available.release.size > 0) {
                        Text(
                            s.updateSize(available.release.size / 1_048_576),
                            style = MaterialTheme.typography.labelSmall,
                            color = brand.muted,
                        )
                    }
                }
            },
            confirmButton = { TextButton(onClick = vm::downloadUpdate) { Text(s.updateDownload) } },
            dismissButton = { TextButton(onClick = vm::dismissUpdate) { Text(s.later) } },
        )
    }

    (state.update as? UpdateStage.Ready)?.let {
        val context = LocalContext.current
        AlertDialog(
            onDismissRequest = vm::dismissUpdate,
            title = { Text(s.updateReady(it.release.versionName)) },
            text = {
                Text(
                    "Android sẽ hỏi xác nhận trước khi cài đè lên bản đang chạy. " +
                        "Lần đầu máy còn xin bật \"cho phép cài từ nguồn này\"."
                )
            },
            confirmButton = {
                TextButton(onClick = { installOrAskPermission(context, vm) }) { Text(s.install) }
            },
            dismissButton = { TextButton(onClick = vm::dismissUpdate) { Text(s.later) } },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TopBar(
    state: UiState,
    onToggleLang: () -> Unit,
    show3d: Boolean,
    onToggle3d: () -> Unit,
) {
    val brand = LocalBrand.current
    val pane = LocalPane.current
    val s = LocalS.current
    val status = state.snapshot.status
    val online = state.snapshot.online && status != null

    val tone = when {
        !state.linked -> brand.danger
        !online -> brand.danger
        status!!.error -> brand.danger
        status.busy -> brand.warn
        else -> brand.ok
    }

    // Thanh tren la dai gradient xanh Hasaki, chu trang - dung cong thuc cua
    // .topbar ben web (#2e7d5b -> #3f9670). Truoc day thanh nay mau surface
    // trang nen app khong ra chat Hasaki, du bang mau con lai da lay tu web.
    Box(
        Modifier
            .fillMaxWidth()
            .background(Brush.horizontalGradient(listOf(brand.barStart, brand.barEnd))),
    ) {
        Column {
            TopAppBar(
                navigationIcon = {
                    Image(
                        painterResource(R.drawable.logo_hasaki),
                        contentDescription = null,
                        modifier = Modifier.padding(start = 12.dp).size(34.dp),
                    )
                },
                title = {
                    Column {
                        Text(
                            "SmartTraySort",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = Color.White,
                        )
                        Text(
                            "Hasaki Inside",
                            style = MaterialTheme.typography.labelSmall,
                            color = Color.White.copy(alpha = 0.85f),
                        )
                    }
                },
                actions = {
                    // Man ngang thi tri so nam ngay tren thanh, canh phai, sat
                    // chip trang thai. Man doc khong du cho nen xuong dai duoi.
                    if (pane.wide) {
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(14.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            BarReadouts(state, status)
                        }
                        Spacer(Modifier.width(14.dp))
                    }
                    BarPill(
                        text = if (!state.linked) s.offline else connectionText(state.snapshot, s),
                        dot = tone,
                    )
                    Spacer(Modifier.width(10.dp))
                    BarIconButton(
                        describe = if (show3d) s.hide3d else s.show3d,
                        onClick = onToggle3d,
                        active = show3d,
                    ) {
                        Icon(
                            Icons.Filled.ViewInAr,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(20.dp),
                        )
                    }
                    Spacer(Modifier.width(8.dp))
                    // Bam mot cai la doi tieng, khong phai vao Cai dat - giong
                    // .icon-btn tren thanh xanh ben web.
                    BarIconButton(describe = s.switchLang, onClick = onToggleLang) {
                        Text(
                            s.otherLangCode,
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = Color.White,
                        )
                    }
                    Spacer(Modifier.width(14.dp))
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
            )

            if (!pane.wide) {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState())
                        .padding(start = 12.dp, end = 12.dp, bottom = 10.dp),
                    horizontalArrangement = Arrangement.spacedBy(14.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    BarReadouts(state, status)
                    Spacer(Modifier.width(2.dp))
                }
            }
        }
    }
}

/** Nut vuong tren thanh xanh - .icon-btn ben web. */
@Composable
private fun BarIconButton(
    describe: String,
    onClick: () -> Unit,
    active: Boolean = false,
    content: @Composable () -> Unit,
) {
    Box(
        Modifier
            .size(38.dp)
            .clip(RoundedCornerShape(10.dp))
            .background(Color.White.copy(alpha = if (active) 0.30f else 0.16f))
            .clickable(onClick = onClick)
            .semantics { contentDescription = describe },
        contentAlignment = Alignment.Center,
    ) { content() }
}

/** Bon tri so tren thanh xanh: nhan mo, so trang dam, chu so deu be - .readout. */
@Composable
private fun BarReadouts(state: UiState, status: vn.hasaki.traysort.data.PlcStatus?) {
    BarReadout("X", status?.x?.let { "%.1f".format(it) } ?: "—", "mm")
    BarReadout("Y", status?.y?.let { "%.1f".format(it) } ?: "—", "°")
    BarReadout("Z", status?.z?.let { "%.1f".format(it) } ?: "—", "mm")
    BarReadout(
        LocalS.current.stock,
        "${state.summary.totalItems}/${state.summary.totalCapacity}",
        null,
    )
}

@Composable
private fun BarReadout(label: String, value: String, unit: String?) {
    Row(verticalAlignment = Alignment.Bottom) {
        Text(
            label,
            style = MaterialTheme.typography.labelMedium,
            color = Color.White.copy(alpha = 0.75f),
        )
        Spacer(Modifier.width(5.dp))
        Text(
            value,
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.Bold,
            color = Color.White,
        )
        if (unit != null) {
            Spacer(Modifier.width(2.dp))
            Text(
                unit,
                style = MaterialTheme.typography.labelSmall,
                color = Color.White.copy(alpha = 0.75f),
            )
        }
    }
}

/** Chip trang thai tren thanh xanh: nen trang mo, chu trang, cham doi mau. */
@Composable
private fun BarPill(text: String, dot: Color, modifier: Modifier = Modifier) {
    Row(
        modifier
            .clip(CircleShape)
            .background(Color.White.copy(alpha = 0.16f))
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(9.dp).clip(CircleShape).background(dot))
        Spacer(Modifier.width(7.dp))
        Text(
            text,
            style = MaterialTheme.typography.labelMedium,
            color = Color.White,
            maxLines = 1,
        )
    }
}
