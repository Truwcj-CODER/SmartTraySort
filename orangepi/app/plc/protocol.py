from __future__ import annotations

import struct
from dataclasses import dataclass, asdict
from enum import IntEnum, IntFlag

# ---------------------------------------------------------------- ban do thanh ghi

# Khoi client GHI XUONG: HR0..HR9, luon ghi tron khoi bang 1 lenh FC16
ADDR_WRITE_BLOCK = 0
SIZE_WRITE_BLOCK = 10

# Khoi PLC TRA VE: HR10..HR23, chi doc
ADDR_STATUS_BLOCK = 10
SIZE_STATUS_BLOCK = 14

# Chi cap nhat rieng o dieu khien (bit jog / cap dien)
ADDR_CTRL = 2


# Ma lenh ghi vao HR0, khop bang trong 01_Types.scl
#   Truc X = ngang qua lai | Truc Y = lat trai phai | Truc Z = len xuong
class Command(IntEnum):
    NONE = 0
    AUTO = 1       # toi khay -> dung -> lat dung ben -> ve cho
    HOME = 2       # chay lay goc toa do ca 3 truc
    STOP = 3
    RESET = 4
    TEACH = 5      # luu vi tri hien tai vao khay
    GOTO = 6       # chi di toi khay
    TILT = 7       # chi lat tai cho theo chieu cua khay
    MOVE_XZ = 8    # di toi vi tri tu do (ngang + cao)
    PARK = 9       # ve vi tri cho
    TILT_TO = 10   # lat truc Y toi mot goc cu the
    SET_SLOT = 11  # ghi toa do 1 khay xuong PLC
    SET_PARK = 12  # ghi vi tri cho (giua gian khay, noi lap cam bien)
    SET_COUNT = 13  # bao cho PLC biet bo cuc hien co bao nhieu ro
    SET_PARAM = 14  # ghi mot tham so chay may, xem lop Param


# Ma tham so cho lenh SET_PARAM. Phai trung CASE #SelPos trong 04_FB_XY_Tray.scl
class Param(IntEnum):
    VEL_X = 1        # mm/s
    VEL_Y = 2        # do/s
    VEL_Z = 3        # mm/s
    TILT_ANGLE = 4   # do
    TILT_VEL = 5     # do/s
    DWELL_MS = 6     # ms, dung yen tai ro cho het rung
    TILT_HOLD_MS = 7  # ms, giu o goc lat
    TILT_COUNT = 8   # so lan lat
    # KHONG CON TAC DUNG. Ca may gio chi dung MOT bo toc do: jog tay, chay tu
    # dong va do cam bien luc home deu lay VelX / TiltVel / VelZ. PLC van nhan ba
    # ma nay va ghi vao DB_TrayTable, nhung khong cho nao doc toi nua.
    # Giu lai de tools/home_test.py cu khong bao loi khi gui xuong.
    SEEK_VEL_X = 9
    SEEK_VEL_Y = 10
    SEEK_VEL_Z = 11
    # KHONG CON TAC DUNG. May LUON tu lay goc sau khi mat dien truc - do la
    # viec bat buoc, khong phai tuy chon. PLC van nhan ma nay nhung FB khong
    # doc UseAutoHome nua.
    AUTO_HOME = 12

    # 16..18 khong ghi vao bang tham so ma sua thang DynamicDefaults cua
    # Technology Object, tuc gia toc dung cho moi lenh chay.
    #
    # Khong co ma cho MaxVelocity: DynamicLimits.MaxVelocity la read-only tren
    # TO_PositioningAxis V8, chi dat duoc trong TIA. Con so do la tran ma
    # Geometry.max_velocity() dung de chan vel_x/vel_z tu phia web. Bo trong
    # 13..15 cho khoi lech so voi bang ma trong 01_Types.scl.
    ACC_X = 16       # mm/s2, dung luon cho ca ham va ham khan cap
    ACC_Y = 17       # do/s2
    ACC_Z = 18       # mm/s2


# Params carrying an angle, an angular rate or an angular acceleration on the
# tilt axis. Axis_Y in TIA is scaled in pulses, so these are the values
# PlcService converts on the way down. A degree, a degree per second and a
# degree per second squared all scale by the same pulses-per-degree factor, so
# one set covers all three. Everything else in Param is mm, ms or a plain
# count - never scaled.
Y_SCALED_PARAMS = frozenset({
    Param.VEL_Y,
    Param.TILT_ANGLE,
    Param.TILT_VEL,
    Param.SEEK_VEL_Y,
    Param.ACC_Y,
})


# Ma ket qua PLC tra ve o HR15
class Result(IntEnum):
    IDLE = 0
    RUNNING = 1
    OK = 2
    ABORTED = 3
    ERROR = 4
    REJECTED = 5
    # Cham vach gioi han: truc do ngung, truc con lai chay not. Khong phai loi -
    # tach rieng khoi ABORTED de nhat ky khong bao "that bai" khi may chay dung.
    LIMIT = 6


RESULT_TEXT: dict[int, str] = {
    Result.IDLE: "chưa chạy lệnh nào",
    Result.RUNNING: "đang chạy",
    Result.OK: "hoàn thành",
    Result.ABORTED: "bị dừng giữa chừng",
    Result.ERROR: "lỗi",
    Result.REJECTED: "lệnh không hợp lệ hoặc máy chưa sẵn sàng",
    Result.LIMIT: "dừng vì chạm vạch giới hạn",
}


# Ket qua KHONG phai loi. Ngoai OK ra con LIMIT: cham vach gioi han la may lam
# dung viec cua no, khong phai hong hoc gi - bao len nhu mot ket qua binh thuong.
RESULT_OK = frozenset({Result.OK, Result.LIMIT})


# Cac bit trong HR2
class CtrlBit(IntFlag):
    NONE = 0
    JOG_X_POS = 1 << 0   # ngang, chieu duong
    JOG_X_NEG = 1 << 1
    JOG_Y_POS = 1 << 2   # lat sang phai
    JOG_Y_NEG = 1 << 3   # lat sang trai
    JOG_Z_POS = 1 << 4   # len
    JOG_Z_NEG = 1 << 5   # xuong
    AXES_ENABLE = 1 << 8   # = 256, khong bat thi truc khong co dien


# Cac bit trong HR10
class StatusBit(IntFlag):
    READY = 1 << 0
    BUSY = 1 << 1
    DONE = 1 << 2
    HOMED = 1 << 3
    ERROR = 1 << 4

    # Bit 8..12: trang thai CAM BIEN, chi de xem. Ten dat theo CHAN chu khong
    # theo cong dung, vi chinh cai dang phai lam ro la chan nao noi voi cai gi.
    IN_00 = 1 << 8    # IO_List: STOP_BTN  | FB_XY_Tray doc lam X home
    IN_01 = 1 << 9    # IO_List: X_MIN     | FB_XY_Tray doc lam Z home
    IN_03 = 1 << 10   # IO_List: Z_HOME
    IN_06 = 1 << 11   # IO_List: Y_HOME
    IN_10 = 1 << 12   # IO_List: X_HOME (doi tu %I0.0 sang)
    IN_07 = 1 << 13   # START/STOP: tiep diem NO 8-12 cua relay K1


SEQ_MAX = 65535


# ---------------------------------------------------------------- so thuc 32 bit
def encode_f32(value: float) -> tuple[int, int]:
    hi, lo = struct.unpack(">HH", struct.pack(">f", float(value)))
    return hi, lo


def decode_f32(hi: int, lo: int) -> float:
    return struct.unpack(">f", struct.pack(">HH", hi & 0xFFFF, lo & 0xFFFF))[0]


def next_seq(current: int) -> int:
    # quay vong 1..65535, bo qua 0 de khong lan voi gia tri mac dinh
    return current % SEQ_MAX + 1


# ---------------------------------------------------------------- dong goi lenh
def build_command_frame(
    command: Command,
    seq: int,
    *,
    slot: int = 0,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    ctrl: CtrlBit = CtrlBit.AXES_ENABLE,
) -> list[int]:
    # ghi tron khoi HR0..HR9: MB_SERVER xu ly het 1 yeu cau trong 1 vong quet nen PLC
    # khong bao gio doc phai trang thai nua voi (Command moi ma SelPos con cu)
    hi_x, lo_x = encode_f32(x)
    hi_y, lo_y = encode_f32(y)
    hi_z, lo_z = encode_f32(z)
    return [int(command), int(slot), int(ctrl), int(seq),
            hi_x, lo_x, hi_y, lo_y, hi_z, lo_z]


def build_ctrl_frame(ctrl: CtrlBit) -> list[int]:
    return [int(ctrl)]


# ---------------------------------------------------------------- giai ma trang thai
@dataclass(frozen=True)
class PlcStatus:
    ready: bool
    busy: bool
    done: bool
    homed: bool
    error: bool
    step: int
    error_id: int
    ack_seq: int
    done_seq: int
    result: int
    x: float      # vi tri ngang (mm)
    y: float      # goc lat (do)
    z: float      # do cao (mm)
    slot: int
    # Trang thai cac chan cam bien, khoa la ten CHAN (%I0.0 -> "I0.0"). Chi de
    # xem tren web: che tay vao cam bien roi nhin chan nao len TRUE la biet no
    # noi vao dau, khoi phai mo TIA di do.
    inputs: dict

    @classmethod
    def from_registers(cls, regs: list[int]) -> "PlcStatus":
        if len(regs) < SIZE_STATUS_BLOCK:
            raise ValueError(
                f"khoi trang thai can {SIZE_STATUS_BLOCK} thanh ghi, nhan duoc {len(regs)}"
            )
        bits = regs[0]
        return cls(
            ready=bool(bits & StatusBit.READY),
            busy=bool(bits & StatusBit.BUSY),
            done=bool(bits & StatusBit.DONE),
            homed=bool(bits & StatusBit.HOMED),
            error=bool(bits & StatusBit.ERROR),
            step=regs[1],
            error_id=regs[2],
            ack_seq=regs[3],
            done_seq=regs[4],
            result=regs[5],
            x=round(decode_f32(regs[6], regs[7]), 3),
            y=round(decode_f32(regs[8], regs[9]), 3),
            z=round(decode_f32(regs[10], regs[11]), 3),
            slot=regs[12],
            inputs={
                "I0.0": bool(bits & StatusBit.IN_00),
                "I0.1": bool(bits & StatusBit.IN_01),
                "I0.3": bool(bits & StatusBit.IN_03),
                "I0.6": bool(bits & StatusBit.IN_06),
                "I1.0": bool(bits & StatusBit.IN_10),
                "I0.7": bool(bits & StatusBit.IN_07),
            },
        )

    @property
    def result_text(self) -> str:
        return RESULT_TEXT.get(self.result, f"mã lạ ({self.result})")

    def to_dict(self) -> dict:
        data = asdict(self)
        data["result_text"] = self.result_text
        data["error_id_hex"] = f"0x{self.error_id:04X}"
        return data
