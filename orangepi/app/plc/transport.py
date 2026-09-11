from __future__ import annotations

import asyncio
import logging

from pymodbus.client import ModbusTcpClient

log = logging.getLogger(__name__)


class PlcConnectionError(RuntimeError):
    pass


class ModbusTransport:
    def __init__(self, host: str, port: int = 502, unit: int = 1, timeout: float = 3.0) -> None:
        self._host = host
        self._port = port
        self._unit = unit
        self._timeout = timeout
        self._client: ModbusTcpClient | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------- vong doi
    @property
    def endpoint(self) -> str:
        return f"{self._host}:{self._port}"

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.connected

    async def connect(self) -> None:
        async with self._lock:
            await self._connect_locked()

    async def close(self) -> None:
        async with self._lock:
            if self._client is not None:
                await asyncio.to_thread(self._client.close)
                self._client = None
                log.info("da dong ket noi toi PLC %s", self.endpoint)

    async def _connect_locked(self) -> None:
        if self.connected:
            return
        if self._client is None:
            self._client = ModbusTcpClient(self._host, port=self._port, timeout=self._timeout)
        ok = await asyncio.to_thread(self._client.connect)
        if not ok:
            raise PlcConnectionError(f"khong ket noi duoc toi PLC {self.endpoint}")
        log.info("da ket noi toi PLC %s", self.endpoint)

    # --------------------------------------------------------- doc / ghi
    async def read_registers(self, address: int, count: int) -> list[int]:
        rr = await self._transact(lambda c: self._read(c, address, count))
        return list(rr.registers)

    async def write_registers(self, address: int, values: list[int]) -> None:
        await self._transact(lambda c: self._write(c, address, values))

    # ------------------------------------------------------------- noi bo
    async def _transact(self, call):
        async with self._lock:
            await self._connect_locked()
            assert self._client is not None
            try:
                response = await asyncio.to_thread(call, self._client)
            except Exception as exc:  # loi socket, timeout...
                await asyncio.to_thread(self._client.close)
                self._client = None
                raise PlcConnectionError(f"giao dich Modbus that bai: {exc}") from exc
            if response.isError():
                raise PlcConnectionError(f"PLC tra ve loi: {response}")
            return response

    # pymodbus doi ten slave -> device_id o ban 3.9, boc o day cho phan con lai khoi biet
    def _read(self, client: ModbusTcpClient, address: int, count: int):
        try:
            return client.read_holding_registers(address, count=count, slave=self._unit)
        except TypeError:
            return client.read_holding_registers(address, count=count, device_id=self._unit)

    def _write(self, client: ModbusTcpClient, address: int, values: list[int]):
        try:
            return client.write_registers(address, values, slave=self._unit)
        except TypeError:
            return client.write_registers(address, values, device_id=self._unit)
