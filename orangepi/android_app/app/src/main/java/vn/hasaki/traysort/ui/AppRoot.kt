// Khung ngoai: thanh tieu de, bon tab duoi cung, va may man hinh de len tren
// (quet ma, hoi dia chi server, bao co ban moi).
package vn.hasaki.traysort.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.PanTool
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CenterAlignedTopAppBar
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
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.R
import vn.hasaki.traysort.data.UpdateStage
import vn.hasaki.traysort.ui.parts.Pill
import vn.hasaki.traysort.ui.parts.installOrAskPermission
import vn.hasaki.traysort.ui.parts.Readout
import vn.hasaki.traysort.ui.parts.connectionText
import vn.hasaki.traysort.ui.screens.ConfigScreen
import vn.hasaki.traysort.ui.screens.DiagramScreen
import vn.hasaki.traysort.ui.screens.FirstRunScreen
import vn.hasaki.traysort.ui.screens.LogScreen
import vn.hasaki.traysort.ui.screens.OperateScreen
import vn.hasaki.traysort.ui.screens.ScannerScreen
import vn.hasaki.traysort.ui.screens.SettingsScreen
import vn.hasaki.traysort.ui.theme.LocalBrand

private enum class Tab(val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector) {
    OPERATE("Vận hành", Icons.Filled.PanTool),
    DIAGRAM("Sơ đồ", Icons.Filled.Dashboard),
    CONFIG("Cài đặt máy", Icons.Filled.Tune),
    LOG("Nhật ký", Icons.Filled.Description),
    SETTINGS("Hệ thống", Icons.Filled.Settings),
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppRoot(vm: AppViewModel, state: UiState) {
    val brand = LocalBrand.current
    var tab by remember { mutableStateOf(Tab.OPERATE) }
    var scanning by remember { mutableStateOf(false) }
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

    if (scanning) {
        ScannerScreen(
            onResult = { code -> scanning = false; vm.scan(code) },
            onClose = { scanning = false },
        )
        return
    }

    val pane = LocalPane.current

    Scaffold(
        topBar = { TopBar(state) },
        // Man ngang thi thanh dieu huong nam doc ben trai: chieu cao la thu
        // hiem nhat tren tablet ngang, khong nen cat mot dai o duoi cung.
        bottomBar = {
            if (!pane.wide) {
                NavigationBar {
                    Tab.entries.forEach { entry ->
                        NavigationBarItem(
                            selected = tab == entry,
                            onClick = { tab = entry },
                            icon = { Icon(entry.icon, contentDescription = entry.label) },
                            label = { Text(entry.label, style = MaterialTheme.typography.labelSmall) },
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
                            icon = { Icon(entry.icon, contentDescription = entry.label) },
                            label = { Text(entry.label, style = MaterialTheme.typography.labelSmall) },
                        )
                    }
                }
            }

            Column(Modifier.weight(1f).fillMaxSize()) {
                if (state.running != null) {
                    LinearProgressIndicator(Modifier.fillMaxWidth().height(2.dp))
                }
                when (tab) {
                    Tab.OPERATE -> OperateScreen(state, vm, onOpenScanner = { scanning = true })
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
            title = { Text("Có bản ${available.release.versionName}") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(
                        available.release.notes.ifBlank { "Bản mới đã sẵn trên máy chủ." },
                        style = MaterialTheme.typography.bodySmall,
                    )
                    if (available.release.size > 0) {
                        Text(
                            "Dung lượng ${available.release.size / 1_048_576} MB",
                            style = MaterialTheme.typography.labelSmall,
                            color = brand.muted,
                        )
                    }
                }
            },
            confirmButton = { TextButton(onClick = vm::downloadUpdate) { Text("Tải và cài") } },
            dismissButton = { TextButton(onClick = vm::dismissUpdate) { Text("Để sau") } },
        )
    }

    (state.update as? UpdateStage.Ready)?.let {
        val context = LocalContext.current
        AlertDialog(
            onDismissRequest = vm::dismissUpdate,
            title = { Text("Đã tải xong ${it.release.versionName}") },
            text = {
                Text(
                    "Android sẽ hỏi xác nhận trước khi cài đè lên bản đang chạy. " +
                        "Lần đầu máy còn xin bật \"cho phép cài từ nguồn này\"."
                )
            },
            confirmButton = {
                TextButton(onClick = { installOrAskPermission(context, vm) }) { Text("Cài đặt") }
            },
            dismissButton = { TextButton(onClick = vm::dismissUpdate) { Text("Để sau") } },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TopBar(state: UiState) {
    val brand = LocalBrand.current
    val status = state.snapshot.status
    val online = state.snapshot.online && status != null

    val tone = when {
        !state.linked -> brand.danger
        !online -> brand.danger
        status!!.error -> brand.danger
        status.busy -> brand.warn
        else -> brand.ok
    }

    Column {
        CenterAlignedTopAppBar(
            navigationIcon = {
                Image(
                    painterResource(R.drawable.logo_hasaki),
                    contentDescription = null,
                    modifier = Modifier.padding(start = 12.dp).size(30.dp),
                )
            },
            title = {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        "SmartTraySort",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        "Hasaki Inside",
                        style = MaterialTheme.typography.labelSmall,
                        color = brand.muted,
                    )
                }
            },
            actions = {
                Pill(
                    text = if (!state.linked) "mất mạng" else connectionText(state.snapshot),
                    color = tone,
                    modifier = Modifier.padding(end = 12.dp),
                )
            },
            colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                containerColor = MaterialTheme.colorScheme.surface,
            ),
        )

        Row(
            Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 12.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Readout("X ngang", status?.x?.let { "%.1f".format(it) } ?: "—", "mm")
            Readout("Y lật", status?.y?.let { "%.1f".format(it) } ?: "—", "°")
            Readout("Z cao", status?.z?.let { "%.1f".format(it) } ?: "—", "mm")
            Readout("Tồn", "${state.summary.totalItems}/${state.summary.totalCapacity}")
            Spacer(Modifier.width(2.dp))
        }
    }
}
