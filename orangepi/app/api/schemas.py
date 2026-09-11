from __future__ import annotations

from pydantic import BaseModel, Field


# ------------------------------------------------------------------ chuyen dong
class MoveRequest(BaseModel):
    x: float = Field(..., description="Vi tri ngang, mm")
    z: float = Field(..., description="Do cao, mm")


class TiltRequest(BaseModel):
    angle: float = Field(..., description="Goc lat, do. Duong = phai, am = trai")


class JogRequest(BaseModel):
    x_pos: bool = False
    x_neg: bool = False
    y_pos: bool = False
    y_neg: bool = False
    z_pos: bool = False
    z_neg: bool = False


# ------------------------------------------------------------------ cau hinh
class GeometryIn(BaseModel):
    # Cot va hang KHONG khai bao. Server tu tinh tu hanh trinh va kich thuoc ro.
    x_first: float = Field(200.0, description="Tam ro cot dau tien, mm")
    z_first: float = Field(100.0, description="Mieng ro hang duoi cung, mm")

    basket_length: float = Field(90.0, gt=0, description="Ro dai bao nhieu doc truc X, mm")
    basket_depth: float = Field(200.0, gt=0, description="Ro sau bao nhieu, mm")
    basket_height: float = Field(90.0, gt=0, description="Chieu cao thanh ro, mm")
    basket_gap: float = Field(10.0, ge=0, description="Khe ho giua 2 ro ke nhau, mm")

    rack_offset: float = Field(95.0, gt=0, description="Tu tam ray toi mep trong ro, mm")
    drop_lift: float = Field(90.0, ge=0, description="Khay cao hon mieng ro, mm")
    tray_width: float = Field(200.0, gt=0, description="Be rong khay dung, mm")
    tray_length: float = Field(200.0, gt=0, description="Chieu dai khay dung doc truc X, mm")

    # vi tri cho - noi may dung giua hai chu trinh
    park_x: float = Field(650.0, description="Vi tri cho, ngang, mm")
    park_y: float = Field(0.0, description="Vi tri cho, goc lat, do")
    park_z: float = Field(0.0, description="Vi tri cho, cao, mm")

    # hanh trinh toi da tung truc
    x_travel: float = Field(1300.0, gt=0, description="Hanh trinh ngang, mm")
    z_travel: float = Field(400.0, gt=0, description="Hanh trinh len xuong, mm")
    y_max_angle: float = Field(70.0, gt=0, description="Goc lat toi da cho phep, do")
    # --- tham so chay may, day xuong PLC bang lenh 14 ---
    tilt_angle: float = Field(60.0, gt=0, description="Goc lat khi do vat, do")
    tilt_vel: float = Field(200.0, gt=0, description="Toc do lat, do/s")
    tilt_hold_ms: int = Field(1000, ge=0, description="Giu o goc lat, ms")
    tilt_count: int = Field(1, ge=0, description="So lan lat moi chu trinh")
    auto_home: bool = Field(True, description="Tu HOME khi bat dien")
    vel_x: float = Field(80.0, gt=0, description="Toc do chay ngang, mm/s")
    vel_z: float = Field(60.0, gt=0, description="Toc do len xuong, mm/s")
    dwell_ms: int = Field(1000, ge=0, description="Dung yen tai ro, ms")

    # Tham so co khi - chi de doi chieu va canh bao toc do.
    # PHAI nhap trung voi Technology Object trong TIA, server khong ghi xuong PLC duoc.
    x_pulses_per_rev: int = Field(3200, gt=0)
    x_mm_per_rev: float = Field(32.0, gt=0)
    z_pulses_per_rev: int = Field(2000, gt=0)
    z_mm_per_rev: float = Field(54.0, gt=0)
    y_pulses_per_rev: int = Field(1000, gt=0)
    y_deg_per_rev: float = Field(360.0, gt=0)


# ------------------------------------------------------------------ ton kho
class SlotConfigIn(BaseModel):
    code: str | None = Field(None, description="Ma hang gan cho khay")
    capacity: int | None = Field(None, ge=0, description="Suc chua toi da")


class ItemChange(BaseModel):
    amount: int = Field(1, ge=1)


class ScanRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Ma vua quet duoc")
    run: bool = Field(True, description="Quet xong chay may luon hay chi tra ve so khay")


# ------------------------------------------------------------------ tra ve
class StatusOut(BaseModel):
    online: bool
    endpoint: str
    last_error: str | None = None
    slot_count: int
    status: dict | None = None


class CommandOut(BaseModel):
    ok: bool = True
    message: str
    status: dict | None = None


class ScanOut(BaseModel):
    ok: bool = True
    code: str
    slot: int
    message: str
    inventory: dict | None = None
    status: dict | None = None
