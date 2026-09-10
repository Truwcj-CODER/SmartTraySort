#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
home_test.py  -  UI don gian: 1 nut VE HOME, xem truc co ve goc khong.

Noi thang PLC qua Modbus TCP. Bam VE HOME -> gui lenh Home (CmdCode 2) ->
PLC chay active homing theo cau hinh trong Technology Object (di ve huong da
set toi khi cham cong tac Home thi dung + dat goc).

    python tools/home_test.py                 (mac dinh 192.168.0.10)
    python tools/home_test.py --host 192.168.0.10

YEU CAU: PLC dang chay CHUONG TRINH CHINH (co MB_SERVER). Project teststep
KHONG co MB_SERVER nen tool bao "MAT KET NOI" - do la dung, khong phai loi.
Tat server Pi/docker truoc vi MB_SERVER chi nhan 1 ket noi.

LUU Y: nut nay gui lenh 15 = home RIENG TRUC Z (X va Y dung yen). Can:
  1. Da Download config homing cua Axis_Z (STOP CPU) trong TIA.
  2. HomeMode = 3 trong DB_TrayTable (active homing dung cong tac).
  3. Tat server Pi/docker de nhuong ket noi MB_SERVER cho tool.
"""
from __future__ import annotations

import argparse, socket, struct, threading, time
import tkinter as tk

HOST, PORT, UNIT = "192.168.0.10", 502, 1
WRITE_ADDR, STATUS_ADDR = 0, 10
C_HOME_ALL, C_HOME_Z, C_HOME_X, C_STOP, C_RESET = 2, 15, 16, 3, 4  # 2=home X+Z, 15=Z, 16=X

BG, CARD, INK, SUB = "#eef2f6", "#ffffff", "#1f2d3a", "#6b7a89"
GREEN, GREEND = "#1e9e5a", "#17824a"
BLUE, BLUED = "#0a7cff", "#0864cf"
RED, REDD = "#d64545", "#b83a3a"
ORANGE, ORANGED = "#e0891e", "#c1741a"
GRAY = "#8794a3"


def rd_f32(hi, lo): return struct.unpack(">f", struct.pack(">HH", hi & 0xFFFF, lo & 0xFFFF))[0]
def f32(v): return struct.unpack(">HH", struct.pack(">f", float(v)))


class Modbus:
    def __init__(s, host, port): s.host, s.port, s._s, s._t, s._lk = host, port, None, 0, threading.Lock()
    def close(s):
        with s._lk:
            if s._s:
                try: s._s.close()
                except Exception: pass
                s._s = None
    def _xfer(s, pdu):
        with s._lk:
            for a in (1, 2):
                try:
                    if s._s is None:
                        s._s = socket.create_connection((s.host, s.port), timeout=3); s._s.settimeout(3)
                    s._t = (s._t + 1) & 0xFFFF
                    s._s.sendall(struct.pack(">HHHB", s._t, 0, len(pdu) + 1, UNIT) + pdu)
                    h = s._recvn(7); _, _, ln, _ = struct.unpack(">HHHB", h)
                    return s._recvn(ln - 1)
                except Exception:
                    if s._s:
                        try: s._s.close()
                        except Exception: pass
                    s._s = None
                    if a == 2: raise
    def _recvn(s, n):
        b = b""
        while len(b) < n:
            c = s._s.recv(n - len(b))
            if not c: raise OSError("mat ket noi")
            b += c
        return b
    def read(s, addr, cnt):
        b = s._xfer(struct.pack(">BHH", 0x03, addr, cnt))
        if b[0] & 0x80: raise OSError("loi doc")
        return list(struct.unpack(">" + "H" * (b[1] // 2), b[2:2 + b[1]]))
    def write(s, addr, regs):
        n = len(regs); data = struct.pack(">" + "H" * n, *[r & 0xFFFF for r in regs])
        b = s._xfer(struct.pack(">BHHB", 0x10, addr, n, n * 2) + data)
        if b[0] & 0x80: raise OSError("loi ghi")


class Plc:
    def __init__(s, host, port): s.mb = Modbus(host, port); s._seq = 0
    def status(s):
        r = s.mb.read(STATUS_ADDR, 14); sb = r[0]
        return dict(ready=bool(sb & 1), homed=bool(sb & 8), error=bool(sb & 16),
                    step=r[1], error_id=r[2], ack=r[3], done_seq=r[4], result=r[5],
                    x=rd_f32(r[6], r[7]), y=rd_f32(r[8], r[9]), z=rd_f32(r[10], r[11]))
    def _send(s, cmd):
        s._seq = s._seq % 65535 + 1
        # [cmd, sel, CtrlBits=256(AXES_ENABLE), seq, X, Y, Z]
        s.mb.write(WRITE_ADDR, [cmd, 0, 256, s._seq, 0, 0, 0, 0, 0, 0])
        return s._seq
    def enable(s): s.mb.write(WRITE_ADDR, [0, 0, 256, 0, 0, 0, 0, 0, 0, 0])
    def _wait(s, seq, to):
        t = time.time() + to; ack = False
        while time.time() < t:
            st = s.status()
            if st["ack"] == seq: ack = True
            if ack and st["done_seq"] == seq: return st
            time.sleep(0.1)
        raise TimeoutError("het gio - truc chay lau hon hoac chua nhan lenh")
    def home_all(s): s.enable(); time.sleep(0.6); return s._wait(s._send(C_HOME_ALL), 240)
    def home_z(s): s.enable(); time.sleep(0.6); return s._wait(s._send(C_HOME_Z), 180)
    def home_x(s): s.enable(); time.sleep(0.6); return s._wait(s._send(C_HOME_X), 180)
    # JOG Z: giu la chay, nha la dung. bit4=Z+ (len), bit5=Z- (xuong), bit8=enable.
    # cmd=0 + giu nguyen seq -> khong kich CmdPulse, chi tac dong CtrlBits lien tuc.
    def jog_z(s, d):
        ctrl = 256
        if d > 0: ctrl |= 16      # bit4 = Z+
        elif d < 0: ctrl |= 32    # bit5 = Z-
        s.mb.write(WRITE_ADDR, [0, 0, ctrl, s._seq, 0, 0, 0, 0, 0, 0])
    def jog_x(s, d):
        ctrl = 256
        if d > 0: ctrl |= 1       # bit0 = X+
        elif d < 0: ctrl |= 2     # bit1 = X-
        s.mb.write(WRITE_ADDR, [0, 0, ctrl, s._seq, 0, 0, 0, 0, 0, 0])
    # dat toc jog cho ca X (param 9) va Z (param 11) qua SET_PARAM (cmd 14).
    # Toc nay dung chung cho jog tay VA cho buoc home (mcSeekX/Z) -> tang la
    # ca hai nhanh len. Gia tri (mm/s) nam o o X (thanh ghi 4,5).
    def set_jogvel(s, v):
        for sel in (9, 11):
            s._seq = s._seq % 65535 + 1
            xh, xl = f32(v)
            s.mb.write(WRITE_ADDR, [14, sel, 256, s._seq, xh, xl, 0, 0, 0, 0])
            s._wait(s._seq, 10)
    def stop(s): return s._wait(s._send(C_STOP), 5)
    def reset(s): return s._wait(s._send(C_RESET), 10)


def mkbtn(parent, text, bg, bgd, cmd, w=10, big=False):
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg="white",
                     activebackground=bgd, activeforeground="white",
                     font=("Segoe UI", 17 if big else 11, "bold"),
                     relief="flat", bd=0, cursor="hand2",
                     width=w, height=2 if big else 1)


class App:
    def __init__(s, root, host, port):
        s.plc = Plc(host, port); s.root = root; s.busy = False
        s._jogdir = 0; s._jogaxis = "z"
        root.title("HOME truc Z"); root.configure(bg=BG)
        root.geometry("430x470"); root.minsize(410, 450)

        s.banner = tk.Label(root, text="dang ket noi...", bg=GRAY, fg="white",
                            font=("Segoe UI", 13, "bold"), pady=10)
        s.banner.pack(fill="x")

        card = tk.Frame(root, bg=CARD); card.pack(fill="both", expand=True, padx=14, pady=12)

        tk.Label(card, text="Bam de truc chay ve goc (Home)", bg=CARD, fg=SUB,
                 font=("Segoe UI", 11)).pack(pady=(16, 2))
        tk.Label(card, text="chay tới khi cham cong tac -> dung + dat goc 0",
                 bg=CARD, fg=SUB, font=("Segoe UI", 8)).pack(pady=(0, 8))

        mkbtn(card, "HOME  X + Z", GREEN, GREEND, s._home_all, w=16, big=True).pack(pady=(6, 2))
        hrow = tk.Frame(card, bg=CARD); hrow.pack(pady=(0, 2))
        mkbtn(hrow, "HOME Z", GRAY, "#6f7d8b", s._home, w=9).pack(side="left", padx=5)
        mkbtn(hrow, "HOME X", GRAY, "#6f7d8b", s._home_x, w=9).pack(side="left", padx=5)

        # vi tri 3 truc
        grid = tk.Frame(card, bg=CARD); grid.pack(pady=12)
        s.pos = {}
        for i, ax in enumerate(("X", "Y", "Z")):
            tk.Label(grid, text=ax, bg=CARD, fg=SUB, font=("Segoe UI", 11, "bold")).grid(row=0, column=i, padx=14)
            v = tk.StringVar(value="-")
            tk.Label(grid, textvariable=v, bg=CARD, fg=GREEND,
                     font=("Consolas", 15, "bold")).grid(row=1, column=i, padx=14)
            s.pos[ax] = v

        # JOG X: giu de chay, nha la dung  (◄ am/ve home, ► duong)
        xrow = tk.Frame(card, bg=CARD); xrow.pack(pady=(8, 0))
        bxl = mkbtn(xrow, "X  ◄ (−)", BLUE, BLUED, None, w=9)
        bxr = mkbtn(xrow, "X  ► (+)", BLUE, BLUED, None, w=9)
        bxl.pack(side="left", padx=6); bxr.pack(side="left", padx=6)
        bxl.bind("<ButtonPress-1>", lambda e: s._jog("x", -1))
        bxl.bind("<ButtonRelease-1>", lambda e: s._jog("x", 0))
        bxr.bind("<ButtonPress-1>", lambda e: s._jog("x", 1))
        bxr.bind("<ButtonRelease-1>", lambda e: s._jog("x", 0))

        # JOG Z: giu de chay, nha la dung
        jrow = tk.Frame(card, bg=CARD); jrow.pack(pady=(6, 0))
        bup = mkbtn(jrow, "Z  ▲ LEN", BLUE, BLUED, None, w=9)
        bdn = mkbtn(jrow, "Z  ▼ XUONG", BLUE, BLUED, None, w=9)
        bup.pack(side="left", padx=6); bdn.pack(side="left", padx=6)
        bup.bind("<ButtonPress-1>", lambda e: s._jog("z", 1))
        bup.bind("<ButtonRelease-1>", lambda e: s._jog("z", 0))
        bdn.bind("<ButtonPress-1>", lambda e: s._jog("z", -1))
        bdn.bind("<ButtonRelease-1>", lambda e: s._jog("z", 0))
        tk.Label(card, text="(giu nut de chay, nha la dung)", bg=CARD, fg=SUB,
                 font=("Segoe UI", 8)).pack(pady=(2, 0))

        # toc do jog / seek home (mm/s) - chinh nhanh cham
        vrow = tk.Frame(card, bg=CARD); vrow.pack(pady=(6, 0))
        tk.Label(vrow, text="toc jog (mm/s):", bg=CARD, fg=INK,
                 font=("Segoe UI", 9)).pack(side="left")
        s.jvel = tk.StringVar(value="30")
        ev = tk.Entry(vrow, textvariable=s.jvel, width=6, relief="solid", bd=1)
        ev.pack(side="left", padx=4); ev.bind("<Return>", lambda _=None: s._apply_jvel())
        mkbtn(vrow, "AP DUNG", GRAY, "#6f7d8b", s._apply_jvel, w=8).pack(side="left", padx=4)

        row = tk.Frame(card, bg=CARD); row.pack(pady=8)
        mkbtn(row, "DUNG", RED, REDD, s._stop, w=9).pack(side="left", padx=6)
        mkbtn(row, "XOA LOI", ORANGE, ORANGED, s._reset, w=9).pack(side="left", padx=6)

        s.msg = tk.StringVar(value="")
        tk.Label(card, textvariable=s.msg, bg=CARD, fg=SUB, font=("Segoe UI", 9), wraplength=360).pack(pady=6)

        s._stopflag = False
        threading.Thread(target=s._poll, daemon=True).start()
        root.protocol("WM_DELETE_WINDOW", s._close)

    def _home_all(s): s._do_home(s.plc.home_all, "X+Z")
    def _home(s): s._do_home(s.plc.home_z, "Z")
    def _home_x(s): s._do_home(s.plc.home_x, "X")
    def _do_home(s, fn, ax):
        if s.busy: s.msg.set("dang chay, cho ti"); return
        s.busy = True
        def w():
            try:
                st = s.plc.status()
                if st["error"] or st["step"] >= 900:
                    s.msg.set("dang loi -> xoa loi..."); s.plc.reset(); time.sleep(2)
                s.msg.set(f"dang home {ax}... (chay ve cong tac roi dung)")
                r = fn()
                ok = {0:"?",1:"dang chay",2:"XONG - da ve home",3:"bi dung",4:"LOI",5:"tu choi"}
                s.msg.set(f"Home {ax}: {ok.get(r['result'],'?')}"
                          + (f"  (loi 0x{r['error_id']:04X})" if r['error_id'] else ""))
            except Exception as ex:
                s.msg.set(f"loi: {ex}")
            finally:
                s.busy = False
        threading.Thread(target=w, daemon=True).start()

    def _apply_jvel(s):
        def w():
            try:
                v = float(s.jvel.get()); s.plc.set_jogvel(v)
                s.msg.set(f"toc jog/seek = {v:g} mm/s")
            except Exception as e: s.msg.set(str(e))
        threading.Thread(target=w, daemon=True).start()

    def _jog(s, axis, d):
        s._jogaxis = axis; s._jogdir = d
        fn = s.plc.jog_x if axis == "x" else s.plc.jog_z
        if d == 0:
            try: fn(0)
            except Exception as e: s.msg.set(str(e))
        else:
            s._jog_tick()
    def _jog_tick(s):
        if s._jogdir != 0:
            fn = s.plc.jog_x if s._jogaxis == "x" else s.plc.jog_z
            try:
                fn(s._jogdir)
            except Exception as e:
                s.msg.set(str(e)); s._jogdir = 0; return
            s.root.after(150, s._jog_tick)

    def _stop(s):
        s._jogdir = 0
        threading.Thread(target=lambda: s._safe(s.plc.stop, "da dung"), daemon=True).start()
    def _reset(s): threading.Thread(target=lambda: s._safe(s.plc.reset, "da xoa loi"), daemon=True).start()
    def _safe(s, fn, ok):
        try: fn(); s.msg.set(ok)
        except Exception as e: s.msg.set(str(e))

    def _poll(s):
        while not s._stopflag:
            try: st = s.plc.status(); s.root.after(0, s._upd, True, st)
            except Exception: s.root.after(0, s._upd, False, {})
            time.sleep(0.4)

    def _upd(s, online, st):
        if not online:
            s.banner.config(text="● MAT KET NOI PLC  (can chuong trinh chinh)", bg=RED)
            for v in s.pos.values(): v.set("-")
            return
        e = st.get("error_id", 0)
        if st.get("error") or e:
            s.banner.config(text=f"● LOI 0x{e:04X}  (bam XOA LOI)", bg=RED)
        elif st.get("homed") and st.get("ready"):
            s.banner.config(text="● DA HOME - SAN SANG", bg=GREEN)
        elif st.get("step", 0) not in (0,) :
            s.banner.config(text="● DANG CHAY...", bg=BLUE)
        else:
            s.banner.config(text="● CHUA HOME  (bam VE HOME)", bg=ORANGE)
        for ax, key in (("X", "x"), ("Y", "y"), ("Z", "z")):
            try: s.pos[ax].set(f"{st[key]:.0f}")
            except Exception: s.pos[ax].set("-")

    def _close(s):
        s._stopflag = True; s.plc.mb.close(); s.root.destroy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST); ap.add_argument("--port", type=int, default=PORT)
    a = ap.parse_args()
    root = tk.Tk(); App(root, a.host, a.port); root.mainloop()


if __name__ == "__main__":
    main()
