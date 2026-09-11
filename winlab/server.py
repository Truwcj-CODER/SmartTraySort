# Dung app that de chay tren Windows, voi hai thay doi:
#
#   1. MySQL  -> SQLite  (khong can Docker, khong can cai MySQL)
#   2. Mount them /winlab  de mo cac trang tra cuu trong thu muc nay
#
# Tach rieng khoi run.py de uvicorn --reload cung dung duoc: tien trinh con
# import module nay la co du hai thay doi tren, khong phai chay lai run.py.
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent

# Doi lop Database TRUOC khi app.main chay dong "from .db import Database".
import app.db as app_db          # noqa: E402
import sqlite_db                 # noqa: E402

app_db.Database = sqlite_db.Database

from fastapi.staticfiles import StaticFiles   # noqa: E402
from app.main import app                      # noqa: E402

# Trang tra cuu nam trong winlab/, khong nhet vao app/static de khoi lan lon
# voi giao dien van hanh. Mount cung goc nen chung goi duoc /api/... binh thuong.
app.mount("/winlab", StaticFiles(directory=str(HERE), html=True), name="winlab")
