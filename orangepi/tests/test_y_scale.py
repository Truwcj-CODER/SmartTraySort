# Test cho viec quy doi truc Y: web va app nhap DO, PLC nhan XUNG.
#
# Axis_Y trong TIA duoc chinh lai theo xung, con toan bo phan tren server van
# noi bang do. PlcService la tang duy nhat biet chuyen do, nen test o day soi
# dung cai khung lenh ghi ra day - khong phai goi tri gian tiep nao.
#
# cd orangepi && python -m unittest discover -s tests -v
import asyncio
import sys
import unittest
from pathlib import Path
from unittest import mock
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.plc.protocol import (  # noqa: E402
    Command,
    Param,
    PlcStatus,
    Result,
    Y_SCALED_PARAMS,
    decode_f32,
    encode_f32,
)
from app.plc.service import PlcService  # noqa: E402

# 3200 xung mot vong, mot vong = 360 do  ->  8.888... xung mot do
SCALE = 3200 / 360.0


def _settings() -> Settings:
    return Settings(
        plc_host="127.0.0.1", plc_port=5020, plc_unit=1, plc_connect_timeout=1,
        net_setup=False, plc_local_ip="", plc_local_prefix=24, plc_iface="",
        plc_net_interval=5,
        poll_interval=0.001, command_timeout=1, homing_timeout=1,
        http_host="127.0.0.1", http_port=8000,
        mysql_host="127.0.0.1", mysql_port=3307, mysql_user="u",
        mysql_password="p", mysql_database="d", mysql_connect_timeout=1,
        mysql_ready_timeout=1,
    )


# Duong truyen gia: ghi nho khung lenh, roi bao ngay la PLC lam xong lenh do.
# Bao xong ngay tai cho de khoi phai chay vong poll thuc trong test.
class RecordingTransport:
    def __init__(self) -> None:
        self.frames: list[list[int]] = []
        self.service: PlcService | None = None
        self.reported_y = 0.0      # gia tri Y PLC bao ve, don vi XUNG

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def write_registers(self, addr: int, frame: list[int]) -> None:
        self.frames.append(list(frame))
        seq = frame[3] if len(frame) > 3 else 0
        hi, lo = encode_f32(self.reported_y)
        self.service._status = PlcStatus.from_registers(
            [0, 0, 0, seq, seq, int(Result.OK), 0, 0, hi, lo, 0, 0, 0, 0]
        )

    async def read_registers(self, addr: int, count: int) -> list[int]:
        hi, lo = encode_f32(self.reported_y)
        return [0, 0, 0, 0, 0, int(Result.OK), 0, 0, hi, lo, 0, 0, 0, 0]


def build(scale: float | None) -> tuple[PlcService, RecordingTransport]:
    service = PlcService(_settings())
    transport = RecordingTransport()
    transport.service = service
    service._transport = transport
    service.slot_count = 24
    if scale is not None:
        service.y_scale = scale
    return service, transport


# x nam o thanh ghi 4-5 cua khung, y o 6-7, z o 8-9.
def frame_x(frame: list[int]) -> float:
    return decode_f32(frame[4], frame[5])


def frame_y(frame: list[int]) -> float:
    return decode_f32(frame[6], frame[7])


class TestScaleWiring(unittest.TestCase):
    def test_default_is_degrees(self):
        # Khong mac day thi khong quy doi - dung y nhu server truoc day.
        service, _ = build(None)
        self.assertEqual(service.y_scale, 1.0)

    def test_rejects_zero_and_negative(self):
        service, _ = build(None)
        for bad in (0, -1, -8.889):
            with self.assertRaises(ValueError):
                service.y_scale = bad
        self.assertEqual(service.y_scale, 1.0)


class TestAngleGoesDownAsPulses(unittest.TestCase):
    def test_tilt_to_converts(self):
        service, transport = build(SCALE)
        asyncio.run(service.tilt_to(60.0))
        frame = transport.frames[-1]
        self.assertEqual(frame[0], int(Command.TILT_TO))
        self.assertAlmostEqual(frame_y(frame), 60.0 * SCALE, places=2)
        self.assertAlmostEqual(frame_y(frame), 533.33, places=1)

    def test_park_angle_converts(self):
        service, transport = build(SCALE)
        asyncio.run(service.set_park(5.0, 12.0, 200.0))
        frame = transport.frames[-1]
        self.assertEqual(frame[0], int(Command.SET_PARK))
        self.assertAlmostEqual(frame_y(frame), 12.0 * SCALE, places=2)

    def test_negative_angle_keeps_its_sign(self):
        # Lat sang trai la goc am. Quy doi khong duoc lam mat dau.
        service, transport = build(SCALE)
        asyncio.run(service.tilt_to(-60.0))
        self.assertAlmostEqual(frame_y(transport.frames[-1]), -60.0 * SCALE, places=2)


class TestParamScaling(unittest.TestCase):
    def test_angle_and_rate_params_convert(self):
        for param, value in ((Param.TILT_ANGLE, 60.0),
                             (Param.TILT_VEL, 30.0),
                             (Param.VEL_Y, 30.0),
                             (Param.SEEK_VEL_Y, 20.0),
                             (Param.ACC_Y, 400.0)):
            with self.subTest(param=param.name):
                service, transport = build(SCALE)
                asyncio.run(service.set_param(param, value))
                frame = transport.frames[-1]
                self.assertEqual(frame[1], int(param))
                self.assertAlmostEqual(frame_x(frame), value * SCALE, places=2)

    def test_mm_ms_and_count_params_pass_through(self):
        # Quy doi lot sang cac param nay la doi ca toc do ngang va thoi gian cho.
        for param, value in ((Param.VEL_X, 100.0),
                             (Param.VEL_Z, 100.0),
                             (Param.DWELL_MS, 1000.0),
                             (Param.TILT_HOLD_MS, 1000.0),
                             (Param.TILT_COUNT, 1.0),
                             (Param.SEEK_VEL_X, 50.0),
                             (Param.SEEK_VEL_Z, 50.0),
                             (Param.ACC_X, 500.0),
                             (Param.ACC_Z, 500.0)):
            with self.subTest(param=param.name):
                service, transport = build(SCALE)
                asyncio.run(service.set_param(param, value))
                self.assertAlmostEqual(frame_x(transport.frames[-1]), value, places=3)

    def test_scaled_set_covers_every_y_param(self):
        # Them param truc Y moi vao Param ma quen bo vao Y_SCALED_PARAMS thi
        # no se di xuong bang do trong khi PLC dem xung. Chot lai o day.
        by_name = {p for p in Param if p.name in ("VEL_Y", "TILT_ANGLE", "TILT_VEL",
                                                  "SEEK_VEL_Y", "ACC_Y")}
        self.assertEqual(set(Y_SCALED_PARAMS), by_name)


class TestSlotDirectionNotScaled(unittest.TestCase):
    def test_direction_sign_stays_one(self):
        # O y trong SET_SLOT cho dau chieu lat, khong phai goc. Nhan voi 8.889
        # la ca bang toa do sai.
        service, transport = build(SCALE)
        asyncio.run(service.set_slot(6, 433.33, 580.0, -1))
        frame = transport.frames[-1]
        self.assertEqual(frame[0], int(Command.SET_SLOT))
        self.assertAlmostEqual(frame_y(frame), -1.0, places=6)
        asyncio.run(service.set_slot(2, 433.33, 580.0, 1))
        self.assertAlmostEqual(frame_y(transport.frames[-1]), 1.0, places=6)


class TestStatusComesBackAsDegrees(unittest.TestCase):
    def test_pulses_read_back_as_degrees(self):
        service, transport = build(SCALE)
        transport.reported_y = 60.0 * SCALE          # PLC bao 533 xung
        status = asyncio.run(service.refresh())
        self.assertAlmostEqual(status.y, 60.0, places=2)

    def test_no_scale_no_conversion(self):
        service, transport = build(None)
        transport.reported_y = 60.0
        status = asyncio.run(service.refresh())
        self.assertAlmostEqual(status.y, 60.0, places=3)

    def test_x_and_z_untouched(self):
        # X va Z la mm o ca hai ben - quy doi khong duoc lan sang.
        service, transport = build(SCALE)

        async def run():
            regs = [0, 0, 0, 0, 0, int(Result.OK)]
            regs += list(encode_f32(433.33))
            regs += list(encode_f32(0.0))
            regs += list(encode_f32(580.0))
            regs += [6, 0]
            transport.read_registers = lambda addr, count: _ready(regs)
            return await service.refresh()

        async def _ready(value):
            return value

        status = asyncio.run(run())
        self.assertAlmostEqual(status.x, 433.33, places=2)
        self.assertAlmostEqual(status.z, 580.0, places=2)


class TestRoundTrip(unittest.TestCase):
    def test_down_then_up_returns_the_same_angle(self):
        service, _ = build(SCALE)
        for angle in (0.0, 1.0, 12.5, 60.0, 70.0, -60.0):
            with self.subTest(angle=angle):
                self.assertAlmostEqual(service._y_up(service._y_down(angle)),
                                       angle, places=6)


# Hieu chinh truc Y chi doi mot con so ti le, khong doi truong hinh hoc nao.
# send_layout so sanh voi lan day truoc de chi ghi phan da doi, nen day dung la
# cho de bo sot: PLC van giu goc lat cu TINH BANG XUNG, ma phep so sanh thi
# khong thay gi khac.
class TestCalibrationReachesThePlc(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        from app.geometry import Geometry

        self.calls: list[tuple] = []
        self.old = Geometry(park_y=10.0)
        self.new = Geometry(park_y=10.0, y_deg_per_rev=14.4)   # 25:1, sau hieu chinh

    def _app(self):
        outer = self

        class Service:
            y_scale = 1.0
            slot_count = 0

            async def set_park(self, *a):
                outer.calls.append(("set_park", a))

            async def push_table(self, rows):
                outer.calls.append(("push_table", len(rows)))

            async def set_slot_count(self, n):
                outer.calls.append(("set_slot_count", n))

            async def set_param(self, param, value):
                outer.calls.append(("set_param", param, value))

        class Store:
            def write(self, value):
                pass

        class Inventory:
            def set_active(self, n):
                pass

        return SimpleNamespace(state=SimpleNamespace(
            plc=Service(), geometry_pushed_store=Store(), inventory=Inventory()))

    async def test_new_y_scale_resends_every_angle(self):
        # Chi khi Axis_Y dem xung thi doi ti le moi doi cai gui xuong PLC.
        from app.api.routes import send_layout

        app = self._app()
        with mock.patch("app.geometry.Y_AXIS_COUNTS_PULSES", True):
            message = await send_layout(app, self.new, self.old)

        sent = {c[1] for c in self.calls if c[0] == "set_param"}
        self.assertEqual(sent & set(Y_SCALED_PARAMS), set(Y_SCALED_PARAMS) & {
            Param.VEL_Y, Param.TILT_ANGLE, Param.TILT_VEL})
        self.assertTrue(any(c[0] == "set_park" for c in self.calls))
        self.assertNotIn("PLC đã khớp", message)

    async def test_mm_params_stay_out_of_it(self):
        # Doi ti le truc Y khong duoc keo theo toc do ngang hay thoi gian cho.
        from app.api.routes import send_layout

        app = self._app()
        with mock.patch("app.geometry.Y_AXIS_COUNTS_PULSES", True):
            await send_layout(app, self.new, self.old)

        sent = {c[1] for c in self.calls if c[0] == "set_param"}
        self.assertNotIn(Param.VEL_X, sent)
        self.assertNotIn(Param.DWELL_MS, sent)

    async def test_scale_change_is_a_no_op_while_axis_counts_degrees(self):
        # Cong tac dang tat: Axis_Y hieu thang so do, nen doi ti le tren server
        # khong lam doi mot byte nao duoi PLC - khong duoc ghi lai gi ca.
        from app.api.routes import send_layout

        app = self._app()
        await send_layout(app, self.new, self.old)
        self.assertEqual(self.calls, [])
        self.assertEqual(app.state.plc.y_scale, 1.0)

    async def test_same_scale_still_sends_nothing(self):
        # Khong doi gi thi van phai im - vet hieu chinh khong duoc lam moi lan
        # luu deu ghi lai ca bang.
        from app.api.routes import send_layout

        app = self._app()
        await send_layout(app, self.old, self.old)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
