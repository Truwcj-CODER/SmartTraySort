from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Request

from ..geometry import ACCEL_X, ACCEL_Y, ACCEL_Z, Geometry
from ..inventory import Inventory, SlotEmptyError, SlotFullError
from ..plc.protocol import CtrlBit, Param, PlcStatus
from ..plc.service import PlcBusyError, PlcCommandError, PlcService
from ..plc.transport import PlcConnectionError
from ..db import ConfigStore
from .schemas import (
    CommandOut,
    GeometryIn,
    ItemChange,
    JogRequest,
    MoveRequest,
    ScanOut,
    ScanRequest,
    SlotConfigIn,
    StatusOut,
    TiltRequest,
)

router = APIRouter(prefix="/api", tags=["may"])


# ------------------------------------------------------------------ phu thuoc
def get_service(request: Request) -> PlcService:
    return request.app.state.plc


def get_inventory(request: Request) -> Inventory:
    return request.app.state.inventory


def get_geometry_store(request: Request) -> ConfigStore:
    return request.app.state.geometry_store


def current_geometry(request: Request) -> Geometry:
    return Geometry.from_dict(request.app.state.geometry_store.read())


async def run_command(action: Callable[[], Awaitable[PlcStatus]], message: str) -> CommandOut:
    # 400 tham so sai | 409 dang ban | 422 may tu choi hoac chay hong | 503 mat ket noi
    try:
        status = await action()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PlcBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PlcConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PlcCommandError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return CommandOut(message=message, status=status.to_dict() if status else None)


# ------------------------------------------------------------------ trang thai
@router.get("/status", response_model=StatusOut)
async def read_status(service: PlcService = Depends(get_service)) -> StatusOut:
    return StatusOut(**service.snapshot)


# Ghep toa do hinh hoc voi ton kho - giao dien chi can goi mot cho.
#
# Nhan thang app chu khong phai Request: duong SSE cung dung lai ham nay ma luc
# do khong co request nao ca. Mot cho tinh, hai duong ra - web va app luon
# nhin thay cung mot bang.
def slots_payload(app) -> dict:
    geometry = Geometry.from_dict(app.state.geometry_store.read())
    inventory: Inventory = app.state.inventory
    stock = {s["slot"]: s for s in inventory.slots}

    rows = []
    for pos in geometry.all_positions():
        entry = stock[pos["slot"]]
        rows.append({
            **pos,
            "code": entry["code"],
            "count": entry["count"],
            "capacity": entry["capacity"],
            "full": entry["count"] >= entry["capacity"],
            "updated_at": entry["updated_at"],
        })
    return {"slots": rows, "summary": inventory.summary()}


@router.get("/slots")
async def list_slots(request: Request) -> dict:
    return slots_payload(request.app)


# --------------------------------------------------------------------- lenh may
@router.post("/home", response_model=CommandOut)
async def home(service: PlcService = Depends(get_service)) -> CommandOut:
    return await run_command(service.home, "da lay goc toa do")


@router.post("/slots/{slot}/run", response_model=CommandOut)
async def run_slot(slot: int, service: PlcService = Depends(get_service)) -> CommandOut:
    return await run_command(lambda: service.run_slot(slot), f"da chay chu trinh khay {slot}")


@router.post("/slots/{slot}/goto", response_model=CommandOut)
async def goto_slot(slot: int, service: PlcService = Depends(get_service)) -> CommandOut:
    return await run_command(lambda: service.goto_slot(slot), f"da toi khay {slot}")


@router.post("/slots/{slot}/tilt", response_model=CommandOut)
async def tilt_slot(slot: int, service: PlcService = Depends(get_service)) -> CommandOut:
    return await run_command(lambda: service.tilt_slot(slot), f"da lat tai khay {slot}")


@router.post("/slots/{slot}/teach", response_model=CommandOut)
async def teach_slot(slot: int, service: PlcService = Depends(get_service)) -> CommandOut:
    return await run_command(
        lambda: service.teach_slot(slot), f"da luu vi tri hien tai vao khay {slot}"
    )


@router.post("/move", response_model=CommandOut)
async def move_to(body: MoveRequest, service: PlcService = Depends(get_service)) -> CommandOut:
    return await run_command(
        lambda: service.move_to(body.x, body.z), f"da toi ngang {body.x} cao {body.z}"
    )


@router.post("/tilt", response_model=CommandOut)
async def tilt_to(body: TiltRequest, service: PlcService = Depends(get_service)) -> CommandOut:
    return await run_command(lambda: service.tilt_to(body.angle), f"da lat toi {body.angle} do")


@router.post("/park", response_model=CommandOut)
async def park(service: PlcService = Depends(get_service)) -> CommandOut:
    return await run_command(service.park, "da ve vi tri cho")


# ------------------------------------------------------- lenh xu ly tuc thi
@router.post("/stop", response_model=CommandOut)
async def emergency_stop(service: PlcService = Depends(get_service)) -> CommandOut:
    try:
        await service.emergency_stop()
    except PlcConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return CommandOut(message="da gui lenh dung")


@router.post("/reset", response_model=CommandOut)
async def reset_fault(service: PlcService = Depends(get_service)) -> CommandOut:
    try:
        await service.reset_fault()
    except PlcConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return CommandOut(message="da gui lenh xoa loi")


# --------------------------------------------------------------------- jog tay
JOG_BITS = {
    "x_pos": CtrlBit.JOG_X_POS, "x_neg": CtrlBit.JOG_X_NEG,
    "y_pos": CtrlBit.JOG_Y_POS, "y_neg": CtrlBit.JOG_Y_NEG,
    "z_pos": CtrlBit.JOG_Z_POS, "z_neg": CtrlBit.JOG_Z_NEG,
}


@router.post("/jog", response_model=CommandOut)
async def jog(body: JogRequest, service: PlcService = Depends(get_service)) -> CommandOut:
    bits = CtrlBit.NONE
    for field, bit in JOG_BITS.items():
        if getattr(body, field):
            bits |= bit

    try:
        await service.set_jog(bits)
    except PlcConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return CommandOut(message="da cap nhat jog")


# --------------------------------------------------------------------- cau hinh
def geometry_payload(app) -> dict:
    geometry = Geometry.from_dict(app.state.geometry_store.read())
    plan = geometry.layout()
    return {
        "geometry": geometry.to_dict(),
        "layout": plan,
        "positions": geometry.all_positions(),
        "derived": {
            "so_ro": f"{plan['slots']} rổ — {plan['rows']} hàng × {plan['columns']} cột × 2 bên",
            "buoc_ngang_mm": round(geometry.x_pitch, 1),
            "khe_ho_that_mm": round(geometry.x_gap, 1),
            "buoc_hang_mm": round(geometry.row_pitch, 1),
            "x_pulses_per_mm": round(geometry.pulses_per_mm("x"), 3),
            "z_pulses_per_mm": round(geometry.pulses_per_mm("z"), 3),
            "y_pulses_per_degree": round(geometry.pulses_per_degree(), 3),
            "x_pulses_full_travel": geometry.pulses_for_full_travel("x"),
            "z_pulses_full_travel": geometry.pulses_for_full_travel("z"),
            "y_pulses_full_range": geometry.pulses_for_full_travel("y"),
            "x_max_velocity_mm_s": round(geometry.max_velocity("x"), 1),
            "z_max_velocity_mm_s": round(geometry.max_velocity("z"), 1),
            "y_max_velocity_deg_s": round(geometry.max_velocity("y"), 1),
        },
        "problems": geometry.problems(),
    }


@router.get("/config/geometry")
async def read_geometry(request: Request) -> dict:
    return geometry_payload(request.app)


# Ghi vi tri cho + ca bang toa do + so ro xuong PLC. Tra ve cau bao ket qua.
#
# Tach rieng vi co hai loi vao: bam nut Day toa do, va luu cau hinh (luc do
# day tu dong). Cung mot viec thi khong duoc co hai duong code khac nhau.
# Nhan thang doi tuong app chu khong phai Request: vong dong bo luc PLC vua noi
# lai cung goi ham nay, ma luc do khong co request nao ca.
async def send_layout(app, geometry: Geometry) -> str:
    service: PlcService = app.state.plc
    plan = geometry.layout()

    await service.set_park(geometry.park_x, geometry.park_y, geometry.park_z)
    written = await service.push_table(geometry.all_positions())

    # Hai phan duoi day chi co o ban SCL moi. CPU con chay ban cu thi tu choi,
    # nhung TOA DO da vao roi - khong duoc vi the ma bao ca lan day la that bai.
    thieu: list[str] = []

    try:
        # Bao so luong SAU khi ghi xong toa do, khong thi PLC co the nhan lenh
        # chay toi mot ro ma toa do chua kip ghi.
        await service.set_slot_count(written)
    except PlcCommandError:
        service.slot_count = written
        thieu.append("SỐ rổ")

    # Tham so chay may cung phai xuong theo, khong thi web hien mot dang ma may
    # chay mot neo - goc lat la cho de lech nhat.
    try:
        for param, value in (
            # Gia toc sua thang DynamicDefaults cua truc. Khong co tham so nao
            # cho tran toc do: MaxVelocity la read-only tren Technology Object,
            # chi dat duoc trong TIA. Server chi lo chan de vel_x/vel_z khong
            # vuot tran do - xem Geometry.velocity_limits().
            (Param.ACC_X, ACCEL_X),
            (Param.ACC_Y, ACCEL_Y),
            (Param.ACC_Z, ACCEL_Z),
            (Param.VEL_X, geometry.vel_x),
            (Param.VEL_Y, geometry.tilt_vel),   # truc lat: buoc TILT_TO dung VelY, cho = tilt_vel de khong vuot tran
            (Param.VEL_Z, geometry.vel_z),
            (Param.TILT_ANGLE, geometry.tilt_angle),
            (Param.TILT_VEL, geometry.tilt_vel),
            (Param.DWELL_MS, geometry.dwell_ms),
            (Param.TILT_HOLD_MS, geometry.tilt_hold_ms),
            (Param.TILT_COUNT, geometry.tilt_count),
            (Param.AUTO_HOME, geometry.auto_home),
        ):
            await service.set_param(param, float(value))
    except PlcCommandError:
        thieu.append("tốc độ và góc lật")

    shape = f"{plan['rows']} hàng × {plan['columns']} cột × 2 bên"
    note = ""
    if thieu:
        note = (f" — nhưng PLC chưa nhận được {' và '.join(thieu)}, "
                f"cần nạp lại khối trong TIA")

    app.state.inventory.set_active(plan["slots"])
    return f"đã ghi vị trí chờ + {written} tọa độ rổ xuống PLC ({shape}){note}"


@router.put("/config/geometry")
async def write_geometry(request: Request, body: GeometryIn,
                         store: ConfigStore = Depends(get_geometry_store)) -> dict:
    store.write(body.model_dump())
    geometry = Geometry.from_dict(store.read())
    plan = geometry.layout()

    # Bo cuc doi thi so ro doi theo - ton kho phai biet den dong nao con dung.
    inventory: Inventory = request.app.state.inventory
    orphans = inventory.stock_beyond(plan["slots"])
    inventory.set_active(plan["slots"])
    request.app.state.plc.slot_count = plan["slots"]

    # Doi cau hinh ma khong day xuong thi web va PLC noi hai chuyen khac nhau:
    # web ve ro o cho moi con may van chay theo bang cu. Day luon cho khoi lech.
    pushed = None
    if not geometry.problems():
        try:
            pushed = await send_layout(request.app, geometry)
        except (PlcBusyError, PlcConnectionError, PlcCommandError) as exc:
            pushed = f"CHƯA đẩy xuống PLC được: {exc}"

    return {
        "ok": True,
        "geometry": geometry.to_dict(),
        "layout": plan,
        "positions": geometry.all_positions(),
        "problems": geometry.problems(),
        "pushed": pushed,
        "orphans": [{"slot": o["slot"], "count": o["count"], "code": o["code"]}
                    for o in orphans],
    }


# Day ca gian ro tinh tu cau hinh xuong bang toa do trong PLC.
@router.post("/config/push", response_model=CommandOut)
async def push_table(request: Request) -> CommandOut:
    geometry = current_geometry(request)
    problems = geometry.problems()
    if problems:
        raise HTTPException(status_code=400, detail="; ".join(problems[:3]))

    try:
        return CommandOut(message=await send_layout(request.app, geometry))
    except PlcBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PlcConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PlcCommandError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# --------------------------------------------------------------------- ton kho
@router.put("/slots/{slot}/config")
async def configure_slot(
    slot: int, body: SlotConfigIn, inventory: Inventory = Depends(get_inventory)
) -> dict:
    try:
        if body.code is not None:
            inventory.assign_code(slot, body.code)
        if body.capacity is not None:
            inventory.set_capacity(slot, body.capacity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "slot": inventory.slot(slot)}


@router.post("/slots/{slot}/items")
async def add_items(
    slot: int, body: ItemChange, inventory: Inventory = Depends(get_inventory)
) -> dict:
    try:
        entry = inventory.add_item(slot, body.amount)
    except SlotFullError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "slot": entry, "summary": inventory.summary()}


@router.delete("/slots/{slot}/items")
async def remove_items(
    slot: int, amount: int = 1, inventory: Inventory = Depends(get_inventory)
) -> dict:
    try:
        entry = inventory.remove_item(slot, amount)
    except SlotEmptyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "slot": entry, "summary": inventory.summary()}


@router.post("/inventory/reset")
async def reset_inventory(inventory: Inventory = Depends(get_inventory)) -> dict:
    return {"ok": True, "slots": inventory.reset(), "summary": inventory.summary()}


# --------------------------------------------------------------------- quet ma

# Quet ma -> tra ra khay -> chay may -> cong ton kho.
#
# Ma da gan cho khay nao thi vao khay do. Chua gan thi lay khay trong dau tien.
# Ton kho chi cong SAU khi may chay xong, de lenh that bai khong lam sai so lieu.
@router.post("/scan", response_model=ScanOut)
async def scan(
    body: ScanRequest,
    service: PlcService = Depends(get_service),
    inventory: Inventory = Depends(get_inventory),
) -> ScanOut:
    code = body.code.strip()
    slot = inventory.find_slot_for_code(code)
    auto_picked = slot is None

    if slot is None:
        slot = inventory.first_free_slot()
        if slot is None:
            raise HTTPException(status_code=409, detail="tat ca khay da day")

    entry = inventory.slot(slot)
    if entry["count"] >= entry["capacity"]:
        raise HTTPException(
            status_code=409,
            detail=f"khay {slot} da day ({entry['count']}/{entry['capacity']})",
        )

    status = None
    if body.run:
        result = await run_command(lambda: service.run_slot(slot), "")
        status = result.status

    entry = inventory.add_item(slot)
    note = " (tu chon khay trong)" if auto_picked else ""
    return ScanOut(
        code=code,
        slot=slot,
        message=f"ma {code} -> khay {slot}{note}, con {entry['capacity'] - entry['count']} cho",
        inventory={"slot": entry, "summary": inventory.summary()},
        status=status,
    )
