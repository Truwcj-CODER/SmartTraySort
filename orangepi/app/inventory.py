from __future__ import annotations

from .db import SlotTable

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
    def __init__(self, table: SlotTable) -> None:
        self._table = table
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

    # Ma QR nay thuoc khay nao. Tra None neu chua gan cho khay nao.
    def find_slot_for_code(self, code: str) -> int | None:
        code = code.strip()
        if not code:
            return None
        for s in self._slots[:self._active]:
            if s["code"].strip().lower() == code.lower():
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
