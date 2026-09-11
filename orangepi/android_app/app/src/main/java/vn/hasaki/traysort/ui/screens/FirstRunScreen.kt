// Man hinh dau tien: app chua biet server o dau thi khong lam gi duoc, nen hoi
// truoc roi moi cho vao.
package vn.hasaki.traysort.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import vn.hasaki.traysort.R
import vn.hasaki.traysort.core.Prefs
import vn.hasaki.traysort.ui.theme.LocalBrand

@Composable
fun FirstRunScreen(onSave: (String) -> Unit) {
    val brand = LocalBrand.current
    var draft by remember { mutableStateOf(Prefs.SUGGESTED) }

    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        // Kep be ngang lai: o nhap dai het man tablet thi khong ai biet no bat
        // dau tu dau.
        Column(
            Modifier.fillMaxSize().padding(28.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
          Column(
            Modifier.widthIn(max = 520.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
          ) {
            Image(painterResource(R.drawable.logo_hasaki), null, Modifier.size(84.dp))
            Text("SmartTraySort", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(
                "Nhập địa chỉ máy chủ trên Orange Pi để bắt đầu.",
                style = MaterialTheme.typography.bodyMedium,
                color = brand.muted,
            )
            OutlinedTextField(
                value = draft,
                onValueChange = { draft = it },
                label = { Text("Địa chỉ máy chủ") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Text(
                "Gõ IP là đủ, ví dụ 192.168.1.20 — app tự thêm http:// và cổng 8000.",
                style = MaterialTheme.typography.labelSmall,
                color = brand.muted,
            )
            Button(
                onClick = { onSave(draft) },
                enabled = draft.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Kết nối") }
          }
        }
    }
}
