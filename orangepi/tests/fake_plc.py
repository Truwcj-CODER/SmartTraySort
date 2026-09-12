#!/usr/bin/env python3
# PLC gia lap: Modbus TCP server toi gian + may trang thai bat chuoc FB_XY_Tray.
# Dung de chay thu ca giao dien va app khi khong co PLC that trong tay.
#
#     python3 tests/fake_plc.py                          # lang nghe 0.0.0.0:5020
#     PLC_HOST=127.0.0.1 PLC_PORT=5020 NET_SETUP=0 uvicorn app.main:app
#
# Tu cai dat Modbus (chi FC3/FC6/FC16) thay vi dung server cua pymodbus:
# API datastore cua pymodbus doi lien tuc giua cac ban, con khung tin thi khong doi.
#
# Nhan HET 14 ma lenh cua protocol.Command, ke ca ba cai de sot truoc day - va
# day moi la cho quan trong, vi thieu chung thi thu o nha khong phat hien ra loi
# se gap ngoai xuong:
#
#   11 SET_SLOT   ghi toa do 1 ro           -> bang toa do doi that
#   12 SET_PARK   ghi vi tri cho
#   13 SET_COUNT  bao bo cuc co bao nhieu ro -> so ro ngoai khoang bi tu choi
#   14 SET_PARAM  ghi tham so chay may      -> doi toc do/goc lat trong web thi
#                                              may gia lap chay theo
#
# Va bit jog trong HR2: giu thi truc chay, nha thi dung, tu cat sau 5 giay y nhu
# JogMaxTime ben SCL.
#
# Chuyen dong: X va Z chay CUNG LUC (SyncMove = TRUE), moi truc theo toc do
# rieng, ai xong truoc thi dung cho - thoi gian di bang truc LAU HON chu khong
# cong don. Duong di vi vay la duong cheo, khong phai duong thang noi hai diem:
# S7-1200 khong noi suy quy dao duoc, va o may nay khong can. Dat SYNC_MOVE =
# False de tro lai kieu chay lan luot (buoc 10 xong X roi buoc 20 moi nang Z).
#
# Moi hang so mac dinh trong file nay lay tu 01_Types.scl va 02_DB_TrayTable.scl
# - sua ben do thi sua ca o day, khong thi thu o nha ra mot dang ma ngoai xuong
# chay mot neo.
#
# Khong bat chuoc: ma loi cu the (ErrorID luon 0), gioi han mem tren cua tung
# truc, thoi gian tang/giam toc, va nut DUNG cung tren tu dien. Bon cho do chi
# PLC that co.

from __future__ import annotations

import asyncio
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.plc.protocol import (  # noqa: E402
    Command,
    CtrlBit,
    Param,
    Result,
    decode_f32,
    encode_f32,
)

# X = ngang qua lai | Y = lat trai phai | Z = len xuong
TICK = 0.05           # giay moi vong "quet"
REG_COUNT = 64
MAX_SLOTS = 500       # bang tran cua DB_TrayTable, khop MAX_PLC_SLOTS ben geometry

# Tham so chay may. Day la gia tri KHOI TAO cua DB, dung y nghia voi ban SCL:
# nap lai khoi trong TIA thi DB tro ve may so nay, roi server day tham so that
# xuong bang lenh 14. Khong hardcode nua - de doi tham so trong web thi may gia
# lap chay theo, y nhu may that.
DEFAULTS = {
    Param.VEL_X: 80.0,         # mm/s
    Param.VEL_Y: 200.0,        # do/s  - truc lat
    Param.VEL_Z: 60.0,         # mm/s  - cham hon vi chong trong luc
    Param.TILT_ANGLE: 60.0,    # do
    Param.TILT_VEL: 200.0,     # do/s
    Param.DWELL_MS: 1000.0,    # ms
    Param.TILT_HOLD_MS: 1000.0,
    Param.TILT_COUNT: 1.0,
    Param.SEEK_VEL_X: 10.0,    # toc do bo di tim cam bien luc home - de cham
    Param.SEEK_VEL_Y: 20.0,
    Param.SEEK_VEL_Z: 10.0,
}

# Chay hai truc CUNG LUC hay lan luot. Khop DB_TrayTable.SyncMove := TRUE.
SYNC_MOVE = True

# Vi tri cho = tram nap. X = 5 chu KHONG phai 0: 0 la vach gioi han phan mem,
# ve dung do la PLC bao loi vi tri. Khop HomeX/HomeY/HomeZ trong DB_TrayTable.
PARK = {'x': 5.0, 'y': 0.0, 'z': 5.0}


# Bo cuc khoi tao cua DB_TrayTable: 20 ro. Server day bang that xuong bang lenh
# 11 va bao so ro bang lenh 13, nen may so nay chi song toi lan day dau tien.
def _tray_table() -> dict[int, tuple[float, float, int]]:
    # Cung mot vi tri X phuc vu ca hai ben ray, chi khac chieu lat. Danh so tu
    # hang TREN xuong, moi hang het ben PHAI roi toi ben TRAI.
    columns = (200.0, 437.5, 675.0, 912.5, 1150.0)
    table = {}
    for i, x in enumerate(columns):
        table[1 + i] = (x, 370.0, +1)     # hang 1 - phai
        table[6 + i] = (x, 370.0, -1)     # hang 1 - trai
        table[11 + i] = (x, 190.0, +1)    # hang 2 - phai
        table[16 + i] = (x, 190.0, -1)    # hang 2 - trai
    return table


class FakePlc:
    def __init__(self) -> None:
        self.regs = [0] * REG_COUNT
        self.tray = _tray_table()
        self.params = dict(DEFAULTS)
        # So ro bo cuc hien co. Lenh 13 ghi lai; ngoai khoang nay la tu choi,
        # y nhu #SlotCount ben SCL.
        self.slot_count = 20
        self.ctrl = 0
        self.x, self.y, self.z = PARK['x'], PARK['y'], PARK['z']
        self.step = 0
        self.homed = False
        self.error = False
        self.result = int(Result.IDLE)
        self.cur_seq = self.ack_seq = self.done_seq = 0
        self.slot = 0
        self.tgt_x = PARK['x']
        self.tgt_y = PARK['y']
        self.tgt_z = PARK['z']
        self.tilt_dir = 0
        self.tilt_out = 0.0
        self.tilt_left = 0
        self.dwell = 0
        self.hold = 0
        self.do_tilt = False
        self.do_return = False
        self.jog_ticks = 0        # dem nguoc JogMaxTime

    # ------------------------------------------------------------ tham so
    def p(self, key: Param) -> float:
        return self.params[key]

    def _ticks(self, key: Param) -> int:
        # ms -> so vong quet, it nhat mot vong de con nhin thay buoc do tren web
        return max(1, round(self.p(key) / 1000.0 / TICK))

    def _valid(self, slot: int) -> bool:
        return 1 <= slot <= self.slot_count

    # ------------------------------------------------------------- chuyen dong
    def _approach(self, current: float, target: float, speed: float) -> tuple[float, bool]:
        stepsize = speed * TICK
        if abs(target - current) <= stepsize:
            return target, True
        return current + stepsize * (1 if target > current else -1), False

    # --------------------------------------------------------------- nhan lenh
    def _accept(self, code: int, slot: int, seq: int,
                tx: float, ty: float, tz: float) -> None:
        self.ack_seq = seq
        ready = self.homed and self.step == 0 and not self.error

        def reject() -> None:
            self.result, self.done_seq = int(Result.REJECTED), seq

        def begin(step: int) -> None:
            self.cur_seq, self.result, self.step = seq, int(Result.RUNNING), step

        if code == Command.HOME:
            begin(5) if self.step == 0 else reject()

        elif code == Command.STOP:
            if self.step != 0:
                self.result, self.done_seq = int(Result.ABORTED), self.cur_seq
            self.step = 0

        elif code == Command.RESET:
            self.error = False
            if self.step >= 900:
                self.step = 0

        elif code == Command.TEACH:
            if self._valid(slot) and self.step == 0:
                self.tray[slot] = (self.x, self.z, self.tray[slot][2])
                self.result, self.done_seq = int(Result.OK), seq
            else:
                reject()

        elif code == Command.SET_SLOT:
            if 1 <= slot <= MAX_SLOTS and self.step == 0:
                direction = 1 if ty > 0 else (-1 if ty < 0 else 0)
                self.tray[slot] = (tx, tz, direction)
                self.result, self.done_seq = int(Result.OK), seq
            else:
                reject()

        elif code in (Command.AUTO, Command.GOTO):
            if ready and self._valid(slot):
                x, z, direction = self.tray[slot]
                self.slot, self.tgt_x, self.tgt_z, self.tilt_dir = slot, x, z, direction
                self.do_tilt = self.do_return = code == Command.AUTO
                begin(10)
            else:
                reject()

        elif code == Command.TILT:
            if ready and self._valid(slot):
                self.tilt_dir = self.tray[slot][2]
                self.do_tilt, self.do_return = True, False
                begin(100)
            else:
                reject()

        elif code == Command.SET_PARK:
            if self.step == 0:
                PARK.update(x=tx, y=ty, z=tz)
                self.result, self.done_seq = int(Result.OK), seq
            else:
                reject()

        elif code == Command.MOVE_XZ:
            if ready:
                self.slot, self.tgt_x, self.tgt_z = 0, tx, tz
                self.do_tilt = self.do_return = False
                begin(10)
            else:
                reject()

        elif code == Command.PARK:
            if ready:
                self.do_tilt, self.do_return = False, True
                begin(195)
            else:
                reject()

        elif code == Command.TILT_TO:
            if ready:
                self.tgt_y = ty
                begin(300)
            else:
                reject()

        # Bao bo cuc hien co bao nhieu ro. Server goi ngay sau khi day xong bang
        # toa do, nen tu day tro di moi so ro ngoai khoang deu bi tu choi.
        elif code == Command.SET_COUNT:
            if 0 <= slot <= MAX_SLOTS and self.step == 0:
                self.slot_count = slot
                self.result, self.done_seq = int(Result.OK), seq
            else:
                reject()

        # Ghi mot tham so chay may. So hieu tham so di trong o slot, gia tri
        # trong x - dung nhu service.set_param() gui xuong.
        elif code == Command.SET_PARAM:
            try:
                param = Param(slot)
            except ValueError:
                reject()
            else:
                if self.step == 0:
                    self.params[param] = tx
                    self.result, self.done_seq = int(Result.OK), seq
                else:
                    reject()

        else:
            reject()

    # ----------------------------------------------------------- may trang thai
    def _advance(self) -> None:
        if self.step == 5:
            self.x, self.y, self.z = PARK['x'], PARK['y'], PARK['z']
            self.homed = True
            self.result, self.done_seq, self.step = int(Result.OK), self.cur_seq, 0

        # Duong di la duong CHEO, khong phai duong thang noi hai diem: hai truc
        # nam tren hai kenh xung roi nhau nen kich cung mot vong quet roi ai
        # xong truoc thi dung cho. Thoi gian di bang truc LAU HON, khong phai
        # cong don. S7-1200 khong noi suy quy dao duoc, va o may nay khong can -
        # can den dung toa do la du.
        elif self.step == 10:
            self.x, done_x = self._approach(self.x, self.tgt_x, self.p(Param.VEL_X))
            if not SYNC_MOVE:
                if done_x:
                    self.step = 20
            else:
                self.z, done_z = self._approach(self.z, self.tgt_z, self.p(Param.VEL_Z))
                if done_x and done_z:
                    self.dwell, self.step = self._ticks(Param.DWELL_MS), 30

        # Chi dung khi SyncMove = FALSE, tuc kieu chay lan luot cu.
        elif self.step == 20:
            self.z, done = self._approach(self.z, self.tgt_z, self.p(Param.VEL_Z))
            if done:
                self.dwell, self.step = self._ticks(Param.DWELL_MS), 30

        elif self.step == 30:
            self.dwell -= 1
            if self.dwell <= 0:
                self.step = 100 if self.do_tilt else (195 if self.do_return else 220)

        elif self.step == 100:
            if self.tilt_dir == 0 or self.p(Param.TILT_COUNT) < 1:
                self.step = 190
            else:
                self.tilt_left = int(self.p(Param.TILT_COUNT))
                self.tilt_out = PARK['y'] + self.tilt_dir * self.p(Param.TILT_ANGLE)
                self.step = 170

        elif self.step == 170:
            self.y, done = self._approach(self.y, self.tilt_out, self.p(Param.TILT_VEL))
            if done:
                self.hold, self.step = self._ticks(Param.TILT_HOLD_MS), 175

        elif self.step == 175:
            self.hold -= 1
            if self.hold <= 0:
                self.step = 180

        elif self.step == 180:
            self.y, done = self._approach(self.y, PARK['y'], self.p(Param.TILT_VEL))
            if done:
                self.tilt_left -= 1
                self.step = 170 if self.tilt_left > 0 else 190

        elif self.step == 190:
            self.step = 195 if self.do_return else 220

        elif self.step == 195:
            self.y, done = self._approach(self.y, PARK['y'], self.p(Param.TILT_VEL))
            if done:
                self.step = 200

        # Buoc 195 da dua truc lat ve giua roi, gio mam khong con thoi ra hai
        # ben nua nen chay cheo an toan.
        elif self.step == 200:
            self.z, done_z = self._approach(self.z, PARK['z'], self.p(Param.VEL_Z))
            if not SYNC_MOVE:
                if done_z:
                    self.step = 210
            else:
                self.x, done_x = self._approach(self.x, PARK['x'], self.p(Param.VEL_X))
                if done_z and done_x:
                    self.step = 220

        # Chi dung khi SyncMove = FALSE.
        elif self.step == 210:
            self.x, done = self._approach(self.x, PARK['x'], self.p(Param.VEL_X))
            if done:
                self.step = 220

        elif self.step == 300:
            self.y, done = self._approach(self.y, self.tgt_y, self.p(Param.TILT_VEL))
            if done:
                self.step = 220

        elif self.step == 220:
            self.result, self.done_seq, self.step = int(Result.OK), self.cur_seq, 0

    # ------------------------------------------------------------------ jog tay
    # PLC that cho jog khi may dang ranh: giu bit thi truc chay, nha thi dung.
    # Va no TU CAT sau JogMaxTime - de mat song luc dang giu nut thi truc khong
    # chay mai toi khi dap vao dau hanh trinh. Bat chuoc ca hai o day, khong thi
    # thu tay o nha lai de lot dung cai bay do.
    JOG_MAX_TICKS = int(5.0 / TICK)

    def _jog(self) -> None:
        bits = CtrlBit(self.ctrl & 0x3F)      # chi 6 bit huong, bo AXES_ENABLE

        # jogOK ben SCL chi doi: dang o buoc 0, truc co dien, khong loi, khong
        # het JogMaxTime. KHONG doi da lay goc toa do - vi jog chinh la de di do
        # cong tac goc truoc khi home duoc.
        if bits == CtrlBit.NONE or self.step != 0 or self.error:
            self.jog_ticks = 0
            return

        self.jog_ticks += 1
        if self.jog_ticks > self.JOG_MAX_TICKS:
            return                            # het thoi gian: bo qua, khong chay nua

        # Jog tay chay o toc do chay that, giong FB_XY_Tray: nguoi van hanh bam
        # nut thu dung cai toc do may se chay tu dong. SEEK_VEL_* chi de home.
        dx = self.p(Param.VEL_X) * TICK
        dy = self.p(Param.VEL_Y) * TICK
        dz = self.p(Param.VEL_Z) * TICK

        # Hai chieu cung mot truc bam cung luc thi triet tieu, khong uu tien ben nao.
        if CtrlBit.JOG_X_POS in bits:
            self.x += dx
        if CtrlBit.JOG_X_NEG in bits:
            self.x -= dx
        if CtrlBit.JOG_Y_POS in bits:
            self.y += dy
        if CtrlBit.JOG_Y_NEG in bits:
            self.y -= dy
        if CtrlBit.JOG_Z_POS in bits:
            self.z += dz
        if CtrlBit.JOG_Z_NEG in bits:
            self.z -= dz

        # Khong cho ra ngoai gioi han mem cua Technology Object.
        self.x = max(0.0, self.x)
        self.z = max(0.0, self.z)

    # -------------------------------------------------------------- vong quet
    def scan(self) -> None:
        command, slot, ctrl, seq = self.regs[0:4]
        self.ctrl = ctrl

        if command != 0:
            self.regs[0] = 0        # ack: xoa o lenh y nhu PLC that
            tx = decode_f32(self.regs[4], self.regs[5])
            ty = decode_f32(self.regs[6], self.regs[7])
            tz = decode_f32(self.regs[8], self.regs[9])
            self._accept(command, slot, seq, tx, ty, tz)

        self._advance()
        self._jog()

        busy = 0 < self.step < 900
        bits = (
            (1 if self.homed and self.step == 0 and not self.error else 0)
            | (2 if busy else 0)
            | (8 if self.homed else 0)
            | (16 if self.error else 0)
        )
        hx, lx = encode_f32(self.x)
        hy, ly = encode_f32(self.y)
        hz, lz = encode_f32(self.z)
        self.regs[10:24] = [bits, self.step, 0, self.ack_seq, self.done_seq,
                            self.result, hx, lx, hy, ly, hz, lz, self.slot, 0]


# ------------------------------------------------------------ Modbus TCP toi gian
async def _serve_client(plc: FakePlc, reader: asyncio.StreamReader,
                        writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            header = await reader.readexactly(7)
            txn, _proto, length, unit = struct.unpack(">HHHB", header)
            pdu = await reader.readexactly(length - 1)
            response = _handle_pdu(plc, pdu)
            writer.write(struct.pack(">HHHB", txn, 0, len(response) + 1, unit) + response)
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionResetError):
        pass
    finally:
        writer.close()


def _handle_pdu(plc: FakePlc, pdu: bytes) -> bytes:
    func = pdu[0]

    if func == 3:       # doc nhieu thanh ghi
        addr, count = struct.unpack(">HH", pdu[1:5])
        if addr + count > REG_COUNT:
            return bytes([func | 0x80, 2])
        values = plc.regs[addr:addr + count]
        return bytes([3, count * 2]) + struct.pack(f">{count}H", *values)

    if func == 6:       # ghi 1 thanh ghi
        addr, value = struct.unpack(">HH", pdu[1:5])
        if addr >= REG_COUNT:
            return bytes([func | 0x80, 2])
        plc.regs[addr] = value
        return pdu[:5]

    if func == 16:      # ghi nhieu thanh ghi
        addr, count = struct.unpack(">HH", pdu[1:5])
        if addr + count > REG_COUNT:
            return bytes([func | 0x80, 2])
        plc.regs[addr:addr + count] = struct.unpack(f">{count}H", pdu[6:6 + count * 2])
        return bytes([16]) + struct.pack(">HH", addr, count)

    return bytes([func | 0x80, 1])   # ma ham khong ho tro


async def run(port: int) -> None:
    plc = FakePlc()

    async def scan_loop() -> None:
        while True:
            plc.scan()
            await asyncio.sleep(TICK)

    asyncio.create_task(scan_loop())
    server = await asyncio.start_server(lambda r, w: _serve_client(plc, r, w), "0.0.0.0", port)
    print(f"PLC gia lap dang lang nghe 0.0.0.0:{port} (Ctrl+C de dung)")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(run(int(os.getenv("PLC_PORT", "5020"))))
    except KeyboardInterrupt:
        print("\nda dung PLC gia lap")
