#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
x_test.py  -  Test truc X (ngang) qua PLC Modbus TCP truc tiep.

Go VI TRI X muon toi, bam CHAY, truc chay toi do. Giu Z tai cho (chi X di).
Chi can Python chuan. LAN cam thang laptop <-> PLC.

    python tools/x_test.py
    python tools/x_test.py --host 192.168.0.10

Don vi X theo Technology Object Axis_X:
  - Axis_X de MM   -> go MM, he so = 1.
  - Axis_X de PULSE-> go MM va dat 'he so' = xung/mm, hoac go thang xung, he so=1.
Tat server (Pi/docker) truoc vi MB_SERVER chi nhan 1 ket noi.
"""
from __future__ import annotations

import argparse, socket, struct, threading, time
import tkinter as tk
from tkinter import messagebox

HOST, PORT, UNIT = "192.168.0.10", 502, 1
WRITE_ADDR, STATUS_ADDR = 0, 10
C_MOVE_XZ, C_STOP, C_RESET, C_HOME, C_SET_PARAM = 8, 3, 4, 2, 14
P_VEL_X = 1
DEFAULT_FACTOR = 1.0
DEFAULT_VEL = 50.0

# --- bang mau ---
BG, CARD, INK, SUB = "#eef2f6", "#ffffff", "#1f2d3a", "#6b7a89"
GREEN, GREEND = "#1e9e5a", "#17824a"
GRAY, GRAYD = "#8794a3", "#6f7d8b"
RED, REDD = "#d64545", "#b83a3a"
ORANGE, ORANGED = "#e0891e", "#c1741a"
ACCENT = "#0a7cff"


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
                    x=rd_f32(r[6], r[7]), z=rd_f32(r[10], r[11]))
    def _send(s, cmd, sel=0, x=0.0, z=0.0):
        s._seq = s._seq % 65535 + 1
        xh, xl = f32(x); zh, zl = f32(z)
        s.mb.write(WRITE_ADDR, [cmd, sel & 0xFFFF, 256, s._seq, xh, xl, 0, 0, zh, zl])
        return s._seq
    def enable(s): s.mb.write(WRITE_ADDR, [0, 0, 256, 0, 0, 0, 0, 0, 0, 0])
    def _wait(s, seq, to):
        t = time.time() + to; ack = False
        while time.time() < t:
            st = s.status()
            if st["ack"] == seq: ack = True
            if ack and st["done_seq"] == seq: return st
            time.sleep(0.1)
        raise TimeoutError("het gio")
    def move_x(s, x):
        z_now = s.status()["z"]
        return s._wait(s._send(C_MOVE_XZ, x=x, z=z_now), 120)
    def home(s): s.enable(); time.sleep(0.6); return s._wait(s._send(C_HOME), 120)
    def stop(s): return s._wait(s._send(C_STOP), 5)
    def reset(s): return s._wait(s._send(C_RESET), 10)
    def set_vel(s, v): return s._wait(s._send(C_SET_PARAM, sel=P_VEL_X, x=v), 10)


def mkbtn(parent, text, bg, bgd, cmd, w=10, big=False):
    b = tk.Button(parent, text=text, command=cmd, bg=bg, fg="white",
                  activebackground=bgd, activeforeground="white",
                  font=("Segoe UI", 15 if big else 11, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  width=w, height=2 if big else 1, padx=6, pady=2)
    return b


class App:
    def __init__(s, root, host, port):
        s.plc = Plc(host, port); s.root = root; s.busy = False
        root.title("Test truc X"); root.configure(bg=BG)
        root.geometry("440x480"); root.minsize(420, 460)

        # ---- banner trang thai ----
        s.banner = tk.Label(root, text="dang ket noi...", bg=GRAY, fg="white",
                            font=("Segoe UI", 13, "bold"), pady=10)
        s.banner.pack(fill="x")

        # ---- the chinh ----
        card = tk.Frame(root, bg=CARD); card.pack(fill="both", expand=True, padx=14, pady=12)

        tk.Label(card, text="TRUC X  (ngang)", bg=CARD, fg=SUB,
                 font=("Segoe UI", 10, "bold")).pack(pady=(14, 2))
        tk.Label(card, text="Vi tri X muon toi", bg=CARD, fg=INK,
                 font=("Segoe UI", 13)).pack(pady=(6, 4))

        s.pos = tk.StringVar(value="100")
        ent = tk.Entry(card, textvariable=s.pos, justify="center",
                       font=("Segoe UI", 30, "bold"), width=7, relief="solid", bd=1,
                       fg=INK, highlightthickness=2, highlightcolor=ACCENT)
        ent.pack(pady=6); ent.focus(); ent.bind("<Return>", lambda _=None: s._run())

        row = tk.Frame(card, bg=CARD); row.pack(pady=10)
        mkbtn(row, "CHAY", GREEN, GREEND, s._run, w=12, big=True).pack(side="left", padx=6)
        mkbtn(row, "VE 0", GRAY, GRAYD, lambda: s._go(0), w=7, big=True).pack(side="left", padx=6)

        # ---- vi tri thuc ----
        act = tk.Frame(card, bg=CARD); act.pack(pady=(12, 4))
        tk.Label(act, text="X hien tai:", bg=CARD, fg=SUB, font=("Segoe UI", 12)).pack(side="left")
        s.act = tk.StringVar(value="-")
        tk.Label(act, textvariable=s.act, bg=CARD, fg=GREEND,
                 font=("Consolas", 20, "bold")).pack(side="left", padx=8)

        # ---- nut phu ----
        row2 = tk.Frame(card, bg=CARD); row2.pack(pady=8)
        mkbtn(row2, "DUNG", RED, REDD, s._stop, w=8).pack(side="left", padx=5)
        mkbtn(row2, "XOA LOI", ORANGE, ORANGED, s._reset, w=8).pack(side="left", padx=5)

        s.msg = tk.StringVar(value="")
        tk.Label(card, textvariable=s.msg, bg=CARD, fg=SUB, font=("Segoe UI", 9)).pack(pady=4)

        # ---- cai dat ----
        cfg = tk.Frame(card, bg="#f3f6f9"); cfg.pack(fill="x", padx=8, pady=(8, 12))
        tk.Label(cfg, text="Cai dat", bg="#f3f6f9", fg=SUB, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 0))
        r = tk.Frame(cfg, bg="#f3f6f9"); r.pack(padx=8, pady=6)
        tk.Label(r, text="he so (gia tri x):", bg="#f3f6f9", fg=INK, font=("Segoe UI", 9)).pack(side="left")
        s.factor = tk.StringVar(value=f"{DEFAULT_FACTOR:g}")
        tk.Entry(r, textvariable=s.factor, width=7, relief="solid", bd=1).pack(side="left", padx=(4, 12))
        tk.Label(r, text="toc:", bg="#f3f6f9", fg=INK, font=("Segoe UI", 9)).pack(side="left")
        s.vel = tk.StringVar(value=f"{DEFAULT_VEL:g}")
        tk.Entry(r, textvariable=s.vel, width=6, relief="solid", bd=1).pack(side="left", padx=4)

        s._stopflag = False
        threading.Thread(target=s._poll, daemon=True).start()
        root.protocol("WM_DELETE_WINDOW", s._close)

    def _factor(s):
        f = float(s.factor.get())
        return f if f else 1.0

    def _bg(s, val):
        if s.busy: s.msg.set("dang chay, cho ti"); return
        s.busy = True
        def w():
            try:
                st = s.plc.status()
                if st["error"] or st["step"] >= 900:
                    s.msg.set("xoa loi..."); s.plc.reset(); time.sleep(2); st = s.plc.status()
                if not st["homed"] or not st["ready"]:
                    s.msg.set("dang home..."); s.plc.home(); time.sleep(0.5)
                s.plc.set_vel(float(s.vel.get()) * s._factor())
                target = val * s._factor()
                s.msg.set(f"chay X toi {val:g} (gui {target:.0f})...")
                r = s.plc.move_x(target)
                ok = {0:"?",1:"dang chay",2:"XONG",3:"bi dung",4:"LOI",5:"tu choi"}
                s.msg.set(f"X toi {val:g}: {ok.get(r['result'],'?')}"
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
    def _go(s, v): s._bg(v)

    def _stop(s):
        threading.Thread(target=lambda: s._safe(s.plc.stop, "da dung"), daemon=True).start()
    def _reset(s):
        threading.Thread(target=lambda: s._safe(s.plc.reset, "da xoa loi"), daemon=True).start()
    def _safe(s, fn, ok):
        try: fn(); s.msg.set(ok)
        except Exception as e: s.msg.set(str(e))

    def _poll(s):
        while not s._stopflag:
            try: st = s.plc.status(); s.root.after(0, s._upd, True, st)
            except Exception: s.root.after(0, s._upd, False, {})
            time.sleep(0.5)

    def _upd(s, online, st):
        if not online:
            s.banner.config(text="● MAT KET NOI PLC", bg=RED); s.act.set("-"); return
        e = st.get("error_id", 0)
        if st.get("ready"):
            s.banner.config(text="● SAN SANG", bg=GREEN)
        elif e:
            s.banner.config(text=f"● LOI 0x{e:04X}  (bam XOA LOI)", bg=RED)
        else:
            s.banner.config(text="● CHUA HOME  (bam CHAY se tu home)", bg=ORANGE)
        try: s.act.set(f"{st['x'] / s._factor():.1f}")
        except Exception: s.act.set("-")

    def _close(s):
        s._stopflag = True; s.plc.mb.close(); s.root.destroy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST); ap.add_argument("--port", type=int, default=PORT)
    a = ap.parse_args()
    root = tk.Tk(); App(root, a.host, a.port); root.mainloop()


if __name__ == "__main__":
    main()
