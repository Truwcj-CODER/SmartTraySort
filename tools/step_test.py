#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
step_test.py  -  Test truc Y: go GOC (do), bam CHAY, mam lat toi goc do.

Noi thang PLC qua Modbus TCP (LAN cam laptop). Truc Y o pulse mode; tool tu
quy doi do -> xung. Tu HOME, tu dat toc - chi can go so va bam CHAY.

    python tools/step_test.py
    python tools/step_test.py --host 192.168.0.10

Tat server (Pi/docker) truoc vi MB_SERVER chi nhan 1 ket noi.
"""
from __future__ import annotations

import argparse, socket, struct, threading, time
import tkinter as tk
from tkinter import ttk, messagebox

HOST, PORT, UNIT = "192.168.0.10", 502, 1
WRITE_ADDR, STATUS_ADDR = 0, 10
C_TILT_TO, C_STOP, C_RESET, C_HOME, C_SET_PARAM = 10, 3, 4, 2, 14
P_VEL_Y, P_TILT_VEL = 2, 5
DEFAULT_PPD = 3200.0 / 90.0     # xung / do
DEFAULT_VEL_DEG = 200.0          # do/s khi chay


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
    def _send(s, cmd, sel=0, y=0.0):
        s._seq = s._seq % 65535 + 1; yh, yl = f32(y)
        s.mb.write(WRITE_ADDR, [cmd, sel & 0xFFFF, 256, s._seq, 0, 0, yh, yl, 0, 0])
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
    def tilt(s, pulses): return s._wait(s._send(C_TILT_TO, y=pulses), 60)
    def home(s): s.enable(); time.sleep(0.6); return s._wait(s._send(C_HOME), 60)
    def stop(s): return s._wait(s._send(C_STOP), 5)
    def reset(s): return s._wait(s._send(C_RESET), 10)
    def set_vel(s, vp):
        s._wait(s._send(C_SET_PARAM, sel=P_VEL_Y, y=vp), 10)
        return s._wait(s._send(C_SET_PARAM, sel=P_TILT_VEL, y=vp), 10)


class App:
    def __init__(s, root, host, port):
        s.plc = Plc(host, port); s.root = root; s.busy = False
        root.title("Test goc lat truc Y"); root.geometry("400x340"); root.minsize(380, 320)

        # trang thai ket noi
        top = ttk.Frame(root); top.pack(fill="x", padx=12, pady=6)
        s.conn = ttk.Label(top, text="dang ket noi...", font=("", 10, "bold"))
        s.conn.pack(side="left")

        # O NHAP GOC + NUT CHAY
        box = ttk.Frame(root); box.pack(pady=14)
        ttk.Label(box, text="Goc muon lat (do):", font=("", 12)).grid(row=0, column=0, columnspan=2, pady=4)
        s.ang = tk.StringVar(value="90")
        e = ttk.Entry(box, textvariable=s.ang, width=8, font=("", 22, "bold"), justify="center")
        e.grid(row=1, column=0, columnspan=2, pady=6)
        e.focus(); e.bind("<Return>", lambda _=None: s._run())
        ttk.Button(box, text="CHAY", width=12, command=s._run).grid(row=2, column=0, padx=4, pady=6)
        ttk.Button(box, text="VE 0", width=8, command=lambda: s._go(0)).grid(row=2, column=1, padx=4, pady=6)

        # goc thuc te
        mid = ttk.Frame(root); mid.pack(pady=4)
        ttk.Label(mid, text="Goc thuc te:", font=("", 11)).pack(side="left")
        s.act = tk.StringVar(value="-")
        ttk.Label(mid, textvariable=s.act, font=("", 16, "bold"), foreground="#0a6").pack(side="left", padx=8)

        # nut phu
        btn = ttk.Frame(root); btn.pack(pady=6)
        ttk.Button(btn, text="DUNG", command=s._stop).pack(side="left", padx=4)
        ttk.Button(btn, text="XOA LOI", command=s._reset).pack(side="left", padx=4)

        # dong log 1 dong
        s.msg = tk.StringVar(value="")
        ttk.Label(root, textvariable=s.msg, foreground="#555").pack(pady=2)

        # cai dat nho o duoi (ppd de can, it dung)
        cfg = ttk.LabelFrame(root, text="Cai dat (chinh khi can can lai)")
        cfg.pack(fill="x", padx=12, pady=6)
        r = ttk.Frame(cfg); r.pack(pady=3)
        ttk.Label(r, text="xung/do:").pack(side="left")
        s.ppd = tk.StringVar(value=f"{DEFAULT_PPD:.4f}")
        ttk.Entry(r, textvariable=s.ppd, width=9).pack(side="left", padx=4)
        ttk.Label(r, text="toc(do/s):").pack(side="left")
        s.vel = tk.StringVar(value=f"{DEFAULT_VEL_DEG:.0f}")
        ttk.Entry(r, textvariable=s.vel, width=6).pack(side="left", padx=4)

        s._stopflag = False
        threading.Thread(target=s._poll, daemon=True).start()
        root.protocol("WM_DELETE_WINDOW", s._close)

    def _ppd(s): return float(s.ppd.get())

    def _bg(s, deg):
        # CHAY: tu home neu chua, tu dat toc, roi lat. Mot cu click lo het.
        if s.busy:
            s.msg.set("dang chay, cho ti"); return
        s.busy = True
        def w():
            try:
                st = s.plc.status()
                if st["error"] or st["step"] >= 900:
                    s.msg.set("dang loi -> xoa loi..."); s.plc.reset(); time.sleep(2)
                    st = s.plc.status()
                if not st["homed"] or not st["ready"]:
                    s.msg.set("dang home..."); s.plc.home(); time.sleep(0.5)
                # gui toc MOI LAN -> doi o 'toc' la an ngay, khong can XOA LOI
                vp = float(s.vel.get()) * s._ppd()
                s.plc.set_vel(vp)
                pulses = deg * s._ppd()
                s.msg.set(f"lat toi {deg:g} do ({pulses:.0f} xung)...")
                r = s.plc.tilt(pulses)
                ok = {0:"?",1:"dang chay",2:"XONG",3:"bi dung",4:"LOI",5:"tu choi"}
                s.msg.set(f"lat {deg:g} do: {ok.get(r['result'],'?')}"
                          + (f"  (loi 0x{r['error_id']:04X})" if r['error_id'] else ""))
            except Exception as ex:
                s.msg.set(f"loi: {ex}")
            finally:
                s.busy = False
        threading.Thread(target=w, daemon=True).start()

    def _run(s):
        try: deg = float(s.ang.get())
        except ValueError: messagebox.showerror("Loi", "Goc phai la so"); return
        s._go(deg)

    def _go(s, deg): s._bg(deg)

    def _stop(s):
        def w():
            try: s.plc.stop(); s.msg.set("da dung")
            except Exception as e: s.msg.set(str(e))
        threading.Thread(target=w, daemon=True).start()

    def _reset(s):
        def w():
            try: s.plc.reset(); s.msg.set("da xoa loi")
            except Exception as e: s.msg.set(str(e))
        threading.Thread(target=w, daemon=True).start()

    def _poll(s):
        while not s._stopflag:
            try:
                st = s.plc.status()
                s.root.after(0, s._upd, True, st)
            except Exception:
                s.root.after(0, s._upd, False, {})
            time.sleep(0.5)

    def _upd(s, online, st):
        if online:
            e = st.get("error_id", 0)
            tag = "SAN SANG" if st.get("ready") else ("LOI 0x%04X" % e if e else "chua home")
            s.conn.config(text=f"● {tag}", foreground="#0a6" if st.get("ready") else "#c60")
            try: s.act.set(f"{st['y']/s._ppd():.1f} do")
            except Exception: s.act.set("-")
        else:
            s.conn.config(text="● MAT KET NOI", foreground="#c00"); s.act.set("-")

    def _close(s):
        s._stopflag = True; s.plc.mb.close(); s.root.destroy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST); ap.add_argument("--port", type=int, default=PORT)
    a = ap.parse_args()
    root = tk.Tk(); App(root, a.host, a.port); root.mainloop()


if __name__ == "__main__":
    main()
