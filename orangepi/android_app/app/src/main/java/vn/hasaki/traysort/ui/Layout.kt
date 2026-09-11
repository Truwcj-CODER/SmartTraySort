// Man hinh rong bao nhieu thi xep kieu nao.
//
// Dien thoai doc va tablet ngang la hai the gioi khac nhau: mot cot keo gian ra
// 1200 px thi vua trong vua kho doc, ma nhet hai cot vao man 5 inch thi khong
// cho nao bam duoc. Nen do be ngang mot lan roi ca app bam theo.
//
// Nguong lay theo Material window size class: 600 dp va 840 dp.
package vn.hasaki.traysort.ui

import androidx.compose.runtime.staticCompositionLocalOf

enum class Pane {
    /** Dien thoai dung. Mot cot, thanh dieu huong duoi cung. */
    COMPACT,

    /** Tablet nho hoac dien thoai ngang. Mot cot rong hon, chu to hon. */
    MEDIUM,

    /** Tablet ngang. Hai khung canh nhau, thanh dieu huong doc ben trai. */
    EXPANDED,
    ;

    val wide: Boolean get() = this == EXPANDED

    // Nguoi van hanh doc man hinh tu xa nua met, dung dung co chu cua dien thoai
    // cho tablet. He so nay nhan vao ca bo chu - giong bien --z ben CSS cua web.
    val scale: Float
        get() = when (this) {
            COMPACT -> 1.00f
            MEDIUM -> 1.10f
            EXPANDED -> 1.20f
        }
}

fun paneFor(widthDp: Int): Pane = when {
    widthDp >= 840 -> Pane.EXPANDED
    widthDp >= 600 -> Pane.MEDIUM
    else -> Pane.COMPACT
}

val LocalPane = staticCompositionLocalOf { Pane.COMPACT }
