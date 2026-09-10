#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
y_pulse_test.py  -  Test truc Y (lat) o CHE DO XUNG, giong het Axis Control
Panel cua TIA. Go so XUNG, dat toc do (xung/s), bam CHAY -> Y quay toi do.

Vi sao xung thuan: server dang gui do rồi TO quy doi -> neu pulses/rev trong
cau hinh khong khop DIP driver thi sai. Tool nay bo qua quy doi, gui thang
xung -> biet chac dong co + driver chay dung khong.

    python tools/y_pulse_test.py
    python tools/y_pulse_test.py --host 192.168.0.10

Yeu cau: PLC dang chay CHUONG TRINH CHINH (co MB_SERVER + FB_XY_Tray),
truc Y cua TO o DON VI XUNG (1 don vi = 1 xung). Tat server Pi/docker truoc
vi MB_SERVER chi nhan 1 ket noi.

!!! Lenh Y la MC_MoveAbsolute, can truc da HOME (bam HOME truoc). HOME chay
    ca 3 truc - ke do duoi truc Z (truc dung) truoc khi bam.
"""
from __future__ import annotations

import argparse, socket, struct, threading, time
import tkinter as tk
from tkinter import messagebox

HOST, PORT, UNIT = "192.168.0.10", 502, 1
WRITE_ADDR, STATUS_ADDR = 0, 10
C_TILT_TO, C_STOP, C_RESET, C_HOME, C_SET_PARAM = 10, 3, 4, 2, 14
P_TILT_VEL = 5                 # FB dung TiltVel cho truc Y (khong phai VelY)
DEFAULT_PULSES = 16000         # 1 vong theo DIP hien tai
DEFAULT_VEL = 10000            # xung/s (panel TIA dang 10000)
DEFAULT_PPR = 16000            # xung/vong - chi de hien thi do/vong, khong gui

BG, CARD, INK, SUB = "#eef2f6", "#ffffff", "#1f2d3a", "#6b7a89"
GREEN, GREEND = "#1e9e5a", "#17824a"
BLUE, BLUED = "#0a7cff", "#0864cf"
GRAY, GRAYD = "#8794a3", "#6f7d8b"
RED, REDD = "#d64545", "#b83a3a"
ORANGE, ORANGED = "#e0891e", "#c1741a"


def f32(v): return struct.unpack(">HH", struct.pack(">f", float(v)))
def rd_f32(hi, lo): return struct.unpack(">f", struct.pack(">HH", hi & 0xFFFF, lo & 0xFFFF))[0]


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
                    y=rd_f32(r[8], r[9]))
    # Bo cuc thanh ghi ghi (theo FB): [cmd, sel, ctrl=256, seq, Xhi,Xlo, Yhi,Ylo, Zhi,Zlo]
    #   - Gia tri LAT (cmd 10) nam o o Y  (thanh ghi 6,7)
    #   - Gia tri THAM SO (cmd 14) FB doc tu TargetX -> phai de o o X (thanh ghi 4,5)
    def _send(s, cmd, sel=0, x=0.0, y=0.0):
        s._seq = s._seq % 65535 + 1
        xh, xl = f32(x); yh, yl = f32(y)
        s.mb.write(WRITE_ADDR, [cmd, sel & 0xFFFF, 256, s._seq, xh, xl, yh, yl, 0, 0])
        return s._seq
    def enable(s): s.mb.write(WRITE_ADDR, [0, 0, 256, 0, 0, 0, 0, 0, 0, 0])
    def _wait(s, seq, to):
        t = time.time() + to; ack = False
        while time.time() < t:
            st = s.status()
            if st["ack"] == seq: ack = True
            if ack and st["done_seq"] == seq: return st
            time.sleep(0.05)
        raise TimeoutError("het gio")
    def tilt(s, pulses): return s._wait(s._send(C_TILT_TO, y=pulses), 120)
    def home(s): s.enable(); time.sleep(0.6); return s._wait(s._send(C_HOME), 120)
    def stop(s): return s._wait(s._send(C_STOP), 5)
    def reset(s): return s._wait(s._send(C_RESET), 10)
    def set_vel(s, v): return s._wait(s._send(C_SET_PARAM, sel=P_TILT_VEL, x=v), 10)


def mkbtn(parent, text, bg, bgd, cmd, w=10, big=False):
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg="white",
                     activebackground=bgd, activeforeground="white",
                     font=("Segoe UI", 15 if big else 11, "bold"),
                     relief="flat", bd=0, cursor="hand2",
                     width=w, height=2 if big else 1)


class App:
    def __init__(s, root, host, port):
        s.plc = Plc(host, port); s.root = root; s.busy = False
        root.title("Test truc Y - che do XUNG"); root.configure(bg=BG)
        root.geometry("460x560"); root.minsize(440, 540)

        s.banner = tk.Label(root, text="dang ket noi...", bg=GRAY, fg="white",
                            font=("Segoe UI", 13, "bold"), pady=10)
        s.banner.pack(fill="x")

        tk.Label(root, text="gui XUNG thang xuong PLC (bo qua quy doi do)",
                 bg=BG, fg=SUB, font=("Segoe UI", 9)).pack(pady=(6, 0))

        card = tk.Frame(root, bg=CARD); card.pack(fill="both", expand=True, padx=14, pady=10)

        tk.Label(card, text="TRUC Y  (lat)", bg=CARD, fg=SUB,
                 font=("Segoe UI", 10, "bold")).pack(pady=(12, 2))
        tk.Label(card, text="Vi tri Y muon toi (XUNG)", bg=CARD, fg=INK,
                 font=("Segoe UI", 13)).pack(pady=(4, 2))

        s.pos = tk.StringVar(value=str(DEFAULT_PULSES))
        ent = tk.Entry(card, textvariable=s.pos, justify="center",
                       font=("Segoe UI", 30, "bold"), width=8, relief="solid", bd=1,
                       fg=INK, highlightthickness=2, highlightcolor=BLUE)
        ent.pack(pady=4); ent.focus(); ent.bind("<Return>", lambda _=None: s._run())
        ent.bind("<KeyRelease>", lambda _=None: s._hint())

        s.hint = tk.StringVar(value="")
        tk.Label(card, textvariable=s.hint, bg=CARD, fg=BLUE,
                 font=("Segoe UI", 10, "bold")).pack(pady=(0, 4))

        row = tk.Frame(card, bg=CARD); row.pack(pady=6)
        mkbtn(row, "CHAY", GREEN, GREEND, s._run, w=8, big=True).pack(side="left", padx=5)
        mkbtn(row, "+1 VONG", BLUE, BLUED, s._add_rev, w=8, big=True).pack(side="left", padx=5)
        mkbtn(row, "VE 0", GRAY, GRAYD, lambda: s._go(0), w=6, big=True).pack(side="left", padx=5)

        act = tk.Frame(card, bg=CARD); act.pack(pady=(10, 2))
        tk.Label(act, text="Y hien tai:", bg=CARD, fg=SUB, font=("Segoe UI", 12)).pack(side="left")
        s.act = tk.StringVar(value="-")
        tk.Label(act, textvariable=s.act, bg=CARD, fg=GREEND,
                 font=("Consolas", 18, "bold")).pack(side="left", padx=8)
        s.act2 = tk.StringVar(value="")
        tk.Label(card, textvariable=s.act2, bg=CARD, fg=SUB, font=("Segoe UI", 9)).pack()

        row2 = tk.Frame(card, bg=CARD); row2.pack(pady=8)
        mkbtn(row2, "HOME", BLUE, BLUED, s._home, w=8).pack(side="left", padx=5)
        mkbtn(row2, "DUNG", RED, REDD, s._stop, w=7).pack(side="left", padx=5)
        mkbtn(row2, "XOA LOI", ORANGE, ORANGED, s._reset, w=8).pack(side="left", padx=5)

        s.msg = tk.StringVar(value="")
        tk.Label(card, textvariable=s.msg, bg=CARD, fg=SUB, font=("Segoe UI", 9)).pack(pady=4)

        cfg = tk.Frame(card, bg="#f3f6f9"); cfg.pack(fill="x", padx=8, pady=(6, 12))
        tk.Label(cfg, text="Cai dat", bg="#f3f6f9", fg=SUB,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 0))
        r = tk.Frame(cfg, bg="#f3f6f9"); r.pack(padx=8, pady=6)
        tk.Label(r, text="toc(xung/s):", bg="#f3f6f9", fg=INK, font=("Segoe UI", 9)).pack(side="left")
        s.vel = tk.StringVar(value=str(DEFAULT_VEL))
        tk.Entry(r, textvariable=s.vel, width=8, relief="solid", bd=1).pack(side="left", padx=(4, 12))
        tk.Label(r, text="xung/vong:", bg="#f3f6f9", fg=INK, font=("Segoe UI", 9)).pack(side="left")
        s.ppr = tk.StringVar(value=str(DEFAULT_PPR))
        e2 = tk.Entry(r, textvariable=s.ppr, width=7, relief="solid", bd=1)
        e2.pack(side="left", padx=4); e2.bind("<KeyRelease>", lambda _=None: s._hint())

        s._stopflag = False
        s._hint()
        threading.Thread(target=s._poll, daemon=True).start()
        root.protocol("WM_DELETE_WINDOW", s._close)

    def _ppr(s):
        try:
            v = float(s.ppr.get()); return v if v else DEFAULT_PPR
        except ValueError: return DEFAULT_PPR

    def _hint(s):
        try:
            p = float(s.pos.get()); ppr = s._ppr()
            s.hint.set(f"= {p / ppr:.3g} vong  =  {p / ppr * 360:.1f}°")
        except ValueError:
            s.hint.set("")

    def _bg(s, pulses):
        if s.busy: s.msg.set("dang chay, cho ti"); return
        s.busy = True
        def w():
            try:
                st = s.plc.status()
                if st["error"] or st["step"] >= 900:
                    s.msg.set("xoa loi..."); s.plc.reset(); time.sleep(2); st = s.plc.status()
                if not st["homed"] or not st["ready"]:
                    s.msg.set("CHUA HOME - bam HOME truoc"); s.busy = False; return
                s.plc.set_vel(float(s.vel.get()))
                s.msg.set(f"chay Y toi {pulses:.0f} xung...")
                r = s.plc.tilt(pulses)
                ok = {0:"?",1:"dang chay",2:"XONG",3:"bi dung",4:"LOI",5:"tu choi"}
                s.msg.set(f"Y toi {pulses:.0f} xung: {ok.get(r['result'],'?')}"
                          + (f"  (loi 0x{r['error_id']:04X})" if r['error_id'] else ""))
            except Exception as ex:
                s.msg.set(f"loi: {ex}")
            finally:
                s.busy = False
        threading.Thread(target=w, daemon=True).start()

    def _run(s):
        try: v = float(s.pos.get())
        except ValueError: messagebox.showerror("Loi", "Vi tri phai la so"); return
        s._go(v)

    def _go(s, pulses): s._bg(pulses)

    def _add_rev(s):
        # +1 vong tuong doi: doc vi tri hien tai roi cong 1 vong (xung/vong)
        def w():
            try:
                cur = s.plc.status()["y"]; ppr = s._ppr()
                tgt = round(cur + ppr)
                s.root.after(0, lambda: s.pos.set(str(tgt)))
                s.root.after(0, s._hint)
                s._go(tgt)
            except Exception as ex:
                s.msg.set(f"loi: {ex}")
        threading.Thread(target=w, daemon=True).start()

    def _home(s):
        if not messagebox.askokcancel("HOME", "HOME chay CA 3 TRUC (ke Z duoi).\nTiep tuc?"):
            return
        threading.Thread(target=lambda: s._safe(s.plc.home, "da home"), daemon=True).start()

    def _stop(s): threading.Thread(target=lambda: s._safe(s.plc.stop, "da dung"), daemon=True).start()
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
            s.banner.config(text="● MAT KET NOI PLC", bg=RED); s.act.set("-"); s.act2.set(""); return
        e = st.get("error_id", 0)
        if st.get("ready"): s.banner.config(text="● SAN SANG", bg=GREEN)
        elif e: s.banner.config(text=f"● LOI 0x{e:04X}  (bam XOA LOI)", bg=RED)
        elif not st.get("homed"): s.banner.config(text="● CHUA HOME  (bam HOME)", bg=ORANGE)
        else: s.banner.config(text="● BAN / dang chay", bg=GRAY)
        try:
            y = st["y"]; ppr = s._ppr()
            s.act.set(f"{y:.0f} xung")
            s.act2.set(f"{y / ppr:.3g} vong  ({y / ppr * 360:.1f}°)")
        except Exception:
            s.act.set("-"); s.act2.set("")

    def _close(s):
        s._stopflag = True; s.plc.mb.close(); s.root.destroy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST); ap.add_argument("--port", type=int, default=PORT)
    a = ap.parse_args()
    root = tk.Tk(); App(root, a.host, a.port); root.mainloop()


if __name__ == "__main__":
    main()
