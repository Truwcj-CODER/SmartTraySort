#!/usr/bin/env python3
"""Doi tran so ro ma PLC giu duoc.

Con so nay nam o BON cho: mang Pos trong SCL, hai cho kiem tra bien trong FB,
mot cho trong bo giai ma lenh, va hai hang so ben Python. Sua tay bon cho thi
som muon cung lech nhau, nen de mot lenh lo het:

    python tools/set_max_slots.py 500

Sua xong PHAI generate lai khoi 01, 04, 05 trong TIA roi nap xuong CPU. Bang
toa do (02) thi chay lai tools/gen_tray_table.py.

Bo nho: moi ro an 24 byte trong DB (LReal X + LReal Z + Int Dir, can le 8 byte).
CPU 1214C co 100 KB work memory, con phai chia cho ba Technology Object va cac
khoi khac - nen tran cao qua thi TIA se bao thieu bo nho luc bien dich. Gap vay
thi ha so xuong roi chay lai lenh nay.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BYTES_PER_SLOT = 24          # LReal + LReal + Int, can le 8 byte
WORK_MEMORY_KB = 100         # CPU 1214C

# (duong dan, mau tim, cach dung lai) - moi mau phai co dung mot nhom so
EDITS = (
    ("src/01_Types.scl", r"(Pos : ARRAY\[1\.\.)(\d+)(\] OF)", None),
    ("src/01_Types.scl", r"(// so ro dang dung, 1\.\.)(\d+)()", None),
    ("src/04_FB_XY_Tray.scl", r"(#SelPos <= )(\d+)(\))", None),
    ("src/05_FC_CmdDecode.scl", r"(ngoai 1\.\.)(\d+)( tra ve 0)", None),
    ("src/05_FC_CmdDecode.scl", r"(#IF_DB\.SelPos <= )(\d+)(\))", None),
    ("orangepi/app/geometry.py", r"(MAX_PLC_SLOTS = )(\d+)()", None),
    ("orangepi/app/inventory.py", r"(SLOT_COUNT = )(\d+)()", None),
)

# Cho nao nhac toi con so trong loi giai thich thi cung phai doi theo
NOTES = (
    ("src/01_Types.scl", r"(// toi )(\d+)( cho; SlotCount)"),
    ("orangepi/app/geometry.py", r"(khai ARRAY\[1\.\.)(\d+)(\])"),
)


def swap(path: Path, pattern: str, new: int) -> int:
    text = path.read_text(encoding="utf-8")
    updated, hits = re.subn(pattern, lambda m: f"{m[1]}{new}{m[3]}", text)
    if hits:
        path.write_text(updated, encoding="utf-8")
    return hits


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not argv[1].isdigit():
        print(__doc__)
        return 1

    new = int(argv[1])
    if not 1 <= new <= 5000:
        print("tran phai trong khoang 1..5000")
        return 1

    total = 0
    for rel, pattern, _ in EDITS:
        hits = swap(ROOT / rel, pattern, new)
        total += hits
        print(f"  {rel:<32} {hits} cho")
    for rel, pattern in NOTES:
        swap(ROOT / rel, pattern, new)

    if total < len(EDITS):
        print("\n!! co cho khong khop mau - kiem lai bang tay truoc khi nap")
        return 1

    kb = new * BYTES_PER_SLOT / 1024
    print(f"\ntran moi: {new} ro")
    print(f"bang toa do an  {kb:.1f} KB / {WORK_MEMORY_KB} KB work memory "
          f"({kb / WORK_MEMORY_KB * 100:.0f}%)")
    if kb > WORK_MEMORY_KB * 0.25:
        print("!! chiem hon 1/4 bo nho - de y luc bien dich, thieu thi ha xuong")
    print("\nGio generate lai khoi 01, 04, 05 trong TIA roi nap xuong CPU.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
