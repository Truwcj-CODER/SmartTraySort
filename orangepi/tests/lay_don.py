#!/usr/bin/env python3
# Tram lay don: go (hoac quet) ma don, xem du chua, du thi lay ra va tra ro ve trong.
#
#     python3 tests/lay_don.py
#     python3 tests/lay_don.py --url http://172.16.10.140:8000
#     python3 tests/lay_don.py --yes          # du la lay luon, khong hoi lai
#
# Dung cho cho nguoi dung thung o cuoi day chuyen. Cam sung quet ban vao mot cai
# la ma nhay ra day roi Enter - khong phai go tay.
#
# Luat: CHI don da du moi lay ra duoc. Con thieu mon thi script bao thieu mon
# nao va khong dong gi toi ro - lay som mot cai la don thieu hang ma khong ai
# biet, den tay khach moi lo ra.
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def call(url: str, path: str, body: dict | None = None, method: str | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{url}{path}",
        data=data,
        # Co endpoint POST ma khong co than tin (/orders/{ma}/done) - doan
        # "co body thi POST" khong du, phai noi thang phuong thuc.
        method=method or ("POST" if data is not None else "GET"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(body)
        except ValueError:
            return exc.code, {"detail": body}
    except urllib.error.URLError as exc:
        raise SystemExit(f"khong goi duoc {url}: {exc.reason}") from exc


def free_slots(url: str) -> tuple[int, int]:
    _, data = call(url, "/api/slots")
    rows = data.get("slots", [])
    taken = sum(1 for s in rows if s.get("code", "").strip())
    return len(rows) - taken, len(rows)


def show(order: dict) -> None:
    done, total = order["done"], order["total"]
    state = "ĐỦ" if order["complete"] else f"THIẾU {total - done}"
    print(f"\n  {order['order']}   khay {order['slot']}   {done}/{total} món   [{state}]")
    for item in order["items"]:
        print(f"    {'✓' if item['scanned'] else '○'} {item['sku']}")


def take(url: str, code: str, auto_yes: bool) -> None:
    status, data = call(url, "/api/lookup", {"code": code})
    if status == 404:
        print(f"\n  !! {data.get('detail', 'không tìm thấy')}")
        return

    order = data["order"]
    show(order)

    if not order["complete"]:
        missing = [i["sku"] for i in order["items"] if not i["scanned"]]
        print(f"\n  CHƯA LẤY ĐƯỢC — còn chờ: {' '.join(missing)}")
        return

    if not auto_yes:
        answer = input("\n  Lấy đơn này ra? [Enter = có, n = không] ").strip().lower()
        if answer.startswith("n"):
            print("  bỏ qua.")
            return

    status, done = call(url, f"/api/orders/{code}/done", method="POST")
    if status != 200:
        print(f"\n  !! {done.get('detail', 'lỗi')}")
        return

    free, total_slots = free_slots(url)
    print(f"\n  ĐÃ LẤY — khay {done['slot']} trở về trống.")
    print(f"  Giàn rổ: {free}/{total_slots} khay trống, sẵn cho đơn mới từ Kafka.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://100.117.86.73:8000")
    ap.add_argument("--yes", action="store_true", help="đủ là lấy luôn, không hỏi lại")
    args = ap.parse_args()
    url = args.url.rstrip("/")

    free, total_slots = free_slots(url)
    print("=" * 62)
    print("TRẠM LẤY ĐƠN — quét hoặc gõ mã đơn, Enter để xem")
    print(f"{url}   ·   {free}/{total_slots} khay trống")
    print("=" * 62)
    print("Enter rỗng để thoát.")

    while True:
        try:
            code = input("\nMã đơn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not code:
            return 0
        take(url, code, args.yes)


if __name__ == "__main__":
    sys.exit(main())
