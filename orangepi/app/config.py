from __future__ import annotations

import os
from dataclasses import dataclass, fields
from functools import lru_cache
from pathlib import Path
from typing import get_type_hints

DOTENV = Path(__file__).resolve().parent.parent / ".env"


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    
    plc_host: str
    plc_port: int
    plc_unit: int
    plc_connect_timeout: float

    net_setup: bool
    plc_local_ip: str
    plc_local_prefix: int
    plc_iface: str
    plc_net_interval: float

    poll_interval: float
    command_timeout: float
    homing_timeout: float

    http_host: str
    http_port: int

    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str
    mysql_connect_timeout: float
    mysql_ready_timeout: float


def _load_dotenv(path: Path | None = None) -> None:

    path = path or DOTENV
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _as_bool(raw: str) -> bool:
    if raw.lower() in ("1", "true", "yes", "on"):
        return True
    if raw.lower() in ("0", "false", "no", "off"):
        return False
    raise ValueError("phai la 1/0")


# Cot 2: co duoc de trong khong. Rong nghia la "tu chon", khac han voi thieu dong.
_BLANK_OK = {"plc_local_ip", "plc_iface"}
_CAST = {bool: _as_bool, int: int, float: float, str: str}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv()

    hints = get_type_hints(Settings)
    values: dict[str, object] = {}
    missing: list[str] = []
    bad: list[str] = []

    for field in fields(Settings):
        key = field.name.upper()
        raw = os.getenv(key)
        if raw is None:
            missing.append(key)
            continue
        raw = raw.strip()
        if not raw and field.name not in _BLANK_OK:
            missing.append(key)
            continue
        try:
            values[field.name] = _CAST[hints[field.name]](raw)
        except ValueError as exc:
            bad.append(f"{key}={raw!r} ({exc})")

    if missing or bad:
        parts = []
        if missing:
            parts.append("thieu: " + ", ".join(missing))
        if bad:
            parts.append("sai kieu: " + "; ".join(bad))
        raise ConfigError(f"cau hinh trong {DOTENV.name} chua dung — " + " | ".join(parts))

    return Settings(**values)
