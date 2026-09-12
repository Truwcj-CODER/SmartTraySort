from __future__ import annotations

from .db import PendingTable, SkuTable, SlotTable

# Luon giu du so dong bang tran cua PLC. Bo cuc thuc te co the it ro hon - khi
# do chi phan dau danh sach duoc dung, phan con lai nam cho san. Nho vay doi
# kich thuoc ro qua lai khong lam mat ton kho da nhap.
SLOT_COUNT = 500
DEFAULT_CAPACITY = 10


class SlotFullError(RuntimeError):
    pass


class SlotEmptyError(RuntimeError):
    pass


# Theo doi khay nao dang chua gi, con bao nhieu cho.
#
# PLC khong biet gi ve chuyen nay - no chi chay toi toa do. Ton kho nam trong
# MySQL; ban sao trong bo nho chi de doc nhanh, moi thay doi deu ghi xuong
# bang ngay roi moi cap nhat ban sao.
class Inventory:
    def __init__(
        self,
        table: SlotTable,
        skus: SkuTable | None = None,
        pending: PendingTable | None = None,
    ) -> None:
        self._table = table
        self._skus = skus
        self._pending = pending
        # Ban sao trong bo nho cua bang SKU -> don. Quet ma la duong nong nhat
        # trong ca he, khong the moi lan quet lai di hoi MySQL.
        self._sku_order: dict[str, str] = {}
        # Ten SKU dung nhu he tren gui - de con hien lai cho nguoi doc.
        self._sku_name: dict[str, str] = {}
        self._sku_done: set[str] = set()
        # Don da nhan nhung chua co ro. Ban sao trong bo nho de doc nhanh, ban
        # that nam duoi MySQL - restart server khong mat don nao.
        self._queue: list[dict] = pending.all() if pending is not None else []
        # Tra "da co trong hang doi chua" bang set thay vi quet ca danh sach.
        # Quet ca danh sach cho MOI don la O(n^2): 300 don thi khong thay gi,
        # 10 nghin don la 50 trieu phep so moi lan keo hang doi.
        self._queued: set[str] = {q["order"] for q in self._queue}
        # SKU cua don DANG CHO ro. Tach rieng khoi _sku_order (chi chua don da
        # co ro) de tra loi duoc cau "ma nay thuoc don nao" cho ca hai truong
        # hop - khong thi quet vat cua don dang cho se bao "khong thuoc don nao",
        # ma no co thuoc, chi la don chua duoc cap ro.
        self._queued_sku: dict[str, str] = {
            sku.strip().lower(): q["order"] for q in self._queue for sku in q["skus"]
        }
        if skus is not None:
            skus.migrate()
            for raw, order in skus.all().items():
                key = raw.strip().lower()
                self._sku_order[key] = order
                self._sku_name[key] = raw
            self._sku_done = {k for k, v in skus.scanned().items() if v}
            self._sku_done = {k.strip().lower() for k in self._sku_done}
        self._slots = self._table.all()
        self._active = SLOT_COUNT
        # Dem so lan bang thay doi. Duong SSE so con so nay moi vong poll de biet
        # co phai gui lai bang khong - re hon nhieu so voi dung ca bang ra so.
        self._revision = 0

    # Tang moi khi bang doi. Ai theo doi chi can nho mot so nguyen.
    @property
    def revision(self) -> int:
        return self._revision

    def reload(self) -> None:
        self._slots = self._table.all()
        self._revision += 1

    # Nhung ro nam ngoai bo cuc moi ma van dang chua vat.
    #
    # Bo cuc co lai thi may ro cuoi bien mat khoi giao dien. So lieu khong mat
    # (van nam trong bang), nhung nguoi van hanh phai biet de con di lay vat ra.
    def stock_beyond(self, count: int) -> list[dict]:
        return [dict(s) for s in self._slots[max(0, int(count)):] if s["count"] > 0]

    # So ro ma bo cuc hien tai thuc su co. Cac dong sau do bi bo qua.
    def set_active(self, count: int) -> None:
        active = max(0, min(SLOT_COUNT, int(count)))
        if active != self._active:
            self._active = active
            self._revision += 1

    # --------------------------------------------------------------- doc
    @property
    def slots(self) -> list[dict]:
        return [dict(s) for s in self._slots[:self._active]]

    def slot(self, number: int) -> dict:
        return dict(self._slots[self._index(number)])

    def summary(self) -> dict:
        rows = self._slots[:self._active]
        total = sum(s["count"] for s in rows)
        capacity = sum(s["capacity"] for s in rows)
        return {
            "total_items": total,
            "total_capacity": capacity,
            "slot_count": len(rows),
            "full_slots": sum(1 for s in rows if self._is_full(s)),
            "empty_slots": sum(1 for s in rows if s["count"] == 0),
            "fill_percent": round(total / capacity * 100, 1) if capacity else 0.0,
        }

    # Ma vua quet thuoc khay nao. Tra None neu khong lan ra duoc khay nao.
    #
    # Hai duong, theo dung thu tu:
    #   1. Ma DON hang - quet thang nhan don thi khop ngay voi ma gan cho ro.
    #   2. Ma SKU cua mot vat - tra bang SKU -> don, roi tu don ra ro. Day la
    #      duong thuong dung: nguoi van hanh cam vat len quet, khong ai di quet
    #      lai nhan don cho tung mon.
    def find_slot_for_code(self, code: str) -> int | None:
        code = code.strip()
        if not code:
            return None
        direct = self._slot_with_code(code)
        if direct is not None:
            return direct
        order = self._sku_order.get(code.lower())
        return self._slot_with_code(order) if order else None

    # Don hang cua mot SKU - de tang tren con noi cho nguoi van hanh biet.
    def order_of_sku(self, code: str) -> str | None:
        return self._sku_order.get(code.strip().lower())

    # Ma nay thuoc mot don DANG CHO ro? Tra ve ma don, hoac None.
    def queued_order_of_sku(self, code: str) -> str | None:
        return self._queued_sku.get(code.strip().lower())

    def _slot_with_code(self, code: str | None) -> int | None:
        if not code:
            return None
        want = code.strip().lower()
        for s in self._slots[:self._active]:
            if s["code"].strip().lower() == want:
                return s["slot"]
        return None

    # Khay trong dau tien - dung khi ma quet chua duoc gan cho khay nao.
    def first_free_slot(self) -> int | None:
        for s in self._slots[:self._active]:
            if not self._is_full(s):
                return s["slot"]
        return None

    # --------------------------------------------------------------- ghi
    def assign_code(self, number: int, code: str) -> dict:
        code = code.strip()
        owner = self.find_slot_for_code(code)
        if code and owner is not None and owner != number:
            raise ValueError(f"ma {code} da gan cho khay {owner}")
        return self._mutate(number, code=code)

    def set_capacity(self, number: int, capacity: int) -> dict:
        if capacity < 0:
            raise ValueError("suc chua khong duoc am")
        return self._mutate(number, capacity=capacity)

    def add_item(self, number: int, amount: int = 1) -> dict:
        entry = self._slots[self._index(number)]
        if entry["count"] + amount > entry["capacity"]:
            raise SlotFullError(
                f"khay {number} da day ({entry['count']}/{entry['capacity']})"
            )
        return self._mutate(number, count=entry["count"] + amount)

    def remove_item(self, number: int, amount: int = 1) -> dict:
        entry = self._slots[self._index(number)]
        if entry["count"] - amount < 0:
            raise SlotEmptyError(f"khay {number} dang trong")
        return self._mutate(number, count=entry["count"] - amount)

    def clear_slot(self, number: int) -> dict:
        return self._mutate(number, count=0)

    # He tren day danh sach don xuong. Moi don an mot ro trong, va cac SKU cua
    # no vao bang tra. Tra ve dung thu tu da gan de tang tren doi chieu.
    #
    # Het ro trong thi DUNG lai va bao ro - khong am tham bo qua don con lai,
    # vi lam vay thi luc quet no se roi vao nhanh "tu chon ro trong" va vat di
    # sai don ma khong ai biet.
    def assign_orders(self, orders: list[dict], reset: bool = False) -> list[dict]:
        if reset:
            self.reset()
            if self._skus is not None:
                self._skus.clear()
            self._sku_order = {}
            self._sku_name = {}
            self._sku_done = set()
            self._queue = []
            self._queued = set()
            self._queued_sku = {}
            if self._pending is not None:
                self._pending.clear()

        placed: list[dict] = []
        pending: list[dict] = []
        fresh: list[dict] = []          # don moi vao hang doi, can ghi xuong DB
        taken: list[str] = []           # don roi hang doi vi da co ro
        pairs: list[tuple[str, str]] = []
        for order in orders:
            code = str(order.get("order", "")).strip()
            if not code:
                raise ValueError("don hang thieu ma")
            slot = self._slot_with_code(code) or self._first_unassigned_slot()
            if slot is None:
                # Het ro trong thi GIU LAI don do, khong chan ca lo. Chan ca lo
                # thi mot ro ket la dung ca day chuyen; con tra ve danh sach con
                # thieu thi he tren biet ma day lai sau.
                waiting = {"order": code, "skus": list(order.get("skus", []))}
                if code not in self._queued:
                    self._queue.append(waiting)
                    self._queued.add(code)
                    for sku in waiting["skus"]:
                        self._queued_sku[str(sku).strip().lower()] = code
                    fresh.append(waiting)
                pending.append(waiting)
                continue
            self.assign_code(slot, code)
            skus = [str(x).strip() for x in order.get("skus", []) if str(x).strip()]
            # Suc chua cua ro CHINH LA so mon cua don. Nho vay the ro hien "0/6"
            # roi day dan toi "6/6" la biet don du hay chua - khong phai cai
            # "0/10" co dinh chang noi len dieu gi ve don.
            if skus:
                self.set_capacity(slot, len(skus))
            for sku in skus:
                pairs.append((sku, code))
                self._sku_order[sku.lower()] = code
                self._sku_name[sku.lower()] = sku
                self._sku_done.discard(sku.lower())
            if code in self._queued:
                self._queue = [q for q in self._queue if q["order"] != code]
                self._queued.discard(code)
                self._queued_sku = {
                    k: v for k, v in self._queued_sku.items() if v != code
                }
                taken.append(code)
            placed.append({"order": code, "slot": slot, "skus": skus})

        if self._skus is not None:
            self._skus.put_many(pairs)
        if self._pending is not None:
            self._pending.put_many(fresh)
            self._pending.drop(taken)
        self._revision += 1
        return {"placed": placed, "pending": pending}

    # Don da lay di roi: tra ro ve TRONG cho don sau vao.
    #
    # Day la buoc chuyen con thieu cua vong doi mot cai ro. Server biet khi nao
    # don DU (dem duoc), nhung khong tu biet khi nao hang duoc BE DI - chuyen do
    # xay ra ngoai doi. Phai co ai bao: he tren ban event xuong, nguoi quet lai
    # ma don luc bung thung, hoac bam nut tren tablet. Ca ba deu goi vao day.
    def release_order(self, code: str) -> dict | None:
        slot = self._slot_with_code(code)
        if slot is None:
            return None
        entry = self.slot(slot)
        order = entry["code"].strip()

        self.clear_slot(slot)
        self.assign_code(slot, "")
        self.set_capacity(slot, 0)      # het don thi khong chua duoc gi nua

        keys = [k for k, v in self._sku_order.items() if v == order]
        for key in keys:
            self._sku_order.pop(key, None)
            self._sku_name.pop(key, None)
            self._sku_done.discard(key)
        if self._skus is not None and order:
            self._skus.drop_orders([order])

        self._revision += 1
        moved = self._drain_queue()
        return {"order": order, "slot": slot, "freed": len(keys), "moved_in": moved}

    # Ro vua trong ra thi keo don dang cho vao ngay. Goi sau moi lan nha ro.
    def _drain_queue(self) -> list[dict]:
        if not self._queue:
            return []
        waiting, self._queue = self._queue, []
        self._queued = set()
        self._queued_sku = {}
        return self.assign_orders(waiting, reset=False)["placed"]

    @property
    def queue(self) -> list[dict]:
        return [dict(q) for q in self._queue]

    # Danh dau mot SKU la da quet vao ro. Goi sau khi ton kho da cong xong.
    def mark_scanned(self, code: str) -> None:
        key = code.strip().lower()
        if key not in self._sku_order:
            return
        self._sku_done.add(key)
        if self._skus is not None:
            self._skus.mark_scanned(self._sku_name.get(key, code.strip()))
        self._revision += 1

    # Danh sach don dang gan tren gian ro, kem tung SKU da vao hay chua.
    def orders(self) -> list[dict]:
        by_order: dict[str, list[str]] = {}
        for key in self._sku_order:
            by_order.setdefault(self._sku_order[key], []).append(key)
        rows = []
        for s in self._slots[:self._active]:
            code = s["code"].strip()
            if not code:
                continue
            keys = sorted(by_order.get(code, []), key=lambda k: self._sku_name.get(k, k))
            items = [
                {"sku": self._sku_name.get(k, k), "scanned": k in self._sku_done}
                for k in keys
            ]
            done = sum(1 for it in items if it["scanned"])
            rows.append({
                "order": code,
                "slot": s["slot"],
                "count": s["count"],
                "capacity": s["capacity"],
                "items": items,
                "done": done,
                "total": len(items),
                "complete": len(items) > 0 and done == len(items),
                # Giu ten cu cho cho nao chi can danh sach ma.
                "skus": [it["sku"] for it in items],
            })
        return rows

    # Mot don, tra theo ma don hoac theo so ro.
    def order_detail(self, code: str | None = None, slot: int | None = None) -> dict | None:
        want = code.strip().lower() if code else None
        for row in self.orders():
            if want is not None and row["order"].strip().lower() == want:
                return row
            if slot is not None and row["slot"] == slot:
                return row
        return None

    # Ro chua gan don nao va dang trong.
    def _first_unassigned_slot(self) -> int | None:
        for s in self._slots[:self._active]:
            if not s["code"].strip() and s["count"] == 0:
                return s["slot"]
        return None

    def reset(self) -> list[dict]:
        self._table.reset_all()
        self.reload()          # giu nguyen self._active - bo cuc khong doi
        return self.slots

    # --------------------------------------------------------------- noi bo
    @staticmethod
    def _is_full(entry: dict) -> bool:
        return entry["count"] >= entry["capacity"]

    @staticmethod
    def _index(number: int) -> int:
        if not 1 <= number <= SLOT_COUNT:
            raise ValueError(f"so khay phai trong khoang 1..{SLOT_COUNT}")
        return number - 1

    def _mutate(self, number: int, **changes) -> dict:
        index = self._index(number)
        self._table.update(number, **changes)
        row = self._table.one(number)
        if row is None:
            raise ValueError(f"khong tim thay khay {number}")
        self._slots[index] = row
        self._revision += 1
        return dict(row)
