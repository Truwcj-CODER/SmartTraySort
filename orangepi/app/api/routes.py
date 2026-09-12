from __future__ import annotations

import io
import logging

from typing import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from ..geometry import ACCEL_X, ACCEL_Y, ACCEL_Z, Geometry, axis_scale_fields
from ..inventory import Inventory, SlotEmptyError, SlotFullError
from ..plc.protocol import CtrlBit, Param, PlcStatus, Y_SCALED_PARAMS
from ..plc.service import PlcBusyError, PlcCommandError, PlcService
from ..plc.transport import PlcConnectionError
from ..db import ConfigStore
from .schemas import (
    CalibrateRequest,
    CommandOut,
    GeometryIn,
    ItemChange,
    JogRequest,
    MoveRequest,
    OrdersIn,
    ScanOut,
    ScanRequest,
    SlotConfigIn,
    StatusOut,
    TiltRequest,
)

log = logging.getLogger("app.api")

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


# Moi lenh xuong PLC deu di qua day, nen day cung la cho GHI LAI khi that bai.
#
# Truoc day chi tra ma HTTP: doc log thay "POST /api/slots/8/run 503" ma khong
# biet vi sao, phai tu suy tu mot dong WARNING luc khoi dong tit tren dau. Gio
# ly do nam ngay canh, tren cung mot dong.
async def run_command(action: Callable[[], Awaitable[PlcStatus]], message: str) -> CommandOut:
    # 400 tham so sai | 409 dang ban | 422 may tu choi hoac chay hong | 503 mat ket noi
    label = message or "command"
    try:
        status = await action()
    except ValueError as exc:
        log.warning("%s: bad parameter - %s", label, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PlcBusyError as exc:
        log.warning("%s: PLC busy - %s", label, exc)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PlcConnectionError as exc:
        log.error("%s: PLC connection lost - %s", label, exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PlcCommandError as exc:
        log.error("%s: machine rejected or faulted - %s", label, exc)
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


# Lay CHO MAY DANG DUNG lam vi tri cho (HOME).
#
# Nguoi van hanh jog tay toi cho ung y roi bam nut - khong phai go toa do. Cho
# cho vi vay khong con dinh vao diem cam bien: cam bien la LIMIT, co dinh theo
# co khi; HOME la cho dung nghi, muon dat dau thi dat.
@router.post("/park/here", response_model=CommandOut)
async def park_here(request: Request,
                    service: PlcService = Depends(get_service),
                    store: ConfigStore = Depends(get_geometry_store)) -> CommandOut:
    status = service.snapshot["status"]
    if status is None:
        raise HTTPException(status_code=503, detail="chưa đọc được vị trí từ PLC")
    if status["busy"]:
        raise HTTPException(status_code=409,
                            detail="máy đang chạy, dừng lại rồi hãy đặt HOME")

    data = store.read()
    data.update(park_x=status["x"], park_y=status["y"], park_z=status["z"])
    store.write(data)

    geometry = Geometry.from_dict(store.read())
    await service.set_park(geometry.park_x, geometry.park_y, geometry.park_z)
    return CommandOut(
        message=f"đã đặt HOME tại ngang {geometry.park_x:g} · cao {geometry.park_z:g}",
        status=status,
    )


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
        # Toc do qua tran PTO khong lam bo cuc sai, nen di duong rieng voi
        # problems - nhung sau moi lan hieu chinh la cho de vap nhat.
        "speed_warnings": geometry.speed_warnings(),
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
_PUSH_PARAMS = (
    (Param.VEL_X, "vel_x"),
    # Tilt axis: PLC steps 195/300 read VelY. Reuse tilt_vel so this can never
    # exceed the axis ceiling. Never written = VelY keeps its DB init value.
    (Param.VEL_Y, "tilt_vel"),
    (Param.VEL_Z, "vel_z"),
    (Param.TILT_ANGLE, "tilt_angle"),
    (Param.TILT_VEL, "tilt_vel"),
    (Param.DWELL_MS, "dwell_ms"),
    (Param.TILT_HOLD_MS, "tilt_hold_ms"),
    (Param.TILT_COUNT, "tilt_count"),
)


# Gia toc khong nam trong cau hinh nguoi dung sua duoc - no la hang so trong
# geometry.py. Vi the khong so sanh dirty duoc nhu cac tham so tren: cu lan nao
# day ca bo (previous is None) thi ghi lai mot the.
_PUSH_CONSTS = (
    (Param.ACC_X, ACCEL_X),
    (Param.ACC_Y, ACCEL_Y),
    (Param.ACC_Z, ACCEL_Z),
)


def _slot_key(row: dict) -> tuple:
    return (round(float(row["x"]), 2), round(float(row["z"]), 2), int(row["dir"]))


async def send_layout(app, geometry: Geometry, previous: Geometry | None = None) -> str:
    service: PlcService = app.state.plc

    # Truoc moi thu: doi ti le truc Y thi set_park va cac param goc ben duoi
    # phai quy doi theo so moi, khong phai so cua lan day truoc.
    service.y_scale = geometry.y_scale_for_plc()

    # A new Y scale re-values every angle the PLC is already holding: the same
    # degrees, but a different pulse count. None of the geometry fields moved,
    # so the diff below cannot see it - say so outright and resend those.
    y_scale_changed = (previous is not None
                       and geometry.y_scale_for_plc() != previous.y_scale_for_plc())

    plan = geometry.layout()
    rows = geometry.all_positions()
    written = len(rows)

    # previous = None: PLC state unknown -> write everything. With previous:
    # write only what differs from that baseline.
    old_rows = previous.all_positions() if previous is not None else []
    old_key = {r["slot"]: _slot_key(r) for r in old_rows}
    changed_rows = [r for r in rows if old_key.get(r["slot"]) != _slot_key(r)]

    park_now = (geometry.park_x, geometry.park_y, geometry.park_z)
    park_changed = previous is None or y_scale_changed or park_now != (
        previous.park_x, previous.park_y, previous.park_z)
    count_changed = previous is None or len(old_rows) != written

    if previous is None:
        dirty_params = [(p, getattr(geometry, attr)) for p, attr in _PUSH_PARAMS]
        dirty_params += list(_PUSH_CONSTS)
    else:
        dirty_params = [(p, getattr(geometry, attr)) for p, attr in _PUSH_PARAMS
                        if float(getattr(geometry, attr)) != float(getattr(previous, attr))
                        or (y_scale_changed and p in Y_SCALED_PARAMS)]

    if park_changed:
        await service.set_park(*park_now)
    if changed_rows:
        await service.push_table(changed_rows)

    # Hai phan duoi day chi co o ban SCL moi. CPU con chay ban cu thi tu choi,
    # nhung TOA DO da vao roi - khong duoc vi the ma bao ca lan day la that bai.
    thieu: list[str] = []

    if count_changed:
        try:
            await service.set_slot_count(written)
        except PlcCommandError:
            service.slot_count = written
            thieu.append("SỐ rổ")
    else:
        service.slot_count = written

    # Tham so chay may cung phai xuong theo, khong thi web hien mot dang ma may
    # chay mot neo - goc lat la cho de lech nhat.
    if dirty_params:
        try:
            for param, value in dirty_params:
                await service.set_param(param, float(value))
        except PlcCommandError:
            thieu.append("tốc độ và góc lật")

    app.state.inventory.set_active(plan["slots"])

    shape = f"{plan['rows']} hàng × {plan['columns']} cột × 2 bên"
    if previous is None:
        scope = f"toàn bộ {written} tọa độ rổ + vị trí chờ + tham số"
    else:
        bits: list[str] = []
        if changed_rows:
            bits.append(f"{len(changed_rows)} tọa độ rổ")
        if park_changed:
            bits.append("vị trí chờ")
        if count_changed:
            bits.append("số rổ")
        if dirty_params:
            bits.append("tốc độ/góc lật")
        scope = ("phần đã đổi (" + ", ".join(bits) + ")" if bits
                 else "không có gì đổi so với lần trước — PLC đã khớp")

    note = ""
    if thieu:
        note = (f" — nhưng PLC chưa nhận được {' và '.join(thieu)}, "
                f"cần nạp lại khối trong TIA")

    # Keep the old baseline while anything is still missing, so the next save retries it.
    if not thieu:
        app.state.geometry_pushed_store.write(geometry.to_dict())

    return f"đã ghi {scope} xuống PLC ({shape}){note}"


# Ghi cau hinh moi vao kho roi day xuong PLC. Tra ve dung cai payload ma nut
# Luu tren web/app cho doi.
#
# Hai duong vao: nut Luu gui ca form, va lenh hieu chinh chi doi mot con so ti
# le. Cung mot viec thi khong duoc co hai duong code khac nhau - trai lai la co
# ngay mot duong quen day xuong PLC.
async def save_geometry(app, values: dict) -> dict:
    store: ConfigStore = app.state.geometry_store

    # Last geometry pushed to the PLC - the baseline for what differs this time.
    pushed_raw = app.state.geometry_pushed_store.read()
    previous = Geometry.from_dict(pushed_raw) if pushed_raw else None

    store.write(values)
    geometry = Geometry.from_dict(store.read())
    plan = geometry.layout()

    # Bo cuc doi thi so ro doi theo - ton kho phai biet den dong nao con dung.
    inventory: Inventory = app.state.inventory
    orphans = inventory.stock_beyond(plan["slots"])
    inventory.set_active(plan["slots"])
    app.state.plc.slot_count = plan["slots"]

    # Doi cau hinh ma khong day xuong thi web va PLC noi hai chuyen khac nhau:
    # web ve ro o cho moi con may van chay theo bang cu. Day luon cho khoi lech.
    # push_ok la CO BOOLEAN, khong phai de tang tren doan chu. Truoc day app va
    # web deu phai do bang startsWith("CHUA") - doi mot chu trong cau la ca hai
    # cho im lang bao thanh cong trong khi PLC chua nhan gi.
    pushed = None
    push_ok: bool | None = None
    if geometry.problems():
        push_ok = False
        pushed = "chua day xuong PLC: cau hinh chua hop ly"
    else:
        try:
            pushed = await send_layout(app, geometry, previous)
            push_ok = True
        except (PlcBusyError, PlcConnectionError, PlcCommandError) as exc:
            push_ok = False
            pushed = f"CHƯA đẩy xuống PLC được: {exc}"
        except ValueError as exc:
            # Ghi cau hinh trong luc may dang chay chu trinh thi so ro trong
            # service co the con la so cu, va set_slot tu choi. Truoc day loi nay
            # thoat ra thanh 500 trang - nguoi dung khong biet gi.
            push_ok = False
            pushed = f"CHƯA đẩy xuống PLC được: {exc}"

    return {
        "ok": True,
        "geometry": geometry.to_dict(),
        "layout": plan,
        "positions": geometry.all_positions(),
        "problems": geometry.problems(),
        "speed_warnings": geometry.speed_warnings(),
        "pushed": pushed,
        "push_ok": push_ok,
        "orphans": [{"slot": o["slot"], "count": o["count"], "code": o["code"]}
                    for o in orphans],
    }


@router.put("/config/geometry")
async def write_geometry(request: Request, body: GeometryIn) -> dict:
    return await save_geometry(request.app, body.model_dump())


# ----------------------------------------------------------------- hieu chinh

# Ra lenh cho truc chay mot doan da biet, do bang thuoc, roi tinh nguoc ra ti le
# that. Hai buoc tach han nhau:
#
#   preview  chi tinh, KHONG ghi gi ca - chay thu bao nhieu lan cung duoc
#   apply    moi ghi vao cau hinh va day xuong PLC
#
# Tach nhu vay vi con so tinh ra lan dau thuong chua dung: do bang thuoc bao gio
# cung lech mot chut, va phai chay thu lai voi ti le moi de xac nhan. Gop mot
# buoc thi moi lan do hut la mot lan ghi de len cau hinh dang chay.
@router.post("/calibrate/preview")
async def calibrate_preview(request: Request, body: CalibrateRequest) -> dict:
    geometry = current_geometry(request)
    try:
        return geometry.calibrate(body.axis, body.commanded, body.measured)
    except ValueError as exc:
        log.warning("calibrate %s: %s", body.axis, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/calibrate/apply")
async def calibrate_apply(request: Request, body: CalibrateRequest) -> dict:
    geometry = current_geometry(request)
    try:
        result = geometry.calibrate(body.axis, body.commanded, body.measured)
    except ValueError as exc:
        log.warning("calibrate %s: %s", body.axis, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Chi mot o doi. Ghi tron ca form thi cuon theo ban nhap cu tren man hinh
    # nguoi dung dang mo, de len nhung o ho vua sua ma chua luu.
    _, unit_field, _ = axis_scale_fields(body.axis)
    values = {**geometry.to_dict(), unit_field: result["proposed"][unit_field]}

    try:
        saved = await save_geometry(request.app, values)
    except (PlcBusyError, PlcConnectionError, PlcCommandError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    log.info("calibrated axis %s: %s %s -> %s", body.axis, unit_field,
             result["current"][unit_field], result["proposed"][unit_field])
    return {**saved, "calibration": result}


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


# ------------------------------------------------------------------- don hang

# Cho he tren day don xuong. Trong that day la mot consumer Kafka goi vao day;
# doi sang nguon khac thi chi thay cho goi, phan con lai khong doi.
@router.post("/orders")
async def push_orders(body: OrdersIn, inventory: Inventory = Depends(get_inventory)) -> dict:
    try:
        result = inventory.assign_orders(
            [o.model_dump() for o in body.orders], reset=body.reset
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "ok": True,
        "orders": result["placed"],
        # Don chua co ro - het ro trong. He tren giu lai day sau, dung coi la loi.
        "pending": result["pending"],
        "summary": inventory.summary(),
    }


# Don da lay di: tra ro ve trong cho don sau vao.
#
# Ba duong cung goi vao day: Kafka ban event xuat kho, nguoi quet lai ma QR cua
# don luc bung thung, hoac bam nut tren tablet. Server khong tu doan duoc - viec
# be hang di xay ra ngoai doi, phai co ai bao.
@router.post("/orders/{code}/done")
async def finish_order(code: str, inventory: Inventory = Depends(get_inventory)) -> dict:
    freed = inventory.release_order(code)
    if freed is None:
        raise HTTPException(status_code=404, detail=f"khong co don {code} tren gian ro")
    return {"ok": True, **freed, "summary": inventory.summary()}


@router.get("/orders")
async def list_orders(inventory: Inventory = Depends(get_inventory)) -> dict:
    # queue: don da nhan nhung chua co ro. Ro nao trong ra la tu dong nhet vao.
    return {"orders": inventory.orders(), "queue": inventory.queue}


# Tra cuu mot ma - KHONG dung toi ton kho. Quet ma QR cua don de XEM don do
# gom nhung gi, con thieu mon nao; hoac quet ma mot vat de biet no thuoc don nao.
@router.post("/lookup")
async def lookup(body: ScanRequest, inventory: Inventory = Depends(get_inventory)) -> dict:
    code = body.code.strip()
    order = inventory.order_of_sku(code)
    detail = inventory.order_detail(code=order or code)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"ma {code} khong thuoc don nao")
    return {
        "code": code,
        "matched": "sku" if order else "order",
        "order": detail,
    }


@router.get("/orders/{slot}")
async def order_at_slot(slot: int, inventory: Inventory = Depends(get_inventory)) -> dict:
    detail = inventory.order_detail(slot=slot)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"khay {slot} chua gan don nao")
    return {"order": detail}


# QR code (SVG) for an order code. The web order line and the app both show one
# so the picker at the end of the line can scan it back in.
@router.get("/orders/{code}/qr")
async def order_qr(code: str) -> Response:
    import segno

    buf = io.BytesIO()
    # micro=False: dien thoai binh thuong khong doc duoc Micro QR, ma segno tu
    # chon no cho chuoi ngan. error="q" du du phong de quet nhanh.
    segno.make(code.strip(), error="q", micro=False).save(
        buf, kind="svg", scale=1, border=4, dark="#000000", light="#ffffff",
    )
    return Response(buf.getvalue(), media_type="image/svg+xml",
                    headers={"Cache-Control": "max-age=300"})


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

    # Quet lai ma cua mot don DA DU nghia la dang bung thung di, khong phai bo
    # them vat vao. Don du roi thi khong con ly do gi quet them - nen luat nay
    # khong nhap nhang, va nguoi thao tac khong phai bam nut rieng nao.
    taken = inventory.order_detail(code=code)
    if taken is not None and taken["complete"]:
        freed = inventory.release_order(code)
        return ScanOut(
            code=code,
            slot=freed["slot"],
            message=f"don {code} da lay di, khay {freed['slot']} tro ve trong",
            inventory={"slot": inventory.slot(freed["slot"]),
                       "summary": inventory.summary(), "order": None},
            status=None,
        )

    slot = inventory.find_slot_for_code(code)
    order = inventory.order_of_sku(code)

    # Khong lan ra ro thi TU CHOI, khong quang dai vao ro trong dau tien. Nhanh
    # cu lam vay, va do la lam ban don cua nguoi khac: vat la nam trong ro cua
    # mot don that, den luc dong goi moi lo ra thua mot mon khong ai biet o dau.
    #
    # Nhung phai noi dung LY DO. Hai truong hop khac nhau han:
    #   - Ma thuoc mot don DANG CHO ro: cho nguoi van hanh biet de vat sang mot
    #     ben, va biet phai lay bot don da du ra thi moi quet duoc.
    #   - Ma khong thuoc don nao: hang la, hoac quet sai.
    # Truoc day ca hai deu bao "khong thuoc don nao" - cau do noi SAI o truong
    # hop dau, va nguoi van hanh khong biet phai lam gi.
    if slot is None:
        cho = inventory.queued_order_of_sku(code)
        if cho:
            raise HTTPException(
                status_code=409,
                detail=f"ma {code} thuoc don {cho} - don nay dang cho khay. "
                       f"Lay bot don da du ra roi quet lai.",
            )
        raise HTTPException(
            status_code=404,
            detail=f"ma {code} khong thuoc don nao",
        )

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
    inventory.mark_scanned(code)
    detail = inventory.order_detail(slot=slot)
    if order:
        progress = f" {detail['done']}/{detail['total']}" if detail else ""
        note = f" (don {order}{progress})"
    else:
        note = ""
    return ScanOut(
        code=code,
        slot=slot,
        message=f"ma {code} -> khay {slot}{note}, con {entry['capacity'] - entry['count']} cho",
        inventory={
            "slot": entry,
            "summary": inventory.summary(),
            "order": detail,
        },
        status=status,
    )
