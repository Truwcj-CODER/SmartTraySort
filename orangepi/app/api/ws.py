from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..plc.service import PlcService

log = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/status")
async def status_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    service: PlcService = websocket.app.state.plc
    queue = service.subscribe()

    try:
        # gui ngay 1 ban de giao dien co du lieu luc vua mo
        await websocket.send_json(service.snapshot)
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - dong ket noi la du, khong lam sap server
        log.exception("websocket trang thai gap loi")
    finally:
        service.unsubscribe(queue)
