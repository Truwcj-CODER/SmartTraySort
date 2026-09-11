# Gan dia chi phu tren dai cua PLC cho card mang co day dang co tin hieu.
#
# PLC o IP co dinh nhung may chu thi khong: cam qua USB hub, qua cong LAN cua
# Pi, hay may khac deu ra ten card khac nhau va thuong chi co IP cua DHCP van
# phong. Khong co dia chi nao cung dai voi PLC thi goi tin khong bao gio roi
# vao day cap do.
from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
import os
import shutil
import subprocess

from ..config import Settings

log = logging.getLogger(__name__)

SKIP = ("lo", "wl", "docker", "br-", "veth", "virbr", "tun", "tap", "tailscale", "wg")


class NetSetupError(RuntimeError):
    pass


def _ip_binary() -> str:
    found = shutil.which("ip")
    if found:
        return found
    for path in ("/usr/sbin/ip", "/usr/bin/ip", "/sbin/ip", "/bin/ip"):
        if os.access(path, os.X_OK):
            return path
    raise NetSetupError("khong tim thay lenh `ip`, cai goi iproute2")


def _ip(*args: str) -> str:
    try:
        done = subprocess.run((_ip_binary(), *args), capture_output=True, text=True, check=True)
    except FileNotFoundError as exc:
        raise NetSetupError("khong chay duoc lenh `ip`") from exc
    except subprocess.CalledProcessError as exc:
        raise NetSetupError((exc.stderr or "").strip() or f"`ip {' '.join(args)}` that bai") from exc
    return done.stdout


def links() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in _ip("-o", "link", "show").splitlines():
        _, _, rest = line.partition(":")
        name, _, flags = rest.partition(":")
        if not name.strip() or "<" not in flags:
            continue
        out.append((name.strip().split("@")[0], flags.split("<", 1)[1].split(">", 1)[0]))
    return out


def wired(pin: str) -> list[str]:
    if pin:
        return [n for n, _ in links() if n == pin]
    return sorted(n for n, f in links() if not n.startswith(SKIP) and "LOWER_UP" in f)


def addresses(iface: str) -> list[str]:
    cols = _ip("-4", "-o", "addr", "show", "dev", iface).split()
    return [cols[i + 1] for i, c in enumerate(cols) if c == "inet"]


def already_reachable(network: ipaddress.IPv4Network) -> str | None:
    for name, _ in links():
        for cidr in addresses(name):
            if ipaddress.ip_interface(cidr).ip in network:
                return name
    return None


def pick_local(settings: Settings) -> tuple[ipaddress.IPv4Network, str]:
    prefix = settings.plc_local_prefix
    network = ipaddress.ip_network(f"{settings.plc_host}/{prefix}", strict=False)
    if settings.plc_local_ip:
        return network, settings.plc_local_ip
    plc = ipaddress.ip_address(settings.plc_host)
    for suffix in (100, 101, 200, 201):
        candidate = network.network_address + suffix
        if candidate != plc and candidate in network:
            return network, f"{candidate}/{prefix}"
    raise NetSetupError(f"khong chon duoc dia chi trong {network}")


def ensure(network: ipaddress.IPv4Network, local_cidr: str, pin: str) -> str | None:
    have = already_reachable(network)
    if have:
        return have

    for iface in wired(pin):
        try:
            _ip("addr", "add", local_cidr, "dev", iface)
        except NetSetupError as exc:
            if "File exists" in str(exc):
                return iface
            log.warning("khong gan duoc %s cho %s: %s", local_cidr, iface, exc)
            continue
        with contextlib.suppress(NetSetupError):
            _ip("link", "set", iface, "up")
        log.info("da gan %s cho %s", local_cidr, iface)
        return iface
    return None


# Dam bao co mot card mang dung dai voi PLC. Tra ve ten card, hoac None.
async def apply(settings: Settings) -> str | None:
    if not settings.net_setup:
        return None
    try:
        network, local_cidr = pick_local(settings)
        return await asyncio.to_thread(ensure, network, local_cidr, settings.plc_iface)
    except (NetSetupError, ValueError) as exc:
        log.warning("khong tu dat duoc dia chi: %s", exc)
        return None


# Rut cam hay doi adapter deu tu nhan lai, nen phai chay deu dan.
async def keep_route(settings: Settings) -> None:
    last: str | None = None
    while True:
        iface = await apply(settings)
        if iface != last:
            log.info("duong toi PLC: %s", iface or "chua co card nao co tin hieu")
            last = iface
        await asyncio.sleep(settings.plc_net_interval)
