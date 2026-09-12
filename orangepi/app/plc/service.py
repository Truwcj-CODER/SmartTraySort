from __future__ import annotations

import asyncio
import contextlib
import logging

from dataclasses import replace

from collections.abc import Awaitable, Callable

from ..config import Settings
from .protocol import (
    ADDR_CTRL,
    ADDR_STATUS_BLOCK,
    ADDR_WRITE_BLOCK,
    SIZE_STATUS_BLOCK,
    Command,
    CtrlBit,
    Param,
    PlcStatus,
    RESULT_OK,
    Result,
    Y_SCALED_PARAMS,
    build_command_frame,
    build_ctrl_frame,
    next_seq,
)
from .transport import ModbusTransport, PlcConnectionError

log = logging.getLogger(__name__)


class PlcCommandError(RuntimeError):
    def __init__(self, message: str, status: PlcStatus | None = None) -> None:
        super().__init__(message)
        # So ro da ghi xong khi loi xay ra giua chung mot lan day bang.
        self.written = 0
        self.status = status


class PlcBusyError(RuntimeError):
    pass


# Cau nay hien thang len tablet, nguoi van hanh doc - phai noi ro kiem cho nao.
def _failure_text(command: Command, status: PlcStatus) -> str:
    # REJECTED voi READY = 0 khong phai loi cua lenh: may dang khong o trang
    # thai cho phep chay. Bit READY do chuong trinh PLC dat tu tin hieu phan
    # cung, nen chi sua duoc o tu dien chu khong sua duoc tu server.
    if status.result == Result.REJECTED and not status.ready:
        return (
            f"Lệnh {command.name} bị từ chối: máy chưa sẵn sàng — bit READY "
            "trong HR10 đang bằng 0. Kiểm tra nút dừng khẩn, nguồn servo và "
            "contactor lực."
        )

    head = f"Lệnh {command.name} thất bại: {status.result_text}"
    if status.step or status.error_id:
        head += f" (bước {status.step}, ErrorID 0x{status.error_id:04X})"
    return head


class PlcService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._transport = ModbusTransport(
            host=settings.plc_host,
            port=settings.plc_port,
            unit=settings.plc_unit,
            timeout=settings.plc_connect_timeout,
        )
        self._seq = 0
        self._status: PlcStatus | None = None
        self._online = False
        self._last_error: str | None = None
        self._ctrl = CtrlBit.AXES_ENABLE
        # So ro cua bo cuc hien tai. Khong co dinh - cau hinh doi la doi theo.
        self._slot_count = 0        # main.py/cli.py gan lai tu hinh hoc
        # Pulses the PLC counts per degree of tilt. Axis_Y in TIA is scaled in
        # pulses, so every angle and angular rate is converted on the way down
        # and back on the way up: the API, the web and the app all speak degrees
        # and never see a pulse. 1.0 = an Axis_Y still scaled in degrees, which
        # is what this server sent before the axis was rescaled - so nothing
        # changes until main.py / send_layout wires the real scale in.
        self._y_scale = 1.0        # main.py/routes.send_layout gan lai tu hinh hoc
        self._command_lock = asyncio.Lock()
        self._poller: asyncio.Task | None = None
        self._subscribers: set[asyncio.Queue] = set()
        # Goi lai moi khi duong truyen vua song tro lai. Bang toa do trong PLC co
        # Retain nen thuong da dung san; lan day nay la de bat truong hop DB vua
        # bi dua ve gia tri khoi tao sau khi nap lai khoi trong TIA.
        self._on_online: "Callable[[], Awaitable[None]] | None" = None
        self._synced = False
        self._sync_task: asyncio.Task | None = None
        self._sync_retry_at = 0.0     # day that bai thi cho het khoang nay moi thu lai

    # ------------------------------------------------------------- vong doi
    async def start(self) -> None:
        # khong ket noi duoc thi van cho server len, vong lap poll se tu thu lai
        try:
            await self._transport.connect()
            self._online = True
        except PlcConnectionError as exc:
            self._online = False
            self._last_error = str(exc)
            log.warning("could not connect to PLC at startup: %s", exc)

        self._poller = asyncio.create_task(self._poll_loop(), name="plc-poller")

    def on_online(self, callback: "Callable[[], Awaitable[None]]") -> None:
        self._on_online = callback

    async def stop(self) -> None:
        if self._sync_task is not None:
            self._sync_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._sync_task
            self._sync_task = None
        if self._poller is not None:
            self._poller.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._poller
            self._poller = None
        await self._transport.close()
        self._online = False

    # ---------------------------------------------------------- trang thai
    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def snapshot(self) -> dict:
        return {
            "online": self._online,
            "endpoint": self._transport.endpoint,
            "last_error": self._last_error,
            "slot_count": self._slot_count,
            "status": self._status.to_dict() if self._status else None,
        }

    async def refresh(self) -> PlcStatus:
        regs = await self._transport.read_registers(ADDR_STATUS_BLOCK, SIZE_STATUS_BLOCK)
        status = PlcStatus.from_registers(regs)
        # Axis_Y reports where it is in pulses; nothing above this line wants
        # to know that. x and z stay put - they are mm on both sides.
        if self._y_scale != 1.0:
            status = replace(status, y=round(self._y_up(status.y), 3))
        self._status = status
        return self._status

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    # ----------------------------------------------------------------- lenh

    # Gui lenh va cho PLC bao xong. Duong di duy nhat cho lenh co thoi gian chay.
    async def execute(
        self,
        command: Command,
        *,
        slot: int = 0,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        timeout: float | None = None,
    ) -> PlcStatus:
        if self._command_lock.locked():
            raise PlcBusyError("dang co lenh khac chay do, cho lenh hien tai xong da")

        async with self._command_lock:
            seq = await self._send(command, slot=slot, x=x, y=y, z=z)
            status = await self._wait_done(seq, timeout or self._timeout_for(command))

        # Cham vach gioi han khong phai loi: truc dung lai la dung viec no phai
        # lam. Bao that bai o day thi nhat ky day chu do trong khi may chay dung.
        if status.result not in RESULT_OK:
            raise PlcCommandError(_failure_text(command, status), status)
        return status

    async def dispatch(self, command: Command, *, slot: int = 0) -> int:
        # khong qua khoa lenh: dung khan phai gui duoc ca khi dang chay chu trinh
        return await self._send(command, slot=slot)

    async def set_jog(self, bits: CtrlBit) -> None:
        # PLC tu cat jog sau JogMaxTime neu mat ket noi luc dang giu nut
        self._ctrl = CtrlBit.AXES_ENABLE | (bits & ~CtrlBit.AXES_ENABLE)
        await self._transport.write_registers(ADDR_CTRL, build_ctrl_frame(self._ctrl))

    async def stop_jog(self) -> None:
        await self.set_jog(CtrlBit.NONE)

    # -------------------------------------------------------- ham tien dung
    async def home(self) -> PlcStatus:
        return await self.execute(Command.HOME)

    async def run_slot(self, slot: int) -> PlcStatus:
        return await self.execute(Command.AUTO, slot=self._validated_slot(slot))

    async def goto_slot(self, slot: int) -> PlcStatus:
        return await self.execute(Command.GOTO, slot=self._validated_slot(slot))

    # Lat tai cho theo chieu cua khay, khong di chuyen.
    async def tilt_slot(self, slot: int) -> PlcStatus:
        return await self.execute(Command.TILT, slot=self._validated_slot(slot))

    async def teach_slot(self, slot: int) -> PlcStatus:
        return await self.execute(Command.TEACH, slot=self._validated_slot(slot), timeout=10.0)

    # Di toi vi tri tu do: x = ngang (mm), z = do cao (mm).
    async def move_to(self, x: float, z: float) -> PlcStatus:
        return await self.execute(Command.MOVE_XZ, x=x, z=z)

    # Lat truc Y toi mot goc cu the. Dung khi can chinh co cau.
    async def tilt_to(self, angle: float) -> PlcStatus:
        return await self.execute(Command.TILT_TO, y=self._y_down(angle))

    # Ghi toa do 1 khay xuong bang trong PLC.
    #
    # Dau cua tham so y quyet dinh chieu lat, nen gui truc tiep direction vao do.
    #
    # KHONG quy doi y o day. O nay cho +1/-1 - mot dau chieu, khong phai mot goc.
    # Nhan no voi so xung moi do la PLC nhan duoc 8.9 thay vi 1, va bang toa do
    # sai chieu lat het ca gian.
    async def set_slot(self, slot: int, x: float, z: float, direction: int) -> PlcStatus:
        return await self.execute(
            Command.SET_SLOT,
            slot=self._validated_slot(slot),
            x=x, z=z, y=float(direction),
            timeout=10.0,
        )

    # Ghi mot tham so chay may xuong PLC (toc do, thoi gian dung, goc lat).
    async def set_param(self, param: Param, value: float) -> PlcStatus:
        if param in Y_SCALED_PARAMS:
            value = self._y_down(value)
        return await self.execute(Command.SET_PARAM, slot=int(param), x=value, timeout=10.0)

    # Bao so ro cua bo cuc hien tai. PLC tu chan moi so ro ngoai khoang do.
    async def set_slot_count(self, count: int) -> PlcStatus:
        status = await self.execute(Command.SET_COUNT, slot=count, timeout=10.0)
        self.slot_count = count
        return status

    # Ghi vi tri cho xuong PLC. Khong phai goc toa do - xem ghi chu trong SCL.
    # y = goc lat tai vi tri cho, do - quy doi nhu moi goc khac.
    async def set_park(self, x: float, y: float, z: float) -> PlcStatus:
        return await self.execute(
            Command.SET_PARK, x=x, y=self._y_down(y), z=z, timeout=10.0)

    # Day ca bang toa do xuong PLC. Tra ve so ro da ghi.
    #
    # Goi tuan tu qua set_slot de moi ro deu duoc PLC xac nhan rieng - khong
    # co chuyen ghi mot nua roi im lang. Dung giua chung thi bao ro dung o dau,
    # vi luc do PLC dang giu bang NUA MOI NUA CU, nguy hiem hon la khong ghi gi.
    async def push_table(self, rows: list[dict]) -> int:
        try:
            return await self._write_rows(rows)
        except PlcCommandError as exc:
            raise PlcCommandError(
                f"{exc} — mới ghi được {exc.written}/{len(rows)} rổ, "
                f"PLC đang giữ bảng nửa mới nửa cũ",
                exc.status,
            ) from exc

    async def _write_rows(self, rows: list[dict]) -> int:
        for index, row in enumerate(rows):
            try:
                await self.set_slot(int(row["slot"]), float(row["x"]),
                                    float(row["z"]), int(row["dir"]))
            except PlcCommandError as exc:
                exc.written = index          # so ro da ghi xong truoc khi dung
                raise
        return len(rows)

    async def park(self) -> PlcStatus:
        return await self.execute(Command.PARK)

    async def emergency_stop(self) -> int:
        return await self.dispatch(Command.STOP)

    async def reset_fault(self) -> int:
        return await self.dispatch(Command.RESET)

    # --------------------------------------------------------------- noi bo
    @property
    def slot_count(self) -> int:
        return self._slot_count

    @slot_count.setter
    def slot_count(self, count: int) -> None:
        self._slot_count = max(0, int(count))

    @property
    def y_scale(self) -> float:
        return self._y_scale

    @y_scale.setter
    def y_scale(self, pulses_per_degree: float) -> None:
        scale = float(pulses_per_degree)
        if scale <= 0:
            raise ValueError("so xung moi do phai lon hon 0")
        self._y_scale = scale

    # do -> xung, chieu ghi xuong PLC
    def _y_down(self, degrees: float) -> float:
        return float(degrees) * self._y_scale

    # xung -> do, chieu doc trang thai len
    def _y_up(self, pulses: float) -> float:
        return float(pulses) / self._y_scale

    def _validated_slot(self, slot: int) -> int:
        if not 1 <= slot <= self._slot_count:
            raise ValueError(f"so khay phai trong khoang 1..{self._slot_count}")
        return slot

    def _timeout_for(self, command: Command) -> float:
        if command is Command.HOME:
            return self._settings.homing_timeout
        return self._settings.command_timeout

    async def _send(self, command: Command, *, slot: int = 0,
                    x: float = 0.0, y: float = 0.0, z: float = 0.0) -> int:
        self._seq = next_seq(self._seq)
        frame = build_command_frame(command, self._seq, slot=slot, x=x, y=y, z=z, ctrl=self._ctrl)
        await self._transport.write_registers(ADDR_WRITE_BLOCK, frame)
        log.info("sent command %s seq=%s slot=%s", command.name, self._seq, slot)
        return self._seq

    async def _wait_done(self, seq: int, timeout: float) -> PlcStatus:
        # doc tu bo nho dem cua vong lap poll, khong ban them yeu cau nao xuong PLC
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        acked = False

        while loop.time() < deadline:
            status = self._status
            if status is not None:
                if status.ack_seq == seq:
                    acked = True
                if acked and status.done_seq == seq:
                    return status
            await asyncio.sleep(self._settings.poll_interval)

        raise PlcCommandError(
            f"qua {timeout:.0f}s ma PLC chua bao xong lenh seq={seq} "
            f"({'da nhan lenh' if acked else 'PLC chua he nhan duoc lenh'})",
            self._status,
        )

    async def _poll_loop(self) -> None:
        interval = self._settings.poll_interval
        while True:
            try:
                await self.refresh()
                if not self._online:
                    log.info("reconnected to PLC")
                self._online = True
                self._last_error = None
                if not self._synced:
                    self._start_sync()
            except (PlcConnectionError, ValueError) as exc:
                if self._online:
                    log.warning("lost connection to PLC: %s", exc)
                self._online = False
                self._last_error = str(exc)
                # Lan noi lai sau phai day bang mot lan nua: PLC co the vua
                # mat dien va quen sach bang toa do.
                self._synced = False
            except asyncio.CancelledError:
                raise

            self._broadcast()
            await asyncio.sleep(interval)

    def _start_sync(self) -> None:
        # Chay rieng mot task. KHONG duoc await ngay trong vong poll: lenh day
        # bang cho DoneSeq ma DoneSeq lai do chinh vong poll cap nhat - await o
        # day la tu khoa chan minh.
        if self._on_online is None:
            self._synced = True
            return
        if self._sync_task is not None and not self._sync_task.done():
            return
        # Day hong (PLC dang STOP chang han) thi khong duoc thu lai moi vong poll,
        # nhu the la nen PLC moi 200 ms mot lan. Cach nhau it nhat 10 giay.
        if asyncio.get_running_loop().time() < self._sync_retry_at:
            return
        self._synced = True
        self._sync_task = asyncio.create_task(self._run_sync(), name="plc-resync")

    async def _run_sync(self) -> None:
        try:
            await self._on_online()
        except asyncio.CancelledError:
            raise
        except Exception as exc:                      # noqa: BLE001
            # That bai thi danh dau lai de vong poll sau thu tiep.
            self._synced = False
            self._sync_retry_at = asyncio.get_running_loop().time() + 10.0
            log.warning("re-pushing the coordinate table after PLC reconnect failed: %s", exc)

    def _broadcast(self) -> None:
        # hang doi giu 1 phan tu: nguoi nhan cham thi bo ban cu, luon lay ban moi nhat
        payload = self.snapshot
        for queue in list(self._subscribers):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(payload)
