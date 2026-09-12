#!/usr/bin/env python3
# Chay thu ca luong phan loai theo don hang, tu dau den cuoi.
#
#     python3 tests/kafka_orders_test.py                    # 20 don, khong chay may
#     python3 tests/kafka_orders_test.py --run 3            # chay may that 3 lan dau
#     python3 tests/kafka_orders_test.py --url http://192.168.1.121:8000
#
# Script nay dong vai HE TREN - cho nay trong that la mot consumer Kafka. No day
# xuong mot lo don hang, moi don kem cac SKU thuoc don do. Server tu gan moi don
# vao mot ro trong.
#
# Sau do script bat chuoc nguoi van hanh: cam tung vat len quet, THEO THU TU XAO
# TRON (vat tu 20 don do ve bang chuyen lan lon, khong ai xep sang tung don), roi
# doi chieu ro ma server tra ve voi ro cua don chua SKU do.
#
# Seed co dinh nen danh sach don - SKU in ra lan nao cung y het, doi chieu duoc.
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import time
import urllib.error
import urllib.request

ORDER_COUNT = 20
SKU_PER_ORDER = (2, 6)
SEED = 20260826


def call(url: str, path: str, body: dict | None = None, method: str | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{url}{path}",
        data=data,
        method=method or ("POST" if data else "GET"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SystemExit(f"HTTP {exc.code} khi goi {method or 'GET'} {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"khong goi duoc {url}{path}: {exc.reason}") from exc


# Lo don hang gia. Ma don DH-1001.. va SKU dang HSK-<nhom><so> cho de doc.
def build_orders(rng: random.Random) -> list[dict]:
    orders = []
    for i in range(ORDER_COUNT):
        code = f"DH-{1001 + i}"
        n = rng.randint(*SKU_PER_ORDER)
        skus = [f"HSK-{chr(65 + i)}{rng.randrange(1000, 9999)}" for _ in range(n)]
        orders.append({"order": code, "skus": sorted(set(skus))})
    return orders


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--run", type=int, default=0,
                    help="so lan quet dau tien cho may chay that; -1 la chay het")
    ap.add_argument("--out", default=None,
                    help="ghi danh sach don - SKU ra file de doi chieu")
    ap.add_argument("--seed", type=int, default=SEED,
                    help="doi seed de ra lo don khac; 0 la moi lan mot khac")
    ap.add_argument("--delay", type=float, default=0.0,
                    help="nghi bao nhieu giay giua hai lan quet, de con kip nhin")
    args = ap.parse_args()
    url = args.url.rstrip("/")

    rng = random.Random(args.seed or None)
    orders = build_orders(rng)

    # ---------------------------------------------------------- 1. day don
    print("=" * 78)
    print("BUOC 1 — he tren day 20 don xuong, server tu gan moi don mot ro trong")
    print("=" * 78)
    placed = call(url, "/api/orders", {"orders": orders, "reset": True})["orders"]

    slot_of_order = {row["order"]: row["slot"] for row in placed}
    order_of_sku: dict[str, str] = {}
    total_skus = 0
    print(f"\n{'DON':<10}{'RO':>4}   SKU")
    print("-" * 78)
    for row in placed:
        for sku in row["skus"]:
            order_of_sku[sku] = row["order"]
        total_skus += len(row["skus"])
        print(f"{row['order']:<10}{row['slot']:>4}   {' '.join(row['skus'])}")
    print("-" * 78)
    print(f"{ORDER_COUNT} don · {total_skus} SKU")

    if args.out:
        lines = [
            "DANH SACH DON HANG - de doi chieu voi may khi chay",
            f"{ORDER_COUNT} don, moi don {SKU_PER_ORDER[0]}-{SKU_PER_ORDER[1]} SKU, tong {total_skus} SKU",
            "",
            f"{'DON':<10}{'RO':>4}   SKU",
            "-" * 78,
        ]
        for row in placed:
            lines.append(f"{row['order']:<10}{row['slot']:>4}   {' '.join(row['skus'])}")
        lines += ["-" * 78, "", "TRA NGUOC SKU -> DON -> RO:", ""]
        for sku in sorted(order_of_sku):
            o = order_of_sku[sku]
            lines.append(f"  {sku:<12} -> {o:<10} -> ro {slot_of_order[o]}")
        pathlib.Path(args.out).write_text("\n".join(lines) + "\n")
        print(f"\nda ghi danh sach ra {args.out}")

    # ------------------------------------------------------- 2. quet tung vat
    print()
    print("=" * 78)
    print("BUOC 2 — quet tung vat theo thu tu xao tron, doi chieu ro tra ve")
    print("=" * 78)
    items = list(order_of_sku)
    rng.shuffle(items)

    print(f"\n{'#':>3}  {'SKU':<12}{'DON DUNG':<10}{'RO DUNG':>7}{'RO TRA VE':>10}   KET QUA")
    print("-" * 78)

    ok = bad = 0
    fails: list[str] = []
    for i, sku in enumerate(items, 1):
        want_order = order_of_sku[sku]
        want_slot = slot_of_order[want_order]
        run_now = args.run < 0 or i <= args.run
        out = call(url, "/api/scan", {"code": sku, "run": run_now})
        got = out["slot"]
        good = got == want_slot
        if good:
            ok += 1
        else:
            bad += 1
            fails.append(f"{sku} thuoc {want_order} (ro {want_slot}) nhung vao ro {got}")
        print(
            f"{i:>3}  {sku:<12}{want_order:<10}{want_slot:>7}{got:>10}   "
            f"{'dung' if good else 'SAI'}",
            flush=True,
        )
        if args.delay:
            time.sleep(args.delay)

    # ------------------------------------------------------------- 3. tong ket
    print("-" * 78)
    print(f"\n{ok}/{len(items)} vat vao dung ro cua don.")
    if fails:
        print(f"\n{bad} cho SAI:")
        for line in fails:
            print(f"  - {line}")

    # Ton kho tung ro phai bang so SKU cua don nam o ro do.
    print()
    print("=" * 78)
    print("BUOC 3 — doi chieu ton kho tung ro voi so SKU cua don")
    print("=" * 78)
    rows = call(url, "/api/orders")["orders"]
    mismatch = 0
    print(f"\n{'DON':<10}{'RO':>4}{'DA VAO':>8}{'PHAI CO':>9}")
    print("-" * 78)
    for row in sorted(rows, key=lambda r: r["slot"]):
        want = len([s for s, o in order_of_sku.items() if o == row["order"]])
        flag = "" if row["count"] == want else "   <-- LECH"
        if flag:
            mismatch += 1
        print(f"{row['order']:<10}{row['slot']:>4}{row['count']:>8}{want:>9}{flag}")
    print("-" * 78)

    if bad or mismatch:
        print(f"\nKET QUA: HONG — {bad} vat sai ro, {mismatch} ro lech ton kho")
        return 1
    print(f"\nKET QUA: DAT — ca {len(items)} vat vao dung don cua no")
    return 0


if __name__ == "__main__":
    sys.exit(main())
