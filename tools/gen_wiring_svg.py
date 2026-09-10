#!/usr/bin/env python3
# Sinh MOT file SVG gom ca ba phan:
#
#   1. Ngo ra  — PLC dieu khien ba driver step
#   2. Ngo vao — cac cong tac va cam bien
#   3. Bo tri  — cam bien gan o dau tren may
#   4. Mach dieu khien — CB, den bao, nut Start, nut E-Stop, relay K1
#
# File thu hai: SoDoDauDayThucTe.svg — ve dung tung con trong tu, co so coc.
#
#   python tools/gen_wiring_svg.py
#
# Sinh tu code chu khong ve tay de toa do luon khop: doi mot con so trong phan
# khai bao la ca so do tu can lai, khong co chuyen day noi lech vai pixel.
from __future__ import annotations

import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

DOCS = Path(__file__).resolve().parent.parent / "docs"
OUT = DOCS / "SoDoDauDay.svg"
OUT2 = DOCS / "SoDoDauDayThucTe.svg"

W = 1560
SEC = [0, 1140, 2180, 3060]    # goc y cua tung phan
H = 4360
H2 = 1330                      # to "dau day thuc te"

INK, MUTED, LINE = "#12171f", "#5b6676", "#9aa6b5"
AX = {"X": "#cf4437", "Z": "#2b7fd4", "Y": "#2f9c52"}
V_PLUS, ZERO_V, DANGER = "#d4380d", "#111111", "#d4380d"
OKG = "#2f9c52"                # xanh la — trang thai "dang chay"

# (truc, model, vai tro, cac cap Q, y dinh khoi trong phan 1)
DRIVERS = [
    ("X", "HBS86H v4", "chạy ngang — hybrid servo vòng kín",
     [("PUL", "Q0.0"), ("DIR", "Q0.1"), ("ENA", "Q0.4")], 150),
    ("Z", "3DH583", "lên xuống — step 3 pha",
     [("PUL", "Q0.2"), ("DIR", "Q0.3"), ("ENA", "Q0.5")], 420),
    ("Y", "ASD556R-LW", "lật trái phải — step 2 pha",
     [("PUL", "Q0.6"), ("DIR", "Q0.7"), ("ENA", "Q1.0")], 690),
]

PLC_PINS = ["3L+", "Q0.0", "Q0.1", "Q0.2", "Q0.3", "Q0.4",
            "Q0.5", "Q0.6", "Q0.7", "Q1.0", "Q1.1", "3M"]

# (chan, ten, truc, ai doc)
INPUTS = [
    ("I0.0", "STOP_BTN", "",  "SCL"),
    ("I0.1", "X_MIN",    "X", "TO"),
    ("I0.2", "X_MAX",    "X", "TO"),
    ("I0.3", "Z_HOME",   "Z", "TO"),
    ("I0.4", "Z_MIN",    "Z", "TO"),
    ("I0.5", "Z_MAX",    "Z", "TO"),
    ("I0.6", "Y_HOME",   "Y", "TO"),
    ("I0.7", "ESTOP_OK", "",  "SCL"),
    ("I1.0", "X_HOME",   "X", "TO"),
]

parts: list[str] = []
add = parts.append
dy = 0                          # goc y cua phan dang ve


# ------------------------------------------------------------------- ve co ban
def text(x, y, s, size=13, fill=INK, anchor="start", weight="400", mono=False):
    family = ("ui-monospace, SFMono-Regular, Consolas, monospace" if mono
              else "Segoe UI, system-ui, -apple-system, sans-serif")
    add(f'<text x="{x}" y="{y + dy}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}" '
        f'font-family="{family}">{escape(s)}</text>')


def box(x, y, w, h, fill, stroke, rx=8, sw=2, dash=""):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x}" y="{y + dy}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}"{extra}/>')


def wire(pts, color=INK, sw=2, dash=""):
    d = " ".join(f"{'M' if i == 0 else 'L'} {x} {y + dy}" for i, (x, y) in enumerate(pts))
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
        f'stroke-linecap="round" stroke-linejoin="round"{extra}/>')


def dot(x, y, color=INK, r=5):
    add(f'<circle cx="{x}" cy="{y + dy}" r="{r}" fill="{color}"/>')


def circle(x, y, r, fill, stroke, sw=3):
    add(f'<circle cx="{x}" cy="{y + dy}" r="{r}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}"/>')


def terminal(x, y, color=INK):
    add(f'<rect x="{x - 5}" y="{y + dy - 5}" width="10" height="10" rx="2" '
        f'fill="#fff" stroke="{color}" stroke-width="2"/>')


# Hai chan + thanh gat nhac cheo len. Dung chung cho ca NO lan NC de hai ky
# hieu la anh em, chi khac dung mot chi tiet: NC co them vach chan o dau co dinh
# (dung IEC 60617) — nhin la biet ngay tiep diem nao dang dong.
def _contact(x, y, w, color, closed):
    x0, y0 = x + 10, y - 2
    x1, y1 = x + w - 6, y - 18
    dot(x, y, color, 4)
    dot(x + w, y, color, 4)
    wire([(x, y), (x + 10, y)], color, 2)
    wire([(x + w - 10, y), (x + w, y)], color, 2)
    wire([(x0, y0), (x1, y1)], color, 2.5)
    if closed:
        dx, dy = x1 - x0, y1 - y0
        n = (dx * dx + dy * dy) ** 0.5
        px, py = -dy / n * 11, dx / n * 11
        wire([(x1 - px, y1 - py), (x1 + px, y1 + py)], color, 2.5)
    return x + w


# Tiep diem thuong DONG — co vach chan.
def contact_nc(x, y, w=60, color=INK):
    return _contact(x, y, w, color, True)


# Tiep diem thuong MO — khong vach chan.
def contact_no(x, y, w=60, color=INK):
    return _contact(x, y, w, color, False)


# Den bao: vong tron co dau X ben trong (ky hieu IEC).
def lamp(x, y, r, color, label="", sub=""):
    circle(x, y, r, "#fff", color, 3)
    k = r * 0.62
    wire([(x - k, y - k), (x + k, y + k)], color, 2.5)
    wire([(x - k, y + k), (x + k, y - k)], color, 2.5)
    if label:
        text(x, y + r + 20, label, 11, color, "middle", "700")
    if sub:
        text(x, y + r + 35, sub, 10, MUTED, "middle")


# Cuon hut cua relay / contactor.
def coil(x, y, w, h, label, color=INK):
    box(x, y, w, h, "#fff", color, rx=4, sw=2)
    text(x + w / 2, y + h / 2 + 6, label, 16, color, "middle", "700")
    return x + w


# CB hai cuc: hai cuc rieng, noi nhau bang net dut (lien dong co khi).
def mcb_2p(x, y1, y2, w=70, color=INK):
    for yy in (y1, y2):
        dot(x, yy, color, 4)
        dot(x + w, yy, color, 4)
        wire([(x, yy), (x + 12, yy)], color, 2.5)
        wire([(x + w - 12, yy), (x + w, yy)], color, 2.5)
        wire([(x + 12, yy), (x + w - 6, yy - 20)], color, 3)
        wire([(x + w - 22, yy - 11), (x + w - 30, yy - 19)], color, 2.5)
    wire([(x + w * 0.52, y1 - 6), (x + w * 0.52, y2 - 20)], color, 2, dash="4 4")
    return x + w


# Hop thiet bi: khung + may dong chu o giua. Coc ve rieng bang pin_*.
def devbox(x, y, w, h, color, lines, t0=26):
    box(x, y, w, h, "#fff", color, rx=6, sw=2)
    for k, (s_, size, weight) in enumerate(lines):
        text(x + w / 2, y + t0 + k * 17, s_, size,
             color if k == 0 else MUTED, "middle", weight)


# Coc dau day. Nhan luon quay VAO TRONG hop — ben ngoai danh cho day chay,
# neu de nhan ra ngoai la day dam thang vao chu.
def pin_t(x, y, lbl, color=INK):      # coc tren mep TREN
    terminal(x, y, color)
    text(x, y + 20, lbl, 11, color, "middle", "700", mono=True)


def pin_b(x, y, lbl, color=INK):      # coc tren mep DUOI
    terminal(x, y, color)
    text(x, y - 11, lbl, 11, color, "middle", "700", mono=True)


def pin_l(x, y, lbl, color=INK):      # coc tren mep TRAI
    terminal(x, y, color)
    text(x + 13, y + 4, lbl, 11, color, "start", "700", mono=True)


def pin_r(x, y, lbl, color=INK):      # coc tren mep PHAI
    terminal(x, y, color)
    text(x - 13, y + 4, lbl, 11, color, "end", "700", mono=True)


# So hieu day, in tren chinh soi day do.
def tag(x, y, n, color=INK):
    circle(x, y, 11, "#ffffff", color, 2)
    text(x, y + 4, str(n), 10, color, "middle", "700")


def heading(n, title, sub):
    box(60, 24, W - 120, 58, "#f4f7fb", "#1f3a5f", rx=10, sw=2)
    circle(96, 53, 18, "#1f3a5f", "#1f3a5f")
    text(96, 59, str(n), 18, "#ffffff", "middle", "700")
    text(126, 49, title, 20, INK, weight="700")
    text(126, 70, sub, 12, MUTED)


def notes_box(x, y, w, h, title, items, wrap=40):
    box(x, y, w, h, "#fbfcfd", LINE, sw=1)
    text(x + 18, y + 30, title, 14, INK, weight="700")
    cy = y + 58
    for head, body in items:
        text(x + 18, cy, "▸ " + head, 12, INK, weight="700")
        lines = textwrap.wrap(body, wrap)
        for k, line in enumerate(lines):
            text(x + 28, cy + 17 + k * 15, line, 11, MUTED)
        cy += 17 + 15 * len(lines) + 14


# =========================================================== 1. NGO RA
def section_outputs():
    heading(1, "Ngõ RA — PLC điều khiển ba driver step",
            "S7-1200 CPU 1214C DC/DC/DC · ngõ ra PNP 24 V · driver opto 5 V · "
            "đấu common cathode")

    plc_x, plc_y, plc_w = 70, 170, 250
    pin_top, pin_gap = 222, 46
    res_x, res_w = 430, 86
    drv_x, drv_w, drv_h = 700, 330, 210
    minus_bus, motor_x = 660, 1160
    rail_0v, rail_vp = 985, 1035
    psu_x, psu_y, psu_w, psu_h = 70, 925, 250, 125

    plc_h = pin_top + pin_gap * (len(PLC_PINS) - 1) - plc_y + 60
    box(plc_x, plc_y, plc_w, plc_h, "#eef3fa", "#1f3a5f")
    text(plc_x + plc_w / 2, plc_y + 34, "PLC", 20, "#1f3a5f", "middle", "700")
    text(plc_x + plc_w / 2, plc_y + 56, "CPU 1214C DC/DC/DC", 12, MUTED, "middle")

    used = {q for _, _, _, pairs, _ in DRIVERS for _, q in pairs}
    pin_y = {}
    for i, name in enumerate(PLC_PINS):
        y = pin_top + i * pin_gap
        pin_y[name] = y
        color = INK if name in used or name in ("3L+", "3M") else LINE
        terminal(plc_x + plc_w, y, color)
        text(plc_x + plc_w - 14, y + 4, name, 13, color, "end", "600", mono=True)

    text(plc_x + plc_w + 16, pin_y["3L+"] + 4, "24 V cấp cho nhóm ngõ ra", 11, MUTED)
    text(plc_x + plc_w + 16, pin_y["3M"] + 4, "0 V nhóm ngõ ra", 11, MUTED)
    text(plc_x + plc_w + 16, pin_y["Q1.1"] + 4, "còn trống", 11, LINE)

    for axis, model, role, pairs, top in DRIVERS:
        c = AX[axis]
        box(drv_x, top, drv_w, drv_h, "#fbfbfc", c)
        box(drv_x, top, drv_w, 34, c, c, rx=8, sw=0)
        box(drv_x, top + 20, drv_w, 14, c, c, rx=0, sw=0)
        text(drv_x + 14, top + 23, f"TRỤC {axis}   {model}", 14, "#ffffff", weight="700")
        text(drv_x + 14, top + 52, role, 11, MUTED)

        for k, (sig, q) in enumerate(pairs):
            yp = top + 78 + k * 38
            ym = yp + 17
            terminal(drv_x, yp, c)
            text(drv_x + 12, yp + 4, f"{sig}+", 12, c, "start", "600", mono=True)
            terminal(drv_x, ym, MUTED)
            text(drv_x + 12, ym + 4, f"{sig}−", 12, MUTED, "start", "600", mono=True)

            qy = pin_y[q]
            box(res_x, qy - 13, res_w, 26, "#fff", INK, rx=3, sw=2)
            text(res_x + res_w / 2, qy + 4, "2 kΩ", 12, INK, "middle", "600", mono=True)
            wire([(plc_x + plc_w + 5, qy), (res_x, qy)], c)
            wire([(res_x + res_w, qy), (res_x + res_w + 40, qy),
                  (res_x + res_w + 40, yp), (drv_x - 5, yp)], c)
            wire([(drv_x - 5, ym), (minus_bus, ym)], ZERO_V, 2)

        wire([(minus_bus, top + 95), (minus_bus, rail_0v)], ZERO_V, 3)
        for k in range(3):
            dot(minus_bus, top + 78 + k * 38 + 17, ZERO_V, 4)
        dot(minus_bus, rail_0v, ZERO_V, 6)

        vdc_x, gnd_x = drv_x + 60, drv_x + 150
        terminal(vdc_x, top + drv_h, V_PLUS)
        terminal(gnd_x, top + drv_h, ZERO_V)
        text(vdc_x, top + drv_h + 24, "VDC", 11, V_PLUS, "middle", "600", mono=True)
        text(gnd_x, top + drv_h + 24, "GND", 11, ZERO_V, "middle", "600", mono=True)
        wire([(vdc_x, top + drv_h + 5), (vdc_x, rail_vp)], V_PLUS, 3)
        wire([(gnd_x, top + drv_h + 5), (gnd_x, rail_0v)], ZERO_V, 3)
        dot(vdc_x, rail_vp, V_PLUS, 6)
        dot(gnd_x, rail_0v, ZERO_V, 6)

        my = top + drv_h / 2
        mt = "U V W" if axis == "Z" else "A+ A− B+ B−"
        wire([(drv_x + drv_w, my), (motor_x - 46, my)], INK, 3)
        text((drv_x + drv_w + motor_x - 46) / 2, my - 10, mt, 11, MUTED, "middle", mono=True)
        circle(motor_x, my, 44, "#fff", c)
        text(motor_x, my + 2, "M", 26, c, "middle", "700")
        text(motor_x, my + 22, axis, 12, MUTED, "middle", "600")

        if axis == "X":
            wire([(motor_x, my + 46), (motor_x, my + 74),
                  (drv_x + drv_w - 40, my + 74), (drv_x + drv_w - 40, top + drv_h)],
                 c, 2, dash="7 5")
            text(motor_x - 14, my + 92, "cáp encoder — bắt buộc", 11, c, "end", "600")

    for y, color, label, sub in (
        (rail_0v, ZERO_V, "0 V CHUNG", "nối chung nguồn PLC và nguồn driver"),
        (rail_vp, V_PLUS, "V+ ĐỘNG LỰC", "theo nhãn từng driver, KHÔNG đoán"),
    ):
        wire([(psu_x + 60, y), (motor_x + 90, y)], color, 5)
        text(motor_x + 100, y + 5, label, 13, color, "start", "700")
        text(motor_x + 100, y + 22, sub, 10, MUTED)

    wire([(plc_x + plc_w + 5, pin_y["3M"]), (plc_x + plc_w + 60, pin_y["3M"]),
          (plc_x + plc_w + 60, rail_0v)], ZERO_V, 3)
    dot(plc_x + plc_w + 60, rail_0v, ZERO_V, 6)

    box(psu_x, psu_y, psu_w, psu_h, "#fdf3ef", V_PLUS)
    text(psu_x + psu_w / 2, psu_y + 30, "NGUỒN 48 V", 15, V_PLUS, "middle", "700")
    text(psu_x + psu_w / 2, psu_y + 50, "Meanwell LRS-600-48", 11, MUTED, "middle")
    text(psu_x + psu_w / 2, psu_y + 68, "cục bạc to trong tủ", 10, LINE, "middle")
    terminal(psu_x + 60, psu_y + psu_h, ZERO_V)
    terminal(psu_x + 170, psu_y + psu_h, V_PLUS)
    text(psu_x + 60, psu_y + psu_h + 22, "V−", 12, ZERO_V, "middle", "700", mono=True)
    text(psu_x + 170, psu_y + psu_h + 22, "V+", 12, V_PLUS, "middle", "700", mono=True)
    wire([(psu_x + 60, psu_y + psu_h + 5), (psu_x + 60, rail_0v)], ZERO_V, 5)
    wire([(psu_x + 170, psu_y + psu_h + 5), (psu_x + 170, rail_vp)], V_PLUS, 5)
    dot(psu_x + 60, rail_0v, ZERO_V, 7)
    dot(psu_x + 170, rail_vp, V_PLUS, 7)
    circle(psu_x + 60, rail_0v, 15, "none", V_PLUS, 2)
    text(psu_x + 60, rail_0v - 26, "hai nguồn PHẢI chung 0 V", 12, V_PLUS, "middle", "700")

    notes_box(1245, 170, 250, 300, "ĐỌC KỸ", [
        ("2 kΩ không được bỏ", "PLC ra 24 V, driver opto 5 V. Đấu thẳng là cháy opto."),
        ("Chân − không vào Q", "Ba chân − gom về 0 V, chỉ chân + mới nối ngõ Q."),
        ("ENA thường logic ngược", "Nhiều driver cấp tín hiệu là CẮT. Lần đầu để trống."),
        ("Tên chân khác hãng", "PU±, DR±, MF±, EN± — cùng nghĩa, đọc nhãn."),
        ("Dây chéo không chấm", "= không nối. Có chấm tròn mới là nối."),
    ], wrap=34)


# =========================================================== 2. NGO VAO
def section_inputs():
    heading(2, "Ngõ VÀO — mạch dừng khẩn cấp và các công tắc",
            "Nút dừng khẩn cắt thẳng contactor, không qua PLC. Cảm biến vị trí "
            "dùng Omron EE-SX951 loại khe, ngõ ra NPN nên 1M phải lên 24 V.")

    plc_x, plc_y, plc_w = 900, 190, 260
    pin_top, pin_gap = 272, 46
    sw_x = 560
    rail_24, rail_0 = 150, 880

    wire([(120, rail_24), (1480, rail_24)], DANGER, 5)
    text(120, rail_24 - 14, "24 V", 14, DANGER, "start", "700", mono=True)
    wire([(120, rail_0), (1480, rail_0)], INK, 5)
    text(120, rail_0 + 26, "0 V chung", 14, INK, "start", "700", mono=True)

    box(150, 300, 350, 250, "#fff6f3", DANGER, dash="7 5")
    text(325, 334, "MẠCH DỪNG KHẨN", 15, DANGER, "middle", "700")
    text(325, 356, "vẽ đầy đủ ở PHẦN 4 phía dưới", 12, DANGER, "middle", "700")
    for k, s_ in enumerate((
            "CB1 → đèn đỏ → nút START có đèn → relay K1 tự giữ.",
            "Nút E-Stop cắt cuộn K1; K1 nhả thì contactor K2 cắt",
            "nguồn động lực của ba driver — hoàn toàn phần cứng,",
            "không đi qua chương trình PLC.",
            "",
            "Ở đây chỉ vẽ nhánh báo tin về chân I0.7.")):
        text(172, 390 + k * 19, s_, 11, MUTED)

    aux_y = 760
    text(150, aux_y - 40, "tiếp điểm khô của relay K1", 12, DANGER, "start", "700")
    text(150, aux_y - 22, "chỉ để PLC BIẾT, không phải để dừng", 11, MUTED)
    wire([(160, rail_0), (160, aux_y)], INK, 2)
    dot(160, rail_0, INK, 6)
    end2 = contact_no(160, aux_y, 60, DANGER)
    text(300, aux_y + 30, "K1 khối 3 · NO", 10, DANGER, "middle", "600", mono=True)
    text(300, aux_y + 46, "kéo I0.7 xuống 0 V", 10, MUTED, "middle")

    plc_h = pin_top + pin_gap * len(INPUTS) - plc_y + 40
    box(plc_x, plc_y, plc_w, plc_h, "#eef3fa", "#1f3a5f")
    text(plc_x + plc_w / 2, plc_y + 34, "PLC", 20, "#1f3a5f", "middle", "700")
    text(plc_x + plc_w / 2, plc_y + 56, "ngõ vào số — chung 1M", 12, MUTED, "middle")

    for i, (addr, name, axis, owner) in enumerate(INPUTS):
        y = pin_top + i * pin_gap
        c = DANGER if owner == "SCL" else AX.get(axis, INK)
        terminal(plc_x, y, c)
        text(plc_x + 16, y + 5, addr, 13, c, "start", "700", mono=True)
        text(plc_x + 82, y + 5, name, 12, MUTED, "start", mono=True)
        tag = "FC_Main đọc" if owner == "SCL" else f"Axis_{axis} tự đọc"
        text(plc_x + plc_w - 14, y + 5, tag, 11,
             DANGER if owner == "SCL" else LINE, "end", "600")

        if addr == "I0.7":
            wire([(end2, aux_y), (plc_x - 60, aux_y), (plc_x - 60, y), (plc_x - 5, y)],
                 DANGER, 3)
        elif addr == "I0.0":
            # nut DUNG tren nap tu — tiep diem NC, keo chan vao xuong 0 V
            e3 = contact_nc(380, y, 80, c)
            wire([(e3, y), (plc_x - 5, y)], c, 2)
            wire([(380, y), (120, y), (120, rail_0)], INK, 2)
            dot(120, rail_0, INK, 4)
            text(420, y - 34, "nút DỪNG · NC", 10, c, "middle", "700")
            text(420, y - 19, "khác nút E-Stop", 9, MUTED, "middle")
        else:
            # Omron EE-SX951: khe chan sang, ba day dung toi
            box(sw_x, y - 17, 96, 34, "#fff", c, rx=4)
            text(sw_x + 48, y - 2, "EE-SX951", 10, c, "middle", "700", mono=True)
            text(sw_x + 48, y + 11, "khe 5 mm · NPN", 8, MUTED, "middle")
            # nau -> 24 V
            wire([(sw_x + 24, y - 17), (sw_x + 24, rail_24)], DANGER, 2)
            dot(sw_x + 24, rail_24, DANGER, 4)
            # xanh duong -> 0 V
            wire([(sw_x + 72, y + 17), (sw_x + 72, rail_0)], INK, 2)
            dot(sw_x + 72, rail_0, INK, 4)
            # ngo ra -> chan vao PLC
            wire([(sw_x + 96, y), (plc_x - 5, y)], c, 2)

    text(sw_x + 48, pin_top - 56, "cảm biến khe Omron EE-SX951", 12, MUTED, "middle")
    text(sw_x + 48, pin_top - 40, "nâu → 24 V · xanh dương → 0 V · dùng ngõ Light-ON",
         10, LINE, "middle")

    m_y = pin_top + pin_gap * len(INPUTS)
    terminal(plc_x, m_y, DANGER)
    text(plc_x + 16, m_y + 5, "1M", 13, DANGER, "start", "700", mono=True)
    text(plc_x + 60, m_y + 5, "→ +24 V  (vì cảm biến NPN)", 11, DANGER, "start", "700")
    wire([(plc_x - 5, m_y), (plc_x - 150, m_y), (plc_x - 150, rail_24)], DANGER, 3)
    dot(plc_x - 150, rail_24, DANGER, 6)

    notes_box(1180, 300, 300, 360, "PHẢI NHỚ", [
        ("Nút Dừng trên web KHÁC nút này",
         "Nút web đi qua mạng, server, chương trình PLC. Đứt một mắt là bấm không ăn."),
        ("1M lên 24 V, không phải 0 V",
         "EE-SX951 là NPN — nó kéo ngõ vào xuống 0 V. Đấu 1M xuống 0 V thì cảm biến "
         "không bao giờ ăn."),
        ("Dùng ngõ Light-ON",
         "Khe thông = có tín hiệu. Cờ chắn vào khe hoặc đứt dây đều mất tín hiệu — "
         "hỏng cũng dừng máy."),
        ("I0.7 chỉ để báo tin",
         "Việc dừng do contactor K2 làm — xem Phần 4. PLC biết để báo lỗi, "
         "không tự chạy lại."),
        ("Bảy chân kia khai trong TO",
         "Cắm dây thôi chưa đủ — phải khai ở Homing và Position limits từng trục."),
    ])


# =========================================================== 3. BO TRI
def section_layout():
    heading(3, "Cảm biến gắn ở ĐÂU trên máy",
            "Công tắc hành trình phải nằm NGOÀI giới hạn phần mềm — phần mềm "
            "chặn trước, công tắc là lớp dự phòng khi chương trình treo.")

    # ---- truc X: thanh ngang ----
    x0, x1, y_rail = 220, 1150, 300
    text(120, y_rail - 80, "TRỤC X — chạy ngang", 16, AX["X"], "start", "700")
    text(120, y_rail - 58, "hành trình phần mềm 0 … 1250 mm", 12, MUTED)

    wire([(x0 - 70, y_rail), (x1 + 70, y_rail)], "#7d8899", 10)
    for frac, mm_val in ((0.0, "0"), (0.5, "625"), (1.0, "1250")):
        px = x0 + (x1 - x0) * frac
        wire([(px, y_rail - 16), (px, y_rail - 4)], MUTED, 2)
        text(px, y_rail - 22, f"{mm_val} mm", 11, MUTED, "middle", mono=True)

    # ban truot
    box(x0 + 250, y_rail - 46, 90, 40, "#eef3fa", "#1f3a5f", rx=5)
    text(x0 + 295, y_rail - 20, "bàn", 12, "#1f3a5f", "middle", "600")

    def switch_mark(px, label, addr, color, below=True):
        yy = y_rail + (34 if below else -34)
        wire([(px, y_rail), (px, yy)], color, 2, dash="4 3")
        box(px - 52, yy, 104, 36, "#fff", color, rx=5)
        text(px, yy + 15, label, 11, color, "middle", "700", mono=True)
        text(px, yy + 29, addr, 10, MUTED, "middle", mono=True)

    switch_mark(x0 - 45, "X_MIN", "I0.1", AX["X"])
    switch_mark(x0 + 40, "X_HOME", "I0.0", AX["X"])
    switch_mark(x1 + 45, "X_MAX", "I0.2", AX["X"])

    text(x0 - 45, y_rail + 92, "trước vạch 0", 10, MUTED, "middle")
    text(x0 + 40, y_rail + 92, "gần chỗ chờ", 10, MUTED, "middle")
    text(x1 + 45, y_rail + 92, "sau vạch 1250", 10, MUTED, "middle")

    # ---- truc Z: cot dung ----
    zx, z_bot, z_top = 300, 700, 460
    text(120, z_bot + 110, "TRỤC Z — lên xuống", 16, AX["Z"], "start", "700")
    text(120, z_bot + 132, "hành trình 0 … 400 mm", 12, MUTED)

    wire([(zx, z_bot + 60), (zx, z_top - 60)], "#7d8899", 10)
    for py, mm_val in ((z_bot, "0"), (z_top, "400")):
        wire([(zx - 16, py), (zx - 4, py)], MUTED, 2)
        text(zx - 22, py + 4, f"{mm_val} mm", 11, MUTED, "end", mono=True)

    box(zx + 12, (z_bot + z_top) / 2 - 20, 80, 40, "#eef3fa", "#1f3a5f", rx=5)
    text(zx + 52, (z_bot + z_top) / 2 + 6, "đầu", 12, "#1f3a5f", "middle", "600")

    def z_mark(py, label, addr):
        wire([(zx, py), (zx + 130, py)], AX["Z"], 2, dash="4 3")
        box(zx + 130, py - 18, 104, 36, "#fff", AX["Z"], rx=5)
        text(zx + 182, py - 3, label, 11, AX["Z"], "middle", "700", mono=True)
        text(zx + 182, py + 11, addr, 10, MUTED, "middle", mono=True)

    z_mark(z_bot + 40, "Z_MIN", "I0.4")
    z_mark(z_bot - 10, "Z_HOME", "I0.3")
    z_mark(z_top - 40, "Z_MAX", "I0.5")

    # ---- truc Y: goc lat ----
    yx, yy = 800, 580
    text(660, 420, "TRỤC Y — lật trái phải", 16, AX["Y"], "start", "700")
    text(660, 442, "giới hạn phần mềm ±70°, chạy ±60°", 12, MUTED)

    circle(yx, yy, 96, "#fff", "#dfe5ec", 2)
    for ang, lab, col in ((0, "0°  HOME", AX["Y"]), (-60, "−60°", MUTED), (60, "+60°", MUTED)):
        import math
        rad = math.radians(ang - 90)
        ex, ey = yx + 96 * math.cos(rad), yy + 96 * math.sin(rad)
        wire([(yx, yy), (ex, ey)], col, 3 if ang == 0 else 2,
             dash="" if ang == 0 else "5 4")
        text(ex + (0 if ang == 0 else (26 if ang > 0 else -26)),
             ey - 10, lab, 11, col, "middle", "700")
    dot(yx, yy, AX["Y"], 6)
    box(yx - 52, yy + 116, 104, 36, "#fff", AX["Y"], rx=5)
    text(yx, yy + 131, "Y_HOME", 11, AX["Y"], "middle", "700", mono=True)
    text(yx, yy + 145, "I0.6", 10, MUTED, "middle", mono=True)
    text(yx, yy + 172, "trục quay nên không cần công tắc hành trình", 10, MUTED, "middle")

    notes_box(1080, 420, 400, 330, "ĐẶT CÔNG TẮC Ở ĐÂU CHO ĐÚNG", [
        ("Công tắc nằm NGOÀI vạch phần mềm",
         "Giới hạn phần mềm 0…1250 chặn trước. Công tắc đặt lấn ra ngoài "
         "khoảng 10–20 mm, chỉ ăn khi phần mềm đã hỏng."),
        ("HOME đặt gần chỗ chờ",
         "Máy chạy về đó dò gốc. Hiện HomeMode = 0 nên chưa cần — "
         "muốn dùng thì đổi sang 3 và khai trong TO."),
        ("Cữ chặn cơ khí ngoài cùng",
         "Sau công tắc phải còn một cữ cứng để máy không văng ra khỏi ray."),
        ("Công tắc còn nên cắt Enable",
         "Vừa đưa vào DI vừa đấu nối tiếp cắt driver, phòng chương trình treo."),
    ], wrap=44)



# =========================================================== 4. MACH DIEU KHIEN
def section_control_power():
    heading(4, "Mạch điều khiển — CB, đèn đỏ, nút Start có đèn, nút E-Stop",
            "Vẽ theo đúng đồ đang có trong tủ: CHiNT NXB-63 C20 · Omron S8VK-C12024 · "
            "CHiNT NXJ/2Z(D) 24 VDC · Meanwell LRS-600-48")

    LR, RR = 200, 1180              # ray +24 V (trai) va ray 0 V (phai)
    rail_top, rail_bot = 540, 1090
    col_x, col_w = 1250, 250
    l_bus, n_bus = 170, 215

    # ------------------------------------------- 220 V vao -> CB1 -> hai nguon
    text(88, 136, "220 VAC vào tủ", 13, INK, "start", "700")
    text(92, 160, "L", 12, DANGER, "start", "700", mono=True)
    text(92, 205, "N", 12, INK, "start", "700", mono=True)
    wire([(106, l_bus), (180, l_bus)], DANGER, 3)
    wire([(106, n_bus), (180, n_bus)], INK, 3)

    mcb_2p(180, l_bus, n_bus, 70, DANGER)
    text(215, 120, "CB1   NXB-63  C20  2P", 12, DANGER, "middle", "700")
    text(215, 256, "cọc 1,3 vào · 2,4 ra", 10, MUTED, "middle")
    text(215, 270, "nằm trong tủ", 10, MUTED, "middle")

    wire([(250, l_bus), (830, l_bus)], DANGER, 3)
    wire([(250, n_bus), (830, n_bus)], INK, 3)

    box(340, 290, 250, 118, "#fdf3ef", V_PLUS)
    text(465, 316, "NGUỒN 24 V", 13, V_PLUS, "middle", "700")
    text(465, 336, "Omron S8VK-C12024 · 5 A", 10, MUTED, "middle")
    text(465, 354, "cục đen cạnh CB trong tủ", 10, LINE, "middle")
    text(465, 374, "cấp PLC, cảm biến, mạch này", 10, MUTED, "middle")
    terminal(400, 290, DANGER)
    terminal(460, 290, INK)
    wire([(400, 285), (400, l_bus)], DANGER, 2)
    dot(400, l_bus, DANGER, 4)
    wire([(460, 285), (460, n_bus)], INK, 2)
    dot(460, n_bus, INK, 4)
    terminal(400, 408, DANGER)
    terminal(520, 408, INK)
    text(390, 428, "+V", 11, DANGER, "end", "700", mono=True)
    text(510, 428, "−V", 11, INK, "end", "700", mono=True)
    wire([(400, 413), (400, 500), (LR, 500), (LR, rail_top)], DANGER, 4)
    wire([(520, 413), (520, 468), (RR, 468), (RR, rail_top)], INK, 4)

    box(680, 290, 250, 118, "#fdf3ef", V_PLUS)
    text(805, 316, "NGUỒN 48 V", 13, V_PLUS, "middle", "700")
    text(805, 336, "Meanwell LRS-600-48", 10, MUTED, "middle")
    text(805, 354, "cục bạc to trong tủ", 10, LINE, "middle")
    text(805, 374, "chỉ cấp cho ba driver — Phần 1", 10, MUTED, "middle")
    terminal(740, 290, DANGER)
    terminal(800, 290, INK)
    wire([(740, 285), (740, l_bus)], DANGER, 2)
    dot(740, l_bus, DANGER, 4)
    wire([(800, 285), (800, n_bus)], INK, 2)
    dot(800, n_bus, INK, 4)
    terminal(930, 322, V_PLUS)
    terminal(930, 362, INK)
    text(916, 326, "+V", 11, V_PLUS, "end", "700", mono=True)
    text(916, 366, "−V", 11, INK, "end", "700", mono=True)

    wire([(935, 322), (990, 322)], V_PLUS, 3)
    e_k2 = contact_no(990, 322, 80, LINE)
    text(1030, 288, "K2 · CHƯA CÓ — xem cảnh báo dưới", 10, LINE, "middle", "600")
    wire([(e_k2, 322), (1238, 322)], V_PLUS, 3)
    text(1244, 326, "→ +48 V TỚI DRIVER (Phần 1)", 11, V_PLUS, "start", "700")
    wire([(935, 362), (1238, 362)], INK, 3)
    text(1244, 366, "→ 0 V CHUNG (Phần 1)", 11, INK, "start", "700")

    wire([(1060, 362), (1060, 468)], INK, 3)
    dot(1060, 362, INK, 5)
    dot(1060, 468, INK, 5)
    circle(1060, 468, 16, "none", V_PLUS, 2)
    text(1046, 432, "hai nguồn PHẢI chung 0 V", 11, V_PLUS, "end", "700")

    # ------------------------------------------------------------- hai ray
    wire([(LR, rail_top), (LR, rail_bot)], DANGER, 5)
    text(LR - 14, rail_top - 14, "+24 V", 13, DANGER, "end", "700", mono=True)
    wire([(RR, rail_top), (RR, rail_bot)], INK, 5)
    text(RR + 14, rail_top - 14, "0 V", 13, INK, "start", "700", mono=True)

    # ------------------------------------------ nhanh 1: chot tu giu cuon K1
    y1, y1b, y1c = 595, 655, 678
    dot(LR, y1, DANGER, 5)
    wire([(LR, y1), (270, y1)], DANGER, 2)

    circle(312, 526, 16, DANGER, DANGER, 2)
    circle(312, 526, 9, "#ff7a45", "#ff7a45", 1)
    wire([(312, 542), (312, 584)], DANGER, 2.5)
    contact_nc(270, y1, 80, DANGER)
    text(336, 516, "S0 · E-STOP", 11, DANGER, "start", "700")
    text(336, 530, "cọc 11–12 · NC", 9, MUTED, "start")
    text(336, 543, "xoay để nhả", 9, MUTED, "start")

    node_a, node_b = 400, 580
    wire([(350, y1), (node_a, y1)], DANGER, 2)
    dot(node_a, y1, DANGER, 5)

    s1a, s1b = 440, 520
    wire([(node_a, y1), (s1a, y1)], DANGER, 2)
    contact_no(s1a, y1, s1b - s1a, DANGER)
    circle(480, 552, 12, "#eafaf0", OKG, 2)
    wire([(472, 544), (488, 560)], OKG, 2)
    wire([(472, 560), (488, 544)], OKG, 2)
    wire([(480, 564), (480, 586)], OKG, 2.5)
    text(480, 522, "S1   START   cọc 13–14", 11, OKG, "middle", "700")
    text(480, 507, "nút nhấn CÓ ĐÈN", 9, MUTED, "middle")

    wire([(s1b, y1), (node_b, y1)], DANGER, 2)
    dot(node_b, y1, DANGER, 5)

    wire([(node_a, y1), (node_a, y1b), (s1a, y1b)], DANGER, 2)
    contact_no(s1a, y1b, s1b - s1a, DANGER)
    text(480, y1b + 26, "K1 khối 1 · chân 9 → 5  (NO) — TỰ GIỮ", 10, DANGER,
         "middle", "600")
    wire([(s1b, y1b), (node_b, y1b), (node_b, y1)], DANGER, 2)

    wire([(node_b, y1), (880, y1)], DANGER, 2)
    coil(880, y1 - 23, 150, 46, "K1", DANGER)
    text(955, y1 + 42, "CHiNT NXJ/2Z(D)  24 VDC — chỉ 2 khối", 10, MUTED, "middle")
    text(955, y1 + 57, "cuộn: chân 14 (+) vào · chân 13 xuống 0 V", 10, MUTED, "middle")
    wire([(1030, y1), (RR, y1)], INK, 2)
    dot(RR, y1, INK, 5)

    dot(640, y1, DANGER, 5)
    wire([(640, y1), (640, y1c), (692, y1c)], OKG, 2)
    lamp(716, y1c, 22, OKG)
    wire([(740, y1c), (1090, y1c), (1090, y1)], OKG, 2)
    dot(1090, y1, OKG, 5)
    text(716, y1c + 42, "đèn TRONG nút START · cọc X1–X2", 10, OKG, "middle", "700")
    text(716, y1c + 57, "cầu X1 sang cọc 14 ngay tại nút — K1 hút là nút sáng xanh",
         10, MUTED, "middle")
    wire([(494, 552), (700, 552), (700, y1c - 22)], OKG, 2, dash="4 4")
    text(600, 545, "cùng một nút", 9, OKG, "middle", "600")

    # -------------------------- nhanh 2: den do — COM cua khoi 2 nam o 0 V
    y2 = 790
    dot(LR, y2, DANGER, 5)
    wire([(LR, y2), (336, y2)], DANGER, 2)
    lamp(360, y2, 24, DANGER, "H1   ĐÈN ĐỎ", "Φ22 · 24 VDC · X1–X2")
    wire([(384, y2), (560, y2)], DANGER, 2)
    contact_nc(560, y2, 80, DANGER)
    text(600, y2 - 38, "K1 khối 2 · chân 12 → 4  (NC)", 10, DANGER, "middle",
         "600", mono=True)
    wire([(640, y2), (RR, y2)], INK, 2)
    dot(RR, y2, INK, 5)
    text(700, y2 + 30, "SÁNG khi K1 chưa hút — vừa bật CB, hoặc E-Stop đang nhấn",
         11, DANGER, "start", "700")
    text(700, y2 + 48, "TẮT khi K1 hút — lúc đó nút START sáng xanh thay vào",
         11, MUTED, "start")

    # ------------------------------------------- nhanh 3: bao trang thai ve PLC
    y3 = 900
    dot(LR, y3, DANGER, 5)
    wire([(LR, y3), (560, y3)], DANGER, 2)
    box(560, y3 - 45, 280, 90, "#eef3fa", "#1f3a5f")
    text(700, y3 - 24, "PLC · CPU 1214C DC/DC/DC", 11, "#1f3a5f", "middle", "700")
    terminal(560, y3, DANGER)
    terminal(840, y3, DANGER)
    text(578, y3 - 8, "1M", 12, DANGER, "start", "700", mono=True)
    text(822, y3 - 8, "DI a.7", 12, DANGER, "end", "700", mono=True)
    box(662, y3 - 12, 76, 24, "#fff", LINE, rx=3, sw=1)
    text(700, y3 + 4, "opto", 10, MUTED, "middle")
    wire([(565, y3), (662, y3)], LINE, 2, dash="4 3")
    wire([(738, y3), (835, y3)], LINE, 2, dash="4 3")
    text(700, y3 + 32, "mạch vào bên trong PLC", 9, LINE, "middle")

    wire([(845, y3), (900, y3)], DANGER, 2)
    contact_no(900, y3, 80, DANGER)
    text(940, y3 - 30, "K1 khối 2 · chân 12 → 8  (NO)", 10, DANGER, "middle",
         "600", mono=True)
    wire([(980, y3), (RR, y3)], INK, 2)
    dot(RR, y3, INK, 5)
    text(560, y3 + 62, "Chân chung 12 của khối 2 đấu xuống 0 V: phía NC (4) thắp đèn đỏ,", 10, MUTED, "start")
    text(560, y3 + 77, "phía NO (8) kéo I0.7 xuống 0 V. Một khối làm được cả hai việc.", 10, MUTED, "start")

    # ------------------------- khong con tiep diem nao de cat cung: canh bao
    box(200, 985, 980, 128, "#fff6f3", DANGER, dash="7 5")
    text(224, 1015, "⚠  CHƯA CÓ LỚP CẮT CỨNG CHO NGUỒN 48 V CỦA DRIVER", 14,
         DANGER, "start", "700")
    for k, s_ in enumerate((
            "Nút E-Stop của bạn chỉ có MỘT tiếp điểm NC — đã dùng hết để cắt cuộn K1. "
            "Relay NXJ/2Z cũng chỉ có hai khối,",
            "đã dùng hết cho tự giữ và cho đèn đỏ / I0.7. Nên hiện tại nhấn E-Stop chỉ "
            "làm K1 nhả: đèn đỏ sáng, PLC biết qua",
            "I0.7 rồi dừng bằng PHẦN MỀM. Chương trình treo là không ai cắt được 48 V.",
            "Cách rẻ nhất để vá: mua thêm MỘT khối tiếp điểm NC gắn vào chính nút nấm đó, "
            "đấu nối tiếp vào cuộn contactor K2.")):
        text(224, 1042 + k * 17, s_, 11,
             DANGER if k == 3 else MUTED, "start", "700" if k == 3 else "400")

    # ------------------------------------------------ chu giai hai ky hieu
    box(200, 1130, 330, 108, "#fbfcfd", LINE, sw=1)
    text(218, 1158, "KÝ HIỆU TIẾP ĐIỂM — nhìn kỹ trước khi bấm cốt", 11, INK,
         "start", "700")
    contact_nc(244, 1200, 70, INK)
    text(279, 1224, "thường ĐÓNG (NC)", 10, MUTED, "middle", "600")
    contact_no(404, 1200, 70, INK)
    text(439, 1224, "thường MỞ (NO)", 10, MUTED, "middle", "600")
    text(357, 1204, "≠", 15, LINE, "middle", "700")

    # ---------------------------------------------------- cot phai: bang & note
    box(col_x, 540, col_w, 290, "#fbfcfd", LINE, sw=1)
    text(col_x + 18, 572, "BẢNG TRẠNG THÁI", 14, INK, "start", "700")
    cy = 602
    for head, body, c in (
            ("① Bật CB1", "ĐÈN ĐỎ sáng — có điện, máy chưa cho chạy.", DANGER),
            ("② Ấn nút START", "K1 hút và tự giữ · đỏ TẮT, nút START sáng XANH.", OKG),
            ("③ Ấn E-STOP", "K1 nhả · xanh tắt, ĐỎ sáng lại, I0.7 = 0 → FC_Main dừng.", DANGER),
            ("④ Xoay nhả E-Stop", "Đỏ VẪN sáng. Phải ấn START lần nữa — máy không tự chạy lại.", MUTED)):
        text(col_x + 18, cy, head, 12, c, "start", "700")
        lines = textwrap.wrap(body, 36)
        for k, line in enumerate(lines):
            text(col_x + 18, cy + 17 + k * 14, line, 10, MUTED, "start")
        cy += 17 + 14 * len(lines) + 14

    notes_box(col_x, 850, col_w, 388, "PHẢI NHỚ", [
        ("NXJ/2Z chỉ có 2 khối",
         "Khối 1 tự giữ, khối 2 chung cho đèn đỏ và I0.7. Hết chân, không dư."),
        ("Cuộn có diode — phải đúng cực",
         "Bản (D) có diode chống ngược. Chân 14 là (+), chân 13 xuống 0 V."),
        ("Tiếp điểm tự giữ phải là NO",
         "Đấu nhầm 9→1 (NC) là ấn START xong nhả tay ra máy tắt ngay."),
        ("E-Stop hiện chỉ dừng mềm",
         "Chưa có contactor K2 thì E-Stop không cắt được 48 V. Đọc ô cảnh báo."),
        ("Dây điều khiển 0.75 mm²",
         "Bấm đầu cốt ferrule, đánh số hai đầu theo bảng ở file thực tế."),
    ], wrap=33)


# ===================================================== TO 2: DAU DAY THUC TE
WIRES = [
    (1,  "220 V lưới · L",      "CB1 · cọc 1",            "đen"),
    (2,  "220 V lưới · N",      "CB1 · cọc 3",            "xanh dương"),
    (3,  "220 V lưới · PE",     "vỏ tủ / thanh PE",       "vàng-lục"),
    (4,  "CB1 · cọc 2",         "NGUỒN 24V · L",               "đen"),
    (5,  "CB1 · cọc 4",         "NGUỒN 24V · N",               "xanh dương"),
    (6,  "CB1 · cọc 2",         "NGUỒN 48V · AC/L",            "đen"),
    (7,  "CB1 · cọc 4",         "NGUỒN 48V · AC/N",            "xanh dương"),
    (8,  "thanh PE",            "NGUỒN 24V · PE",          "vàng-lục"),
    (9,  "thanh PE",            "NGUỒN 48V · PE",          "vàng-lục"),
    (10, "NGUỒN 24V · +V",           "thanh +24 V",            "đỏ"),
    (11, "NGUỒN 24V · −V",           "thanh 0 V",              "đen"),
    (12, "thanh +24 V",         "S0 · cọc 11",            "đỏ"),
    (13, "S0 · cọc 12",         "S1 · cọc 13",            "đỏ"),
    (14, "S0 · cọc 12",         "K1 · chân 9",            "đỏ"),
    (15, "S1 · cọc 14",         "K1 · chân 14 (+)",       "đỏ"),
    (16, "K1 · chân 5",         "K1 · chân 14 (+)",       "đỏ"),
    (17, "S1 · cọc 14",         "S1 · X1  (cầu tại nút)", "đỏ"),
    (18, "S1 · X2",             "thanh 0 V",              "đen"),
    (19, "K1 · chân 13",        "thanh 0 V",              "đen"),
    (20, "thanh +24 V",         "H1 · X1",                "đỏ"),
    (21, "H1 · X2",             "K1 · chân 4",            "đỏ"),
    (22, "K1 · chân 12",        "thanh 0 V",              "đen"),
    (23, "K1 · chân 8",         "PLC · DI a.7",           "đỏ"),
    (24, "thanh +24 V",         "PLC · L+",               "đỏ"),
    (25, "thanh 0 V",           "PLC · M",                "đen"),
    (26, "thanh +24 V",         "PLC · 1M",               "đỏ"),
    (27, "NGUỒN 48V · +V",           "V+ của 3 driver — Phần 1", "đỏ"),
    (28, "NGUỒN 48V · −V",           "0 V chung + GND driver",   "đen"),
]


def section_real_wiring():
    box(60, 24, W - 120, 58, "#f4f7fb", "#1f3a5f", rx=10, sw=2)
    text(84, 50, "ĐẤU DÂY THỰC TẾ — số cọc đúng như in trên thiết bị", 20, INK,
         weight="700")
    text(84, 71, "CHiNT NXB-63 C20 2P · Omron S8VK-C12024 · CHiNT NXJ/2Z(D) 24 VDC · "
                 "CPU 1214C DC/DC/DC · Meanwell LRS-600-48", 12, MUTED)

    # ------------------------------------------------------------ ① NGUON
    box(60, 108, 710, 442, "#fbfcfd", LINE, rx=8, sw=1)
    text(84, 138, "①  NGUỒN — 220 V vào CB1, ra hai cục nguồn có sẵn trong tủ",
         13, INK, "start", "700")

    devbox(150, 240, 150, 110, DANGER, [("CB1", 14, "700"),
                                        ("NXB-63", 10, "600"),
                                        ("C20 · 2P", 9, "400")])
    pin_t(190, 240, "1", DANGER)
    pin_t(265, 240, "3", INK)
    pin_b(190, 350, "2", DANGER)
    pin_b(265, 350, "4", INK)
    wire([(190, 192), (190, 235)], DANGER, 2)
    wire([(265, 192), (265, 235)], INK, 2)
    text(190, 182, "L", 12, DANGER, "middle", "700", mono=True)
    text(265, 182, "N", 12, INK, "middle", "700", mono=True)
    text(228, 165, "220 V từ lưới", 10, MUTED, "middle")
    tag(190, 214, 1, DANGER)
    tag(265, 214, 2, INK)

    devbox(470, 240, 220, 92, V_PLUS, [("NGUỒN 24 V", 13, "700"),
                                       ("Omron S8VK-C12024", 10, "600"),
                                       ("cục đen cạnh CB", 9, "400")])
    pin_l(470, 262, "L", DANGER)
    pin_l(470, 288, "N", INK)
    pin_l(470, 314, "PE", MUTED)
    pin_r(690, 262, "+V", DANGER)
    pin_r(690, 288, "−V", INK)

    devbox(470, 400, 220, 92, V_PLUS, [("NGUỒN 48 V", 13, "700"),
                                       ("Meanwell LRS-600-48", 10, "600"),
                                       ("cục bạc to · cấp 3 driver", 9, "400")])
    pin_l(470, 422, "AC/L", DANGER)
    pin_l(470, 448, "AC/N", INK)
    pin_l(470, 474, "PE", MUTED)
    pin_r(690, 422, "+V", DANGER)
    pin_r(690, 448, "−V", INK)

    # L: CB1 coc 2 -> hai bo nguon (di vong duoi, khong cat qua hop nao)
    wire([(190, 355), (190, 512), (390, 512), (390, 262), (465, 262)], DANGER, 2)
    dot(390, 422, DANGER, 5)
    wire([(390, 422), (465, 422)], DANGER, 2)
    tag(390, 330, 4, DANGER)
    tag(430, 422, 6, DANGER)
    # N: CB1 coc 4
    wire([(265, 355), (265, 532), (420, 532), (420, 288), (465, 288)], INK, 2)
    dot(420, 448, INK, 5)
    wire([(420, 448), (465, 448)], INK, 2)
    tag(420, 368, 5, INK)
    tag(442, 448, 7, INK)

    for yy, lbl, sub_, c in ((258, "→ +24 V", "dây 10", DANGER),
                             (292, "→ 0 V", "dây 11", INK),
                             (418, "→ +48 V", "dây 27", DANGER),
                             (452, "→ 0 V", "dây 28", INK)):
        wire([(695, yy), (712, yy)], c, 2)
        text(700, yy - 8, lbl, 10, c, "start", "700")
        text(700, yy + 12, sub_, 9, LINE, "start")
    text(610, 166, "Cọc PE của cả hai bộ nguồn bắt vào vỏ tủ", 10, MUTED, "middle")
    text(610, 181, "và dây PE của lưới  —  dây 3 · 8 · 9", 10, MUTED, "middle")

    # --------------------------------------------- ② CHOT TU GIU CUON K1
    box(790, 108, 710, 442, "#fbfcfd", LINE, rx=8, sw=1)
    text(814, 138, "②  CHỐT TỰ GIỮ — E-Stop, nút Start, cuộn K1", 13, INK,
         "start", "700")

    wire([(830, 190), (1460, 190)], DANGER, 4)
    text(830, 176, "thanh +24 V", 11, DANGER, "start", "700")
    wire([(830, 510), (1460, 510)], INK, 4)
    text(830, 534, "thanh 0 V", 11, INK, "start", "700")

    devbox(840, 240, 150, 100, DANGER, [("S0 · E-STOP", 12, "700"),
                                        ("1 tiếp điểm NC", 9, "600")], t0=46)
    pin_t(915, 240, "11", DANGER)
    pin_b(915, 340, "12", DANGER)
    wire([(915, 235), (915, 190)], DANGER, 2)
    dot(915, 190, DANGER, 5)
    tag(915, 213, 12, DANGER)

    devbox(1060, 235, 170, 100, OKG, [("S1 · START", 12, "700"),
                                      ("NO + khối đèn", 9, "600")])
    pin_l(1060, 265, "13", DANGER)
    pin_r(1230, 265, "14", DANGER)
    pin_l(1060, 310, "X2", INK)
    pin_r(1230, 310, "X1", OKG)

    devbox(1290, 240, 160, 160, DANGER, [("K1", 14, "700"),
                                         ("NXJ/2Z(D)", 10, "600"),
                                         ("24 VDC", 9, "400")])
    pin_l(1290, 275, "9", DANGER)
    pin_l(1290, 315, "5", DANGER)
    pin_b(1345, 400, "14", DANGER)
    pin_b(1415, 400, "13", INK)
    text(1370, 350, "khối 1", 10, MUTED, "middle", "600")
    text(1370, 366, "cuộn ↓", 10, MUTED, "middle", "600")

    # nut nhanh A: sau E-Stop
    wire([(915, 345), (915, 366), (1005, 366), (1005, 220), (1270, 220),
          (1270, 275), (1285, 275)], DANGER, 2)
    dot(1005, 265, DANGER, 5)
    wire([(1005, 265), (1055, 265)], DANGER, 2)
    tag(1005, 320, 13, DANGER)
    tag(1140, 220, 14, DANGER)

    # S1 coc 14 -> cuon K1 chan 14
    wire([(1235, 265), (1272, 265), (1272, 440), (1345, 440), (1345, 405)],
         DANGER, 2)
    tag(1272, 380, 15, DANGER)
    # tiep diem tu giu: chan 5 -> chan 14
    wire([(1285, 315), (1283, 315), (1283, 462), (1345, 462), (1345, 440)],
         DANGER, 2)
    dot(1345, 440, DANGER, 5)
    tag(1314, 462, 16, DANGER)
    # cau den ngay tai nut — noi X1 sang coc 14 bang doan day ngan
    wire([(1235, 310), (1252, 310), (1252, 265)], OKG, 2)
    dot(1252, 265, OKG, 5)
    tag(1252, 290, 17, OKG)
    # den ve 0 V
    wire([(1055, 310), (1025, 310), (1025, 510)], INK, 2)
    dot(1025, 510, INK, 5)
    tag(1025, 430, 18, INK)
    # cuon chan 13 ve 0 V
    wire([(1415, 405), (1415, 510)], INK, 2)
    dot(1415, 510, INK, 5)
    tag(1415, 462, 19, INK)

    # ------------------------------------- ③ DEN DO + BAO TRANG THAI VE PLC
    box(60, 578, 710, 432, "#fbfcfd", LINE, rx=8, sw=1)
    text(84, 608, "③  ĐÈN ĐỎ và báo trạng thái về PLC — dùng chung khối 2", 13,
         INK, "start", "700")

    wire([(100, 650), (740, 650)], DANGER, 4)
    text(100, 636, "thanh +24 V", 11, DANGER, "start", "700")
    wire([(100, 960), (740, 960)], INK, 4)
    text(100, 984, "thanh 0 V", 11, INK, "start", "700")

    devbox(130, 700, 140, 90, DANGER, [("H1", 13, "700"),
                                       ("đèn đỏ Φ22 · 24 VDC", 9, "600")], t0=46)
    pin_t(200, 700, "X1", DANGER)
    pin_b(200, 790, "X2", DANGER)
    wire([(200, 695), (200, 650)], DANGER, 2)
    dot(200, 650, DANGER, 5)
    tag(200, 672, 20, DANGER)

    devbox(330, 700, 170, 140, DANGER, [("K1  khối 2", 12, "700"),
                                        ("chân chung 12", 10, "600"),
                                        ("xuống 0 V", 9, "400")])
    pin_l(330, 730, "4", DANGER)
    pin_l(330, 775, "12", INK)
    pin_r(500, 815, "8", DANGER)

    wire([(200, 795), (200, 900), (300, 900), (300, 730), (325, 730)], DANGER, 2)
    tag(300, 830, 21, DANGER)
    wire([(325, 775), (315, 775), (315, 960)], INK, 2)
    dot(315, 960, INK, 5)
    tag(315, 890, 22, INK)

    devbox(585, 700, 155, 180, "#1f3a5f", [("PLC", 13, "700"),
                                           ("CPU 1214C", 10, "600"),
                                           ("DC/DC/DC", 9, "400")])
    pin_l(585, 715, "L+", DANGER)
    pin_l(585, 785, "1M", DANGER)
    pin_l(585, 825, "DI a.7", DANGER)
    pin_b(700, 880, "M", INK)

    wire([(505, 815), (555, 815), (555, 825), (580, 825)], DANGER, 2)
    tag(530, 815, 23, DANGER)
    wire([(580, 715), (570, 715), (570, 650)], DANGER, 2)
    dot(570, 650, DANGER, 5)
    tag(570, 686, 24, DANGER)
    wire([(700, 885), (700, 960)], INK, 2)
    dot(700, 960, INK, 5)
    tag(700, 925, 25, INK)
    wire([(580, 785), (540, 785), (540, 650)], DANGER, 2)
    dot(540, 650, DANGER, 5)
    tag(540, 724, 26, DANGER)

    text(470, 992, "1M lên +24 V nên chân vào chỉ ăn khi bị kéo xuống 0 V", 10,
         MUTED, "middle")

    # --------------------------------------------------- ④ BANG DAU DAY
    box(790, 578, 710, 672, "#fbfcfd", LINE, rx=8, sw=1)
    text(814, 608, "④  BẢNG ĐẤU DÂY — đấu xong tích từng dòng", 13, INK,
         "start", "700")

    cx = (818, 858, 1136, 1390)
    text(cx[0], 638, "#", 10, LINE, "start", "700")
    text(cx[1], 638, "TỪ", 10, LINE, "start", "700")
    text(cx[2], 638, "ĐẾN", 10, LINE, "start", "700")
    text(cx[3], 638, "MÀU", 10, LINE, "start", "700")
    wire([(814, 648), (1476, 648)], LINE, 1)

    for i, (n, a_, b_, mau) in enumerate(WIRES):
        yy = 670 + i * 20
        if i % 2 == 0:
            box(814, yy - 14, 662, 20, "#f4f7fb", "none", rx=3, sw=0)
        c = DANGER if mau == "đỏ" else (MUTED if mau == "vàng-lục" else INK)
        text(cx[0], yy, str(n), 10, c, "start", "700", mono=True)
        text(cx[1], yy, a_, 10, INK, "start", mono=True)
        text(cx[2], yy, b_, 10, INK, "start", mono=True)
        text(cx[3], yy, mau, 10, c, "start", "600")

    text(814, 1238, "Dây điều khiển 0.75 mm², bấm đầu cốt ferrule và lồng số "
                    "hai đầu đúng cột #.", 10, MUTED, "start")

    # ------------------------------------------------------- canh bao cuoi
    box(60, 1040, 710, 250, "#fff6f3", DANGER, rx=8, dash="7 5")
    text(84, 1072, "⚠  ĐỌC TRƯỚC KHI CẤP ĐIỆN", 14, DANGER, "start", "700")
    for k, (head, body) in enumerate((
            ("Cuộn K1 có diode — sai cực là không hút",
             "Bản (D) có diode chống ngược. Chân 14 là (+), chân 13 xuống 0 V."),
            ("Đối chiếu lại số chân in trên nắp relay",
             "NXJ/2Z: khối 1 là 9(chung)–5(NO)–1(NC), khối 2 là 12–8(NO)–4(NC)."),
            ("Cọc của bộ nguồn: đọc nhãn trên máy",
             "S8VK-C12024 có OUTPUT ở mặt trên, INPUT ở mặt dưới. Hình này chỉ "
             "vẽ tên cọc, không vẽ đúng vị trí."),
            ("E-Stop hiện chỉ dừng bằng phần mềm",
             "Nút chỉ có 1 tiếp điểm NC, K1 chỉ có 2 khối — hết chân, chưa cắt "
             "được 48 V. Mua thêm 1 khối NC + contactor K2 mới đủ."))):
        yy = 1104 + k * 46
        text(84, yy, "▸ " + head, 11, DANGER if k == 3 else INK, "start", "700")
        for j, line in enumerate(textwrap.wrap(body, 82)):
            text(96, yy + 17 + j * 14, line, 10, MUTED, "start")



def render(path, height, jobs):
    """jobs = [(goc y, ham ve), ...] — moi lan goi la mot to giay rieng."""
    global dy
    parts.clear()
    for i, (off, fn) in enumerate(jobs):
        dy = off
        fn()
        if i:
            dy = 0
            wire([(60, off - 26), (W - 60, off - 26)], "#dfe5ec", 2)
    dy = 0
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" '
           f'width="{W}" height="{height}">\n'
           f'<rect width="{W}" height="{height}" fill="#ffffff"/>\n'
           + "\n".join(parts) + "\n</svg>\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    print(f"da ghi {path}  ({len(svg)} byte, {height} px cao)")


render(OUT, H, list(zip(SEC, (section_outputs, section_inputs,
                             section_layout, section_control_power))))
render(OUT2, H2, [(0, section_real_wiring)])
