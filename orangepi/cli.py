#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.config import get_settings
from app.geometry import Geometry
from app.plc.service import PlcBusyError, PlcCommandError, PlcService
from app.plc.transport import PlcConnectionError
from app.db import ConfigStore, Database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dieu khien khay X-Y qua Modbus TCP")
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("status", help="xem trang thai may")
    sub.add_parser("home", help="chay lay goc toa do")
    sub.add_parser("park", help="ve vi tri cho")
    sub.add_parser("stop", help="dung khan")
    sub.add_parser("reset", help="xoa loi")

    for name, helptext in [
        ("run", "chu trinh day du: toi khay -> lac -> ve cho"),
        ("goto", "chi di toi khay"),
        ("shake", "chi lac tai khay"),
        ("teach", "luu vi tri hien tai vao khay"),
    ]:
        p = sub.add_parser(name, help=helptext)
        p.add_argument("slot", type=int, help="so khay 1..20")

    p_xy = sub.add_parser("xy", help="di toi toa do tu do")
    p_xy.add_argument("x", type=float)
    p_xy.add_argument("y", type=float)

    return parser


async def dispatch(service: PlcService, args: argparse.Namespace):
    actions = {
        "status": lambda: None,
        "home": service.home,
        "park": service.park,
        "stop": service.emergency_stop,
        "reset": service.reset_fault,
        "run": lambda: service.run_slot(args.slot),
        "goto": lambda: service.goto_slot(args.slot),
        "shake": lambda: service.shake_slot(args.slot),
        "teach": lambda: service.teach_slot(args.slot),
        "xy": lambda: service.move_xy(args.x, args.y),
    }

    if args.action == "status":
        # doi mot nhip poll de co so lieu tuoi
        await asyncio.sleep(service.settings.poll_interval * 2)
        return service.snapshot

    result = await actions[args.action]()
    return result.to_dict() if hasattr(result, "to_dict") else {"sent": True}


async def main() -> int:
    args = build_parser().parse_args()
    settings = get_settings()
    service = PlcService(settings)
    # so ro do hinh hoc quyet dinh, giong het main.py
    db = Database(settings)
    db.wait_ready(settings.mysql_ready_timeout)
    geometry = Geometry.from_dict(
        ConfigStore(db, "geometry", Geometry().to_dict()).read()
    )
    service.slot_count = geometry.slot_count
    # Cung ti le truc Y nhu server, khong thi cli.py lat mot goc khac han.
    service.y_scale = geometry.y_scale_for_plc()
    await service.start()

    try:
        payload = await dispatch(service, args)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    except (PlcCommandError, PlcBusyError, PlcConnectionError, ValueError) as exc:
        print(f"LOI: {exc}", file=sys.stderr)
        return 1
    finally:
        await service.stop()
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
