#!/usr/bin/env python3
# Gia lap day chuyen dang chay: Kafka day don xuong, vat ve lan lon, quet tung cai.
#
#     python3 tests/chay_day_chuyen.py                    # 30 don, moi don 2-3 SKU
#     python3 tests/chay_day_chuyen.py --run              # cho may chay that moi lan quet
#     python3 tests/chay_day_chuyen.py --don 50 --nghi 2  # 50 don, moi vat cach nhau 2 giay
#
# Gian ro chi co 20 khay ma co 30 don, nen 10 don phai NAM CHO. Mo mot cua so
# terminal khac chay tests/lay_don.py de dong vai nguoi lay hang: lay mot don du
# ra la ro trong, va mot don dang cho nhay vao ngay - o day se in ra cho thay.
from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request


def call(url: str, path: str, body: dict | None = None, method: str | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{url}{path}",
        data=data,
        method=method or ("POST" if data is not None else "GET"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} {path}: {exc.read().decode(errors='replace')}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"khong goi duoc {url}: {exc.reason}") from exc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://100.117.86.73:8000")
    ap.add_argument("--don", type=int, default=30, help="so don Kafka day xuong")
    ap.add_argument("--nghi", type=float, default=1.0, help="giay giua hai lan quet")
    ap.add_argument("--run", action="store_true", help="quet xong cho may chay that")
    ap.add_argument("--seed", type=int, default=0, help="0 = moi lan mot khac")
    args = ap.parse_args()
    url = args.url.rstrip("/")
    rng = random.Random(args.seed or None)

    # ---------------------------------------------------------- Kafka day don
    orders = []
    for i in range(args.don):
        code = f"DH-{3001 + i}"
        n = rng.randint(2, 3)
        orders.append({"order": code, "skus": [f"{code}-{j + 1}" for j in range(n)]})

    call(url, "/api/inventory/reset", {})
    out = call(url, "/api/orders", {"orders": orders, "reset": True})
    placed, queued = out["orders"], out["pending"]

    slot_of = {o["order"]: o["slot"] for o in placed}
    total_sku = sum(len(o["skus"]) for o in orders)

    print("=" * 70)
    print(f"KAFKA ĐẨY {args.don} ĐƠN · {total_sku} SKU")
    print("=" * 70)
    for o in placed:
        print(f"  {o['order']}  → khay {o['slot']:>2}   {' '.join(o['skus'])}")
    if queued:
        print(f"\n  {len(queued)} đơn NẰM CHỜ (hết khay): "
              f"{' '.join(q['order'] for q in queued)}")
        print("  → khay nào trống ra là tự nhảy vào.")

    # -------------------------------------------------- vat ve lan lon, quet
    items = [(sku, o["order"]) for o in orders for sku in o["skus"]]
    rng.shuffle(items)

    print("\n" + "=" * 70)
    print("VẬT VỀ BĂNG CHUYỀN — quét từng cái, thứ tự lộn xộn")
    print("=" * 70)
    print("Mở cửa sổ khác chạy:  python3 tests/lay_don.py")
    print("Ctrl-C để dừng.\n")

    known = set(slot_of)
    con_lai = list(items)          # vat chua quet duoc
    stt = 0
    cho = 0

    # Vong lap chay den khi HET vat, khong phai het mot luot. Vat nao co don
    # chua duoc cap ro thi de lai cuoi hang doi, khong vut di.
    #
    # Ban dau cho nay viet mot vong for don gian, gap vat chua co ro thi
    # "continue" - va vat do mat luon. Comment ghi "vong sau quet lai" nhung
    # khong he co vong sau nao.
    while con_lai:
        state = call(url, "/api/orders")
        here = {r["order"] for r in state["orders"]}

        lam_duoc = [x for x in con_lai if x[1] in here]
        if not lam_duoc:
            # Khong vat nao co ro. Chi con cach doi nguoi lay bot don ra.
            cho += 1
            if cho == 1:
                thieu = sorted({o for _, o in con_lai})
                print(f"\n  ⏸  DỪNG — {len(con_lai)} vật còn lại thuộc {len(thieu)} đơn "
                      f"chưa có khay.")
                print(f"     Lấy bớt đơn đã đủ ra (cửa sổ kia) là chạy tiếp ngay.")
                print(f"     Đang chờ: {' '.join(thieu[:8])}"
                      f"{' …' if len(thieu) > 8 else ''}")
            time.sleep(2)
            continue

        if cho:
            print(f"  ▶  CHẠY TIẾP — đã có khay trống.\n")
            cho = 0

        sku, order = lam_duoc[0]
        con_lai.remove((sku, order))
        stt += 1

        out = call(url, "/api/scan", {"code": sku, "run": args.run})
        detail = out.get("inventory", {}).get("order") or {}
        done, total = detail.get("done", 0), detail.get("total", 0)
        mark = "ĐỦ — chờ lấy" if detail.get("complete") else f"{done}/{total}"
        print(f"  {stt:>3}  {sku:<12} → khay {out['slot']:>2}  {order}  {mark}"
              f"   (còn {len(con_lai)} vật)")

        # Ro moi trong ra thi don dang cho da nhay vao - bao cho thay.
        now = {r["order"] for r in call(url, "/api/orders")["orders"]}
        for fresh in sorted(now - known):
            slot = next(r["slot"] for r in call(url, "/api/orders")["orders"]
                        if r["order"] == fresh)
            print(f"       ↳ {fresh} vừa NHẢY VÀO khay {slot} (đơn trước đã lấy đi)")
        known |= now

        time.sleep(args.nghi)

    print("\nhết vật trên băng chuyền.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\ndừng.")
