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
    JOG_VEL_X = 9
    JOG_VEL_Y = 10
    JOG_VEL_Z = 11
    AUTO_HOME = 12   # 1=bat auto-home khi bat dien, 0=tat

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


# Ma ket qua PLC tra ve o HR15
class Result(IntEnum):
    IDLE = 0
    RUNNING = 1
    OK = 2
    ABORTED = 3
    ERROR = 4
    REJECTED = 5


RESULT_TEXT: dict[int, str] = {
    Result.IDLE: "chua chay lenh nao",
    Result.RUNNING: "dang chay",
    Result.OK: "hoan thanh",
    Result.ABORTED: "bi dung giua chung",
    Result.ERROR: "loi",
    Result.REJECTED: "lenh khong hop le hoac may chua san sang",
}


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
        )

    @property
    def result_text(self) -> str:
        return RESULT_TEXT.get(self.result, f"ma la ({self.result})")

    def to_dict(self) -> dict:
        data = asdict(self)
        data["result_text"] = self.result_text
        data["error_id_hex"] = f"0x{self.error_id:04X}"
        return data
