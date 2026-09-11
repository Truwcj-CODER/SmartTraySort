# Ket noi MySQL, dung bang, va cac kho du lieu.
#
# Tang tren chi thay dict va list[dict] - khong cho SQL ro ri ra ngoai file nay.
from __future__ import annotations

import json
import logging
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from .config import Settings

log = logging.getLogger(__name__)

# code de NULL khi chua gan, nho vay UNIQUE van cho nhieu ro trong: MySQL khong
# coi hai NULL la trung nhau. Dung chuoi rong thi ro thu hai se bi tu choi.
SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS config (
      name       VARCHAR(64)  NOT NULL PRIMARY KEY,
      data       JSON         NOT NULL,
      updated_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS slots (
      slot       INT UNSIGNED NOT NULL PRIMARY KEY,
      code       VARCHAR(128) NULL,
      count      INT UNSIGNED NOT NULL DEFAULT 0,
      capacity   INT UNSIGNED NOT NULL DEFAULT 10,
      updated_at DATETIME     NULL,
      UNIQUE KEY uq_slots_code (code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
)


class DatabaseError(RuntimeError):
    pass


class Database:
    def __init__(self, settings: Settings) -> None:
        self._dsn = dict(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset="utf8mb4",
            autocommit=False,
            cursorclass=DictCursor,
            connect_timeout=settings.mysql_connect_timeout,
        )
        self._lock = threading.Lock()
        self._conn: pymysql.connections.Connection | None = None

    @property
    def endpoint(self) -> str:
        return f"{self._dsn['host']}:{self._dsn['port']}/{self._dsn['database']}"

    def _link(self) -> pymysql.connections.Connection:
        if self._conn is None:
            self._conn = pymysql.connect(**self._dsn)
        else:
            self._conn.ping(reconnect=True)
        return self._conn

    @contextmanager
    def cursor(self, write: bool = False):
        with self._lock:
            try:
                conn = self._link()
                with conn.cursor() as cur:
                    yield cur
                if write:
                    conn.commit()
            except Exception as exc:
                if self._conn is not None:
                    try:
                        self._conn.rollback()
                    except Exception:
                        self._conn = None      # ket noi hong han, lan sau mo lai
                raise DatabaseError(str(exc)) from exc

    # Container MySQL thuong len sau app, nen phai cho chu khong duoc chet.
    def wait_ready(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        last = ""
        while time.monotonic() < deadline:
            try:
                with self.cursor() as cur:
                    cur.execute("SELECT 1")
                log.info("da ket noi MySQL %s", self.endpoint)
                return
            except DatabaseError as exc:
                last = str(exc)
                self._conn = None
                time.sleep(1.0)
        raise DatabaseError(f"khong ket noi duoc MySQL {self.endpoint}: {last}")

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


# Mot ban ghi JSON trong bang config. Giu dung giao dien cua kho file cu.
class ConfigStore:
    def __init__(self, db: Database, name: str, default: dict[str, Any]) -> None:
        self._db = db
        self._name = name
        self._default = default
        # Cung y nghia voi Inventory.revision: duong SSE so con so nay de biet
        # cau hinh vua doi ma gui lai bo cuc.
        self._revision = 0
        with self._db.cursor(write=True) as cur:
            cur.execute(
                "INSERT IGNORE INTO config (name, data) VALUES (%s, %s)",
                (name, json.dumps(default, ensure_ascii=False)),
            )

    @property
    def revision(self) -> int:
        return self._revision

    def read(self) -> dict[str, Any]:
        with self._db.cursor() as cur:
            cur.execute("SELECT data FROM config WHERE name = %s", (self._name,))
            row = cur.fetchone()
        if not row:
            return json.loads(json.dumps(self._default))
        data = row["data"]
        return json.loads(data) if isinstance(data, str) else data

    def write(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._db.cursor(write=True) as cur:
            cur.execute(
                "INSERT INTO config (name, data) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE data = VALUES(data)",
                (self._name, json.dumps(data, ensure_ascii=False)),
            )
        self._revision += 1
        return json.loads(json.dumps(data))

    def update(self, **changes: Any) -> dict[str, Any]:
        merged = self.read()
        merged.update(changes)
        return self.write(merged)

    def reset(self) -> dict[str, Any]:
        return self.write(json.loads(json.dumps(self._default)))


# Bang ro: moi ro mot dong, moi ro mot ma QR.
class SlotTable:
    def __init__(self, db: Database, slot_count: int, default_capacity: int) -> None:
        self._db = db
        self._slot_count = slot_count
        self._default_capacity = default_capacity
        self._fill_missing()

    def _fill_missing(self) -> None:
        with self._db.cursor(write=True) as cur:
            cur.executemany(
                "INSERT IGNORE INTO slots (slot, code, count, capacity) VALUES (%s, NULL, 0, %s)",
                [(n, self._default_capacity) for n in range(1, self._slot_count + 1)],
            )

    @staticmethod
    def _row(row: dict) -> dict:
        stamp = row["updated_at"]
        return {
            "slot": int(row["slot"]),
            "code": row["code"] or "",
            "count": int(row["count"]),
            "capacity": int(row["capacity"]),
            "updated_at": stamp.isoformat(timespec="seconds") if isinstance(stamp, datetime) else stamp,
        }

    def all(self) -> list[dict]:
        with self._db.cursor() as cur:
            cur.execute(
                "SELECT slot, code, count, capacity, updated_at FROM slots ORDER BY slot"
            )
            return [self._row(r) for r in cur.fetchall()]

    def one(self, slot: int) -> dict | None:
        with self._db.cursor() as cur:
            cur.execute(
                "SELECT slot, code, count, capacity, updated_at FROM slots WHERE slot = %s",
                (slot,),
            )
            row = cur.fetchone()
        return self._row(row) if row else None

    def update(self, slot: int, **changes: Any) -> None:
        if "code" in changes:
            changes["code"] = changes["code"].strip() or None
        changes["updated_at"] = datetime.now().replace(microsecond=0)
        sets = ", ".join(f"{k} = %s" for k in changes)
        with self._db.cursor(write=True) as cur:
            cur.execute(
                f"UPDATE slots SET {sets} WHERE slot = %s", (*changes.values(), slot)
            )

    def reset_all(self) -> None:
        with self._db.cursor(write=True) as cur:
            cur.execute(
                "UPDATE slots SET code = NULL, count = 0, capacity = %s, updated_at = NULL",
                (self._default_capacity,),
            )

    def count_rows(self) -> int:
        with self._db.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM slots")
            return int(cur.fetchone()["n"])


# Nap du lieu tu ban luu file cu sang MySQL, chi mot lan.
#
# Chay tren may da co san geometry.json / inventory.json. Bang nao da co
# du lieu thi bo qua, khong de lan chay sau ghi de len.
def migrate_json(db: Database, data_dir: Path) -> None:
    geometry = data_dir / "geometry.json"
    if geometry.exists():
        with db.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM config WHERE name = 'geometry'")
            empty = cur.fetchone()["n"] == 0
        if empty:
            with db.cursor(write=True) as cur:
                cur.execute(
                    "INSERT INTO config (name, data) VALUES ('geometry', %s)",
                    (geometry.read_text(encoding="utf-8"),),
                )
            log.info("da nap geometry.json vao MySQL")

    inventory = data_dir / "inventory.json"
    if not inventory.exists():
        return
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM slots WHERE code IS NOT NULL OR count > 0")
        if cur.fetchone()["n"]:
            return

    try:
        rows = json.loads(inventory.read_text(encoding="utf-8")).get("slots") or []
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("khong doc duoc inventory.json: %s", exc)
        return

    # INSERT ... ON DUPLICATE de khong phu thuoc viec 500 dong trong da duoc tao
    # hay chua - migrate chay truoc Inventory.
    payload = []
    for row in rows:
        code = (row.get("code") or "").strip() or None
        payload.append((int(row["slot"]), code, int(row.get("count") or 0),
                        int(row.get("capacity") or 10)))
    with db.cursor(write=True) as cur:
        cur.executemany(
            "INSERT INTO slots (slot, code, count, capacity) VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE code = VALUES(code), count = VALUES(count), "
            "capacity = VALUES(capacity)",
            payload,
        )
    log.info("da nap %d dong ton kho tu inventory.json vao MySQL", len(payload))
