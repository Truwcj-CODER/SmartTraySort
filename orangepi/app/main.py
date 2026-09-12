from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api import appdist, routes, sse, ws
from .api.routes import send_layout
from .config import get_settings
from .db import ConfigStore, Database, PendingTable, SkuTable, SlotTable, migrate_json
from .geometry import Geometry
from .inventory import DEFAULT_CAPACITY, SLOT_COUNT, Inventory
from .plc import netsetup
from .plc.service import PlcService

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)


# Healthcheck cua docker go cua moi 30 giay, va uvicorn ghi access log cho MOI
# request - nen log day dac "GET /healthz 200 OK", chuyen that bi chon o giua.
# Chan rieng duong nay, moi duong khac van ghi binh thuong.
class _BoLocHealthz(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/healthz" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_BoLocHealthz())

# pymodbus ghi "Repeating...." moi lan thu lai - dong nay khong noi duoc gi ma
# lam ngap log. Ha muc khong duoc vi pymodbus ghi no o muc ERROR, nen phai loc
# theo NOI DUNG. Loi that ("Connection refused", "timed out") van giu.
class _BoLocPymodbus(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "Repeating" not in record.getMessage()


logging.getLogger("pymodbus.logging").addFilter(_BoLocPymodbus())
logging.getLogger("pymodbus.logging").setLevel(logging.WARNING)

log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # mot ket noi Modbus va mot vong lap doc trang thai dung chung cho ca ung dung
    settings = get_settings()
    service = PlcService(settings)

    log.info("starting up, PLC at %s:%s", settings.plc_host, settings.plc_port)

    db = Database(settings)
    db.wait_ready(settings.mysql_ready_timeout)
    db.setup()
    migrate_json(db, BASE_DIR / "data")

    # Dat dia chi cung dai voi PLC truoc khi noi, roi canh tiep phong khi rut cam.
    await netsetup.apply(settings)
    net_task = asyncio.create_task(netsetup.keep_route(settings), name="plc-netsetup")

    await service.start()
    app.state.plc = service
    app.state.settings = settings
    app.state.db = db
    app.state.geometry_store = ConfigStore(db, "geometry", Geometry().to_dict())
    # Baseline so send_layout writes only the changed rows, not the whole table each save.
    app.state.geometry_pushed_store = ConfigStore(db, "geometry_pushed", {})
    app.state.inventory = Inventory(
        SlotTable(db, SLOT_COUNT, DEFAULT_CAPACITY),
        SkuTable(db),
        PendingTable(db),
    )

    # Bo cuc gian ro do cau hinh quyet dinh, nen ton kho phai biet ngay tu dau
    # la co bao nhieu ro that su dang dung.
    startup_geometry = Geometry.from_dict(app.state.geometry_store.read())
    layout_slots = startup_geometry.slot_count
    app.state.inventory.set_active(layout_slots)
    service.slot_count = layout_slots
    service.y_scale = startup_geometry.y_scale_for_plc()

    # PLC moi la noi giu bang toa do: DB_TrayTable co Retain nen mat dien bat
    # lai van con nguyen, khong can server. Rieng mot truong hop Retain khong do
    # duoc la vua nap lai khoi trong TIA - luc do DB tro ve gia tri khoi tao (bo
    # cuc 20 ro mac dinh) trong khi web dang cau hinh khac. Nen cu noi duoc toi
    # PLC la day lai mot lan cho chac. Chay xong roi thi khong day nua.
    async def resync_plc() -> None:
        geometry = Geometry.from_dict(app.state.geometry_store.read())
        problems = geometry.problems()
        if problems:
            log.warning("config invalid, not pushing to PLC: %s", "; ".join(problems[:3]))
            return
        log.info("PLC came online, re-pushing the coordinate table")
        log.info("%s", await send_layout(app, geometry))

    service.on_online(resync_plc)

    try:
        yield
    finally:
        log.info("shutting down, closing PLC connection")
        net_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await net_task
        await service.stop()
        db.close()


app = FastAPI(
    title="Dieu khien khay X-Y",
    description="Server tren Orange Pi, dieu khien PLC S7-1200 qua Modbus TCP",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(routes.router)
app.include_router(sse.router)
app.include_router(appdist.router)
app.include_router(ws.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"settings": request.app.state.settings},
    )


@app.get("/healthz", include_in_schema=False)
async def healthz(request: Request) -> dict:
    service: PlcService = request.app.state.plc
    return {"server": "ok", "plc_online": service.snapshot["online"]}
