#!/usr/bin/env python3
# Chay server tren Windows de debug voi PLC that.
#
#   python winlab/run.py                 # cong 8000, PLC lay tu orangepi/.env
#   python winlab/run.py --port 8080
#   python winlab/run.py --plc 192.168.0.10 --reload
#
# Khac ban chay that o dung MOT diem: thay MySQL bang SQLite. Ngoai ra dung
# nguyen code trong orangepi/app, khong sao chep, khong sua. Ban tren Ubuntu
# van chay MySQL qua docker compose nhu cu.
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
APP_DIR = ROOT / "orangepi"


def parse(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Server ban Windows, dung SQLite thay MySQL")
    p.add_argument("--port", type=int, help="cong web, mac dinh lay tu .env hoac 8000")
    p.add_argument("--plc", help="dia chi PLC, ghi de PLC_HOST trong .env")
    p.add_argument("--reload", action="store_true", help="tu nap lai khi sua code")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse(argv)

    if not (APP_DIR / "app" / "main.py").exists():
        print(f"khong thay {APP_DIR / 'app'} - chay file nay tu trong repo", file=sys.stderr)
        return 1

    # Tro vao code that. Them ca thu muc nay de import duoc sqlite_db.
    sys.path.insert(0, str(APP_DIR))
    sys.path.insert(0, str(HERE))

    # _load_dotenv ben app.config dung setdefault, nen bien dat o day thang the.
    if args.plc:
        os.environ["PLC_HOST"] = args.plc
    if args.port:
        os.environ["HTTP_PORT"] = str(args.port)
    os.environ.setdefault("HTTP_HOST", "127.0.0.1")
    # May Windows khong tu gan IP cho card mang - viec do de nguoi dung lo.
    os.environ.setdefault("NET_SETUP", "0")

    # server.py lo phan doi MySQL -> SQLite va mount them /winlab.
    import sqlite_db

    from app.config import get_settings

    settings = get_settings()
    print(f"  code       : {APP_DIR / 'app'}")
    print(f"  du lieu    : {sqlite_db.DATA_DIR}  (SQLite, khong can MySQL)")
    print(f"  PLC        : {settings.plc_host}:{settings.plc_port}")
    print(f"  dashboard  : http://127.0.0.1:{settings.http_port}")
    print(f"  cam bien   : http://127.0.0.1:{settings.http_port}/winlab/cambien.html")
    print()

    import uvicorn

    uvicorn.run(
        "server:app",
        host=settings.http_host,
        port=settings.http_port,
        reload=args.reload,
        reload_dirs=[str(APP_DIR / "app"), str(HERE)] if args.reload else None,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
