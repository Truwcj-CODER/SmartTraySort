# Duong phat trang thai mot chieu cho app Android, dung Server-Sent Events.
#
# Vi sao khong dung chung WebSocket voi web: SSE la HTTP thuong, di qua duoc moi
# proxy, tu noi lai khi rot song, va tren Android chi can OkHttp - khong keo
# them thu vien websocket nao. Doi lai la chi gui duoc mot chieu, ma app cung
# chi can co the: lenh van di bang REST nhu cu.
#
# Ba loai su kien, app nghe het la khong phai hoi vong lan nao nua:
#   status     moi vong poll PLC   - vi tri 3 truc, buoc, loi
#   inventory  khi bang ro doi     - so vat trong tung ro
#   layout     khi cau hinh doi    - toa do ro, quy doi, canh bao
#
# Hai loai sau chi gui khi so revision doi, nen dung yen thi duong truyen chi co
# vai chuc byte moi giay.
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..plc.service import PlcService
from .routes import geometry_payload, slots_payload

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["may"])

# Khong co gi de gui trong ngan nay thi day mot dong chu thich cho proxy va
# tang di dong khoi cat ket noi vi tuong da chet.
HEARTBEAT = 15.0


def frame(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


async def _events(request: Request) -> AsyncIterator[str]:
    app = request.app
    service: PlcService = app.state.plc
    queue = service.subscribe()

    inventory_rev = -1
    geometry_rev = -1

    try:
        # Ban dau day du ba loai mot luot - app ve duoc man hinh ngay khi mo,
        # khong phai goi them REST nao.
        yield frame("status", service.snapshot)
        inventory_rev = app.state.inventory.revision
        yield frame("inventory", slots_payload(app))
        geometry_rev = app.state.geometry_store.revision
        yield frame("layout", geometry_payload(app))

        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT)
            except asyncio.TimeoutError:
                yield ": tick\n\n"
                continue

            yield frame("status", payload)

            # Doc bang chi khi that su co gi doi. So sanh hai so nguyen thoi.
            if app.state.inventory.revision != inventory_rev:
                inventory_rev = app.state.inventory.revision
                yield frame("inventory", slots_payload(app))

            if app.state.geometry_store.revision != geometry_rev:
                geometry_rev = app.state.geometry_store.revision
                yield frame("layout", geometry_payload(app))
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001 - dut mot duong khong duoc lam sap server
        log.exception("duong SSE gap loi")
    finally:
        service.unsubscribe(queue)


@router.get("/events", include_in_schema=False)
async def status_events(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _events(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # nginx dung truoc thi cam no gom goi
        },
    )
