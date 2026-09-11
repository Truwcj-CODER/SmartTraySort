# Ban thay the MySQL bang SQLite, CHI dung khi debug tren Windows.
#
# Giu dung giao dien cua app.db.Database - tang tren (ConfigStore, SlotTable,
# migrate_json) khong biet la co gi doi, nen khong phai sua mot dong nao trong
# app/. Muon quay ve MySQL that thi bo file nay ra, khong con dau vet.
#
# SQLite khong hieu vai cau lenh rieng cua MySQL, nen co mot lop dich o duoi.
from __future__ import annotations

import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path

from app.config import Settings
from app.db import DatabaseError

DATA_DIR = Path(__file__).resolve().parent / "data"

# Khai lai bang theo phuong ngu SQLite thay vi dich SCHEMA cua MySQL: ben kia co
# ENGINE=InnoDB, JSON, ON UPDATE CURRENT_TIMESTAMP... dich sang deu gay, ma cot
# thi chi can dung ten va dung kieu la tang tren chay duoc.
#
# UNIQUE tren code van cho nhieu ro cung NULL - SQLite khong coi hai NULL la
# trung nhau, giong het MySQL.
SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS config (
      name       TEXT PRIMARY KEY,
      data       TEXT NOT NULL,
      updated_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS slots (
      slot       INTEGER PRIMARY KEY,
      code       TEXT,
      count      INTEGER NOT NULL DEFAULT 0,
      capacity   INTEGER NOT NULL DEFAULT 10,
      updated_at TEXT
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_slots_code ON slots (code)",
)

_VALUES_CALL = re.compile(r"VALUES\s*\(\s*(\w+)\s*\)", re.IGNORECASE)
_ON_DUP = re.compile(r"ON\s+DUPLICATE\s+KEY\s+UPDATE", re.IGNORECASE)


# Doi mot cau lenh MySQL thanh cau tuong duong cua SQLite.
#
# Chi ba khac biet ma tang tren dung toi:
#   INSERT IGNORE INTO       -> INSERT OR IGNORE INTO
#   ON DUPLICATE KEY UPDATE  -> ON CONFLICT DO UPDATE SET, VALUES(x) -> excluded.x
#   tham so %s               -> ?
def translate(sql: str, conflict_key: str = "") -> str:
    sql = re.sub(r"INSERT\s+IGNORE\s+INTO", "INSERT OR IGNORE INTO", sql, flags=re.IGNORECASE)

    if _ON_DUP.search(sql):
        key = conflict_key or _guess_key(sql)
        sql = _ON_DUP.sub(f"ON CONFLICT({key}) DO UPDATE SET", sql)
        sql = _VALUES_CALL.sub(lambda m: f"excluded.{m.group(1)}", sql)

    return sql.replace("%s", "?")


# Cot dau tien trong danh sach INSERT chinh la khoa gay xung dot o cac cau
# lenh dang dung. Doan sai thi SQLite bao loi ngay, khong am tham chay tiep.
def _guess_key(sql: str) -> str:
    m = re.search(r"INSERT\s+INTO\s+\w+\s*\(\s*(\w+)", sql, re.IGNORECASE)
    if not m:
        raise DatabaseError(f"khong doan duoc khoa xung dot cho cau lenh: {sql[:60]}")
    return m.group(1)


def _clean(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat(timespec="seconds") if isinstance(value, datetime) else value.isoformat()
    return value


# Boc con tro SQLite cho giong con tro DictCursor cua pymysql: dich cau lenh,
# doi tham so, va tra ve dict thay vi tuple.
class Cursor:
    def __init__(self, raw: sqlite3.Cursor) -> None:
        self._raw = raw

    def execute(self, sql: str, params=()):
        return self._raw.execute(translate(sql), tuple(_clean(p) for p in params))

    def executemany(self, sql: str, seq):
        rows = [tuple(_clean(p) for p in row) for row in seq]
        return self._raw.executemany(translate(sql), rows)

    def fetchone(self):
        row = self._raw.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        return [dict(r) for r in self._raw.fetchall()]

    def __getattr__(self, name):
        return getattr(self._raw, name)


class Database:
    def __init__(self, settings: Settings) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._path = DATA_DIR / f"{settings.mysql_database}.db"
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    @property
    def endpoint(self) -> str:
        return f"sqlite {self._path}"

    def _link(self) -> sqlite3.Connection:
        if self._conn is None:
            conn = sqlite3.connect(self._path, check_same_thread=False, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._conn = conn
        return self._conn

    @contextmanager
    def cursor(self, write: bool = False):
        with self._lock:
            conn = self._link()
            raw = conn.cursor()
            try:
                yield Cursor(raw)
                if write:
                    conn.commit()
            except Exception as exc:
                conn.rollback()
                raise DatabaseError(str(exc)) from exc
            finally:
                raw.close()

    # File nam ngay tren dia, khong co chuyen phai cho container len.
    def wait_ready(self, timeout: float) -> None:
        with self.cursor() as cur:
            cur.execute("SELECT 1")

    def setup(self) -> None:
        with self.cursor(write=True) as cur:
            for statement in SCHEMA:
                cur.execute(statement)

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                finally:
                    self._conn = None
