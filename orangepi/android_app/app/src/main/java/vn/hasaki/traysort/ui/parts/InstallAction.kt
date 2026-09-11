// Bam "Cai dat" thi phai co chuyen gi do xay ra, ke ca khi chua co quyen.
//
// Android 8 tro len bat app xin rieng quyen "cai tu nguon nay". Kiem tra ngay
// luc bam chu khong luc ve man hinh: nguoi dung vua cap quyen xong bam quay lai
// thi lan bam ke tiep phai chay duoc, khong doi ve lai man hinh moi nhan ra.
package vn.hasaki.traysort.ui.parts

import android.content.Context
import android.content.Intent
import vn.hasaki.traysort.ui.AppViewModel

fun installOrAskPermission(context: Context, vm: AppViewModel) {
    if (vm.updaterCanInstall()) {
        vm.installUpdate()
    } else {
        context.startActivity(vm.installPermissionIntent().addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }
}
