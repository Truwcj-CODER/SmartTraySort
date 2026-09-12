// Mo hinh 3D cua may, keo de xoay. Dung lai dung mo hinh cua web
// (app/static/js/viz.js + .viz3d trong styles.css), tung mieng mot:
//
//   san  -> ray truc X -> tram cho -> gian ro -> cot dung + dau cong tac
//
// Web ghep bang CSS transform (perspective + preserve-3d). Compose khong co thu
// tuong duong nen o day tu chieu diem, roi sap cac mat theo do sau va ve tu xa
// den gan (painter's algorithm). Khong dung GPU shader nao.
//
// Cho quan trong nhat, va la cho ban dau lam sai: RO LA HOP HO. Mieng ro nam o
// cao do rack_z, bon thanh thong XUONG duoi mieng dung bang basket_height, day
// ro o duoi cung. Ve ro thanh hop dac thi hai day ro de len nhau thanh mot dam,
// khong con nhin ra cai gi.
//
// He toa do (mm, giong so PLC bao), goc dat tai tram cho nhu ben web:
//   x  chay ngang theo hanh trinh truc X, tinh tu park_x
//   y  chieu sau - day phai o +, day trai o - (theo truong dir cua tung ro)
//   z  cao theo hanh trinh truc Z
package vn.hasaki.traysort.ui.parts

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import vn.hasaki.traysort.data.GeometryMap
import vn.hasaki.traysort.data.PlcStatus
import vn.hasaki.traysort.data.Slot
import vn.hasaki.traysort.ui.theme.LocalBrand
import kotlin.math.cos
import kotlin.math.sin

/** To sam mot mau lai - dung cho mat quay ve phia nguoi xem. */
private fun shade(c: Color, by: Float) = Color(
    red = c.red * by,
    green = c.green * by,
    blue = c.blue * by,
    alpha = c.alpha,
)

private data class P3(val x: Float, val y: Float, val z: Float)

/** Mot mat da chieu xuong man, kem do sau de sap thu tu ve. */
private class Face(
    val pts: List<Offset>,
    val depth: Float,
    val fill: Color,
    val stroke: Color,
    val strokeWidth: Float,
    val dashed: Boolean = false,
)

/** Nhan noi tren mieng ro. Ve sau cung, trong khong gian man nen luon doc duoc. */
private class Tag(val at: Offset, val depth: Float, val slot: Slot)

@Composable
fun Machine3D(
    geometry: GeometryMap,
    slots: List<Slot>,
    status: PlcStatus?,
    selected: Int?,
    modifier: Modifier = Modifier,
) {
    val brand = LocalBrand.current
    val scheme = MaterialTheme.colorScheme
    val measurer = rememberTextMeasurer()

    // Huong ngang lay cua web (VIEW_START.azim = -32). Con goc nga thi KHONG
    // lay 16 do cua web: khung ben web cao 460 px va hep, con o day khung rong
    // va thap nen o 16 do ca gian ro trong nhu mot dai det, va thanh ro phia gan
    // che het long ro. 34 do la muc thay duoc vao trong tung cai ro.
    var azim by remember { mutableFloatStateOf(-32f) }
    var elev by remember { mutableFloatStateOf(34f) }

    fun g(key: String, fallback: Double) = (geometry[key] ?: fallback).toFloat()

    val xTravel = g("x_travel", 1250.0).coerceAtLeast(1f)
    val zTravel = g("z_travel", 400.0).coerceAtLeast(1f)
    val basketLen = g("basket_length", 200.0)
    val basketDep = g("basket_depth", 200.0)
    val wallH = g("basket_height", 60.0)
    val rackOffset = g("rack_offset", 95.0)
    val plateLen = g("tray_length", 220.0)
    val plateDep = g("tray_width", 200.0)
    val parkX = g("park_x", 5.0)
    val parkZ = g("park_z", 200.0)

    val headX by animateFloatAsState(
        (status?.x ?: 0f).coerceIn(0f, xTravel), tween(220), label = "m3d-x",
    )
    val headZ by animateFloatAsState(
        (status?.z ?: 0f).coerceIn(0f, zTravel), tween(220), label = "m3d-z",
    )
    val tilt by animateFloatAsState(status?.y ?: 0f, tween(220), label = "m3d-y")

    val activeSlot = if (status?.busy == true && status.slot > 0) status.slot else null

    Box(
        modifier
            .clip(RoundedCornerShape(12.dp))
            .background(brand.surfaceAlt)
            .pointerInput(Unit) {
                detectDragGestures { _, drag ->
                    azim -= drag.x * 0.35f
                    elev = (elev + drag.y * 0.3f).coerceIn(-12f, 74f)
                }
            },
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val a = Math.toRadians(azim.toDouble())
            val e = Math.toRadians(elev.toDouble())
            val ca = cos(a).toFloat(); val sa = sin(a).toFloat()
            val ce = cos(e).toFloat(); val se = sin(e).toFloat()

            // Goc toa do o tram cho, giong fromPark() ben web.
            fun fx(x: Float) = x - parkX

            val halfDepth = rackOffset + basketDep + 110f
            val cx = fx(xTravel) / 2f
            val cz = zTravel / 2f
            val dist = maxOf(xTravel, zTravel, halfDepth * 2f) * 2.4f

            fun raw(p: P3): Triple<Float, Float, Float> {
                val x = p.x - cx
                val z = p.z - cz
                val x1 = x * ca - p.y * sa
                val y1 = x * sa + p.y * ca
                val sy = -(z * ce) + y1 * se
                val depth = y1 * ce + z * se
                val f = dist / (dist + depth)
                return Triple(x1 * f, sy * f, depth)
            }

            // Tu khit khung: chieu 8 goc hop bao roi do be ngang/cao that tren
            // man. Web co the dung mot he so co dinh vi khung cao co dinh 460px;
            // o day khung cao bao nhieu la do bo cuc, nen phai do moi lan.
            // Khit theo hop bao cua GIAN RO + hanh trinh, khong theo tam san.
            // San rong hon gian ro nhieu (them 80 mm moi ben va ca vung trong
            // truoc/sau), lay no lam moc thi mo hinh bi thu nho lai va dat lech
            // ve mot goc khung.
            val rackDepth = rackOffset + basketDep
            val box = listOf(-1f, 1f).flatMap { sx ->
                listOf(-1f, 1f).flatMap { sy ->
                    listOf(0f, 1f).map { sz ->
                        raw(P3(cx + sx * fx(xTravel) / 2f, sy * rackDepth, sz * zTravel))
                    }
                }
            }
            val spanX = (box.maxOf { it.first } - box.minOf { it.first }).coerceAtLeast(1f)
            val spanY = (box.maxOf { it.second } - box.minOf { it.second }).coerceAtLeast(1f)
            val midX = (box.maxOf { it.first } + box.minOf { it.first }) / 2f
            val midY = (box.maxOf { it.second } + box.minOf { it.second }) / 2f
            val pad = 12f
            val scale = minOf(
                (size.width - pad * 2) / spanX,
                (size.height - pad * 2) / spanY,
            )

            fun project(p: P3): Pair<Offset, Float> {
                val (rx, ry, depth) = raw(p)
                return Offset(
                    size.width / 2f + (rx - midX) * scale,
                    size.height / 2f + (ry - midY) * scale,
                ) to depth
            }

            val faces = mutableListOf<Face>()

            fun addFace(
                corners: List<P3>,
                fill: Color,
                stroke: Color,
                strokeWidth: Float = 1f,
                dashed: Boolean = false,
            ) {
                val proj = corners.map { project(it) }
                faces += Face(
                    pts = proj.map { it.first },
                    depth = proj.sumOf { it.second.toDouble() }.toFloat() / proj.size,
                    fill = fill,
                    stroke = stroke,
                    strokeWidth = strokeWidth,
                    dashed = dashed,
                )
            }

            /** Tam nam ngang o cao do z. */
            fun pad(x0: Float, x1: Float, y0: Float, y1: Float, z: Float, fill: Color, stroke: Color, w: Float = 1f, dashed: Boolean = false) =
                addFace(
                    listOf(P3(x0, y0, z), P3(x1, y0, z), P3(x1, y1, z), P3(x0, y1, z)),
                    fill, stroke, w, dashed,
                )

            /** Thanh dung song song truc X, dat tai chieu sau y. */
            fun wallX(x0: Float, x1: Float, y: Float, z0: Float, z1: Float, fill: Color, stroke: Color, w: Float = 1f) =
                addFace(
                    listOf(P3(x0, y, z0), P3(x1, y, z0), P3(x1, y, z1), P3(x0, y, z1)),
                    fill, stroke, w,
                )

            /** Thanh dung song song truc Y, dat tai hoanh do x. */
            fun wallY(y0: Float, y1: Float, x: Float, z0: Float, z1: Float, fill: Color, stroke: Color, w: Float = 1f) =
                addFace(
                    listOf(P3(x, y0, z0), P3(x, y1, z0), P3(x, y1, z1), P3(x, y0, z1)),
                    fill, stroke, w,
                )

            // ---------------------------------------------------------- san may
            // Web ve san bang hai repeating-linear-gradient 36 px, opacity .35 -
            // tuc mot LUOI O chu khong phai tam dac. Luoi cho mat diem tua de
            // uoc luong khoang cach; tam dac thi chi lam nen phang.
            run {
                val x0 = fx(0f) - 80f; val x1 = fx(xTravel) + 80f
                val step = 120f
                val grid = brand.line.copy(alpha = 0.75f)
                var gx = x0
                while (gx <= x1) {
                    val a = project(P3(gx, -halfDepth, 0f)).first
                    val b = project(P3(gx, halfDepth, 0f)).first
                    drawLine(grid, a, b, strokeWidth = 1f)
                    gx += step
                }
                var gy = -halfDepth
                while (gy <= halfDepth) {
                    val a = project(P3(x0, gy, 0f)).first
                    val b = project(P3(x1, gy, 0f)).first
                    drawLine(grid, a, b, strokeWidth = 1f)
                    gy += step
                }
            }

            // ------------------------------------------------------ ray truc X
            // Ray nam DUOI SAN - .viz3d__rail ben web la mot dai rotateX(90deg),
            // tuc mot thanh det nam ngang. Cot truc Z dung LEN tu xe con chay
            // tren ray nay. Ban dau ve ray tren dinh voi cot thong xuong la nguoc
            // hoan toan so voi may that.
            pad(
                fx(0f), fx(xTravel),
                -14f, 14f,
                0f,
                brand.muted.copy(alpha = 0.55f), brand.muted, 1.2f,
            )

            // ---------------------------------------------------- tram cho
            pad(
                -plateLen / 2f, plateLen / 2f,
                -plateDep / 2f, plateDep / 2f,
                parkZ,
                Color.Transparent, brand.ok.copy(alpha = 0.75f), 1.4f, dashed = true,
            )

            // ------------------------------------------------------- gian ro
            val tags = mutableListOf<Tag>()
            slots.forEach { row ->
                // Mau lay dung tu .viz3d__slot ben web: cai ro la vat the XAM
                // TRANG (thanh = --surface-2, day = --surface, vien = --line),
                // gan nhu dac (opacity .92). Mau chi xuat hien khi CO TRANG THAI:
                // vien xanh khi ro day, ca ro vang khi may dang chay toi.
                //
                // Ban dau to xanh moi cai ro voi alpha 15-72% - thanh ra nhin
                // xuyen qua nhau, ca gian ro la mot dam kinh xanh, khong ra hinh
                // cai may nao.
                val target = row.slot == activeSlot
                val picked = row.slot == selected
                val lower = row.row > 0

                // Web dat thanh ro mau --surface-2, ma nen khung .viz3d cung la
                // --surface-2. Tren theme TOI (anh mau cua web) hai mau do lech
                // nhau du de thay; tren theme SANG chung trung nhau, chi con
                // vien --line rat nhat nen ca gian ro gan nhu vo hinh.
                //
                // Nen o day khong copy y nguyen: thanh ro to TRANG cho noi len
                // khoi nen xam, long ro xam hon thanh de nhin ra do sau, va vien
                // dung --muted thay vi --line cho ranh gioi ro rang.
                val wallFill = when {
                    target -> brand.warn.copy(alpha = 0.55f)
                    lower -> scheme.surface
                    else -> scheme.surface
                }
                val plateFill = when {
                    target -> brand.warn.copy(alpha = 0.38f)
                    else -> brand.line
                }
                val edge = when {
                    target -> brand.warn
                    picked -> scheme.primary
                    row.full -> brand.ok
                    else -> brand.muted.copy(alpha = 0.55f)
                }
                val lw = if (picked || target) 2.4f else 1.3f

                val cxs = fx(row.x)
                // rack_offset la khoang tu tam ray toi MEP TRONG cua ro, nen tam
                // ro con xa hon nua be sau - dung cong thuc cua web.
                val cy = row.dir * (rackOffset + basketDep / 2f)
                val x0 = cxs - basketLen / 2f; val x1 = cxs + basketLen / 2f
                val y0 = cy - basketDep / 2f; val y1 = cy + basketDep / 2f
                val mouth = row.rackZ
                val floor = mouth - wallH

                // day ro
                pad(x0, x1, y0, y1, floor, plateFill, edge, lw)

                // DU BON THANH - cai ro phai ra cai ro. Da thu bo hai thanh
                // phia gan cho de nhin vao long, nhung bo di thi con ba mat,
                // khong con la cai hop nua. Nhin duoc vao long la viec cua GOC
                // NGHIENG: o 16 do, thanh cao 60 mm chieu ra ~58 don vi con day
                // ro sau 200 mm chi chieu ra ~55, tuc thanh gan che het day; tu
                // ~34 do tro len thi day ro chieu ra ~112, ho ra thay ro.
                //
                // Thanh phia gan camera to sam hon thanh phia xa - do la cach
                // mot cai hop that hien ra khoi, khong phai mot dam mat phang.
                val mid = (floor + mouth) / 2f
                val here = project(P3((x0 + x1) / 2f, (y0 + y1) / 2f, mid)).second
                listOf(
                    Triple(project(P3((x0 + x1) / 2f, y0, mid)).second, 0, y0),
                    Triple(project(P3((x0 + x1) / 2f, y1, mid)).second, 0, y1),
                    Triple(project(P3(x0, (y0 + y1) / 2f, mid)).second, 1, x0),
                    Triple(project(P3(x1, (y0 + y1) / 2f, mid)).second, 1, x1),
                ).forEach { (depth, kind, at) ->
                    val near = depth < here
                    val fill = if (near && !target) shade(wallFill, 0.90f) else wallFill
                    if (kind == 0) {
                        wallX(x0, x1, at, floor, mouth, fill, edge, lw)
                    } else {
                        wallY(y0, y1, at, floor, mouth, fill, edge, lw)
                    }
                }

                // Nhan chim vao long ro mot doan ngan tinh tu mieng - du de thay
                // no nam TRONG hop, chua sat day.
                val (at, d) = project(P3(cxs, cy, mouth - wallH * 0.32f))
                tags += Tag(at, d, row)
            }

            // ------------------------------- cot dung + dau cong tac + khay lat
            val mastW = 26f
            val hx = fx(headX)
            // Xe con chay tren ray, cot truc Z dung len tu do - hai tam vuong
            // goc nhau cho ra cam giac cot vuong, giong mastA/mastB ben web.
            pad(
                hx - mastW, hx + mastW,
                -mastW, mastW,
                0f,
                brand.ok.copy(alpha = 0.45f), brand.ok, 1.4f,
            )
            wallX(hx - mastW / 2f, hx + mastW / 2f, 0f, 0f, zTravel, brand.ok.copy(alpha = 0.30f), brand.ok, 1.2f)
            wallY(-mastW / 2f, mastW / 2f, hx, 0f, zTravel, brand.ok.copy(alpha = 0.22f), brand.ok, 1.2f)

            // Dau cong tac: hai tam nho vuong goc tai cao do Z hien tai.
            wallX(hx - plateLen * 0.22f, hx + plateLen * 0.22f, 0f, headZ, headZ + 34f, brand.ok.copy(alpha = 0.5f), brand.ok, 1.4f)
            wallY(-plateDep * 0.22f, plateDep * 0.22f, hx, headZ, headZ + 34f, brand.ok.copy(alpha = 0.4f), brand.ok, 1.4f)

            // Mam khay + vat dang mang. Mam LAT quanh tam no theo goc truc Y -
            // dung nhu .viz3d__plate ben web (rotateX(90 - y), tam quay o giua
            // mam). Truoc day o day chi ve mot DUONG THANG xoay, nen tren man
            // trong nhu mot cai cay chong lat qua lat lai chu khong ra cai mam
            // do vat.
            run {
                val t = Math.toRadians(tilt.toDouble())
                val ct = cos(t).toFloat()
                val st = sin(t).toFloat()
                val plateZ = headZ + 34f

                // Mam nam ngang khi goc 0. Lat thi mep phia +Y (day PHAI, phia
                // gan nguoi xem) ha xuong, mep -Y nang len - vat truot ve phia
                // do ma roi vao ro.
                fun corner(dx: Float, dy: Float) = P3(hx + dx, dy * ct, plateZ - dy * st)

                fun tipped(halfLen: Float, halfDep: Float, fill: Color, stroke: Color, w: Float) =
                    addFace(
                        listOf(
                            corner(-halfLen, -halfDep),
                            corner(halfLen, -halfDep),
                            corner(halfLen, halfDep),
                            corner(-halfLen, halfDep),
                        ),
                        fill, stroke, w,
                    )

                tipped(plateLen / 2f, plateDep / 2f, brand.ok.copy(alpha = 0.55f), brand.ok, 1.8f)
                // Vat dang nam tren mam, neo vao giua mam - .viz3d__load.
                tipped(plateLen * 0.21f, plateDep * 0.21f, brand.warn.copy(alpha = 0.9f), brand.warn, 1.2f)
            }

            // Ve tu xa den gan.
            faces.sortByDescending { it.depth }
            val dash = PathEffect.dashPathEffect(floatArrayOf(9f, 7f))
            faces.forEach { f ->
                val path = Path().apply {
                    moveTo(f.pts[0].x, f.pts[0].y)
                    for (i in 1 until f.pts.size) lineTo(f.pts[i].x, f.pts[i].y)
                    close()
                }
                if (f.fill != Color.Transparent) drawPath(path, f.fill)
                drawPath(
                    path,
                    f.stroke,
                    style = Stroke(
                        width = f.strokeWidth,
                        pathEffect = if (f.dashed) dash else null,
                    ),
                )
            }

            // Nhan so ro: ve sau cung. LUON ve so - truoc day co dieu kien khung
            // phai cao hon 200 dp moi ve, nen o dai duoi tab Van hanh (chi ~180
            // dp) toan bo so ro bien mat, trong nhu chua gan gi. Chi dong ma
            // quet ben duoi la an khi khung hep, va co chu thi nho lai theo khung.
            drawTags(
                tags = tags,
                measurer = measurer,
                activeSlot = activeSlot,
                selected = selected,
                tagBg = brand.tagBg,
                line = brand.line,
                ink = scheme.onSurface,
                muted = brand.muted,
                warn = brand.warn,
                warnInk = Color(0xFF201704),
                ok = brand.ok,
                // Rong toi thieu bang be ngang cai ro, giong buildTag ben web.
                // Vua khit con so, khong keo rong bang ca cai ro - de con thay hop.
                minWidth = 0f,
                // Web luon hien dong nay, khong co nguong nao.
                // Chi ghi so ro - dong ma/so luong lam nhan to ra, che mat hop.
                withSub = false,
                small = size.height < 260.dp.toPx(),
            )
        }
    }
}

private fun DrawScope.drawTags(
    tags: List<Tag>,
    measurer: TextMeasurer,
    activeSlot: Int?,
    selected: Int?,
    tagBg: Color,
    line: Color,
    ink: Color,
    muted: Color,
    warn: Color,
    warnInk: Color,
    ok: Color,
    minWidth: Float,
    withSub: Boolean,
    small: Boolean,
) {
    // Ve tu xa den gan: the o gan de len the o xa, khong phai nguoc lai.
    tags.sortedByDescending { it.depth }.forEach { tag ->
        val row = tag.slot
        val target = row.slot == activeSlot
        val picked = row.slot == selected
        // The o binh thuong ve mo mot chut: doc duoc nhung van thay no NAM TRONG
        // long ro chu khong noi lo lung. The dang chay / dang chon ve dam de bat mat.
        val faint = !target && !picked

        val numColor = when {
            target -> warnInk
            faint -> ink.copy(alpha = 0.72f)
            else -> ink
        }
        val subColor = if (target) warnInk else muted
        val num = measurer.measure(
            row.slot.toString(),
            TextStyle(
                fontSize = if (small) 12.sp else 15.sp,
                fontWeight = FontWeight.SemiBold,
                color = numColor,
            ),
        )
        val sub = if (!withSub) null else measurer.measure(
            row.code.ifBlank { "${row.count}/${row.capacity}" },
            TextStyle(fontSize = 10.sp, color = subColor),
        )

        val padX = 5.dp.toPx()
        val padY = 3.dp.toPx()
        val w = maxOf(
            minWidth,
            num.size.width + padX * 2,
            (sub?.size?.width ?: 0) + padX * 2,
        )
        val h = num.size.height + (sub?.size?.height ?: 0) + padY * 2
        val left = tag.at.x - w / 2f
        val top = tag.at.y - h / 2f

        // The nhan la mot tam DAC bo goc, khong phai chu tron. Chu tron nam
        // giua mo hinh thi trong nhu so lo lung khong dinh vao dau, va nen phia
        // sau la gi thi chu chim theo. Web giai bang .viz3d__tag: nen --tag-bg
        // (trang 88% / den 78%), vien --line, bo goc 5px.
        drawRoundRect(
            color = if (target) warn
                    else if (faint) tagBg.copy(alpha = tagBg.alpha * 0.5f)
                    else tagBg,
            topLeft = Offset(left, top),
            size = Size(w, h),
            cornerRadius = CornerRadius(5.dp.toPx()),
        )
        drawRoundRect(
            color = when {
                target -> warn
                picked -> ok
                else -> line.copy(alpha = line.alpha * 0.5f)
            },
            topLeft = Offset(left, top),
            size = Size(w, h),
            cornerRadius = CornerRadius(5.dp.toPx()),
            style = Stroke(width = if (picked || target) 2f else 1f),
        )

        drawText(
            num,
            topLeft = Offset(tag.at.x - num.size.width / 2f, top + padY),
        )
        if (sub != null) {
            drawText(
                sub,
                topLeft = Offset(
                    tag.at.x - sub.size.width / 2f,
                    top + padY + num.size.height,
                ),
            )
        }
    }
}
