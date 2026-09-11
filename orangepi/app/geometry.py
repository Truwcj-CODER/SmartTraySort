from __future__ import annotations

import math
from dataclasses import dataclass, asdict

# Mang Pos trong 01_Types.scl khai ARRAY[1..500], nen day la tran cung cua PLC.
# So ro THUC TE khong co dinh: no la ket qua tinh tu hanh trinh va kich thuoc ro,
# va duoc bao xuong PLC bang lenh 13 (SlotCount).
MAX_PLC_SLOTS = 500

# Khe ho toi thieu khi khay chay ngang luon duoi day ro hang tren (mm)
MIN_TRAVEL_GAP = 30.0

# Chua ra bao nhieu mm so voi gioi han phan mem cua truc. Dung ngay tren vach
# la PLC bao loi - da dinh mot lan roi, xem ghi chu o park_z.
LIMIT_MARGIN = 20.0

# Hai day ro nam hai ben ray. Thu tu nay quyet dinh cach danh so o.
SIDES = ((+1, "phai"), (-1, "trai"))

# Tan so xung cao nhat dong co con keo noi, do bang tay: cho chay o che do phat
# xung roi tang dan cho toi khi dong co duoi buoc. May nay do duoc 20 000 xung/s
# tren ca ba truc.
#
# Chia cho so xung moi mm ra toc do tran theo mm/s - cung chinh la con so nhap
# vao Dynamics > Max velocity trong TIA. Thap hon nhieu so voi tran 100 kHz cua
# kenh PTO tren PLC, vi dong co duoi buoc truoc khi PLC het suc, nen day moi la
# con so quyet dinh may chay nhanh toi dau.
#
# Doi dong co hay doi vi buoc thi do lai roi sua o day.
MAX_PULSE_HZ = 20000.0

# Gia toc cua ba truc. Cac lenh MC_MoveAbsolute khong truyen Acceleration nen
# truc lay thang tu DynamicDefaults; server ghi may so nay xuong do bang tham so
# 16/17/18 moi lan khoi dong va moi lan luu cau hinh.
#
# De hang so chu khong phai o nhap tren web: doi gia toc la viec chinh mot lan
# khi lap may, khong phai viec hang ngay - bay ra trang Cai dat chi to roi.
#
# Gia toc quyet dinh quang tang toc v^2/2a. Buoc giua hai cot la 406 mm, nen o
# 200 mm/s voi gia toc 200 thi mat 100 mm de tang toc va 100 mm de ham - dung
# nua quang duong. Nang len 1000 thi chi con 20 mm moi dau, chu trinh ngan di
# gan mot giay moi lan di chuyen. Nang tu tu va chay thu, gia toc gat qua thi
# dong co truot buoc.
ACCEL_X = 200.0   # mm/s2
ACCEL_Z = 200.0   # mm/s2
ACCEL_Y = 200.0   # do/s2


# Kich thuoc thuc cua may. Server tu suy ra so ro va toa do tung ro tu day.
#
# Nguoi dung khong go so o hay do cao tung hang. Ho khai hanh trinh hai truc
# va kich thuoc mot cai ro, con so ro xep duoc la KET QUA tinh ra.
@dataclass
class Geometry:
    # --- goc dat gian ro ---
    x_first: float = 200.0         # tam ro cot dau tien, tinh tu tram nap (mm)
    z_first: float = 100.0         # mieng ro hang duoi cung (mm)

    # --- kich thuoc mot cai ro ---
    basket_length: float = 200.0   # doc theo truc X (mm)   <- so mau, ro VUONG
    basket_depth: float = 200.0    # theo chieu sau, huong ra xa ray (mm)
    basket_height: float = 60.0    # chieu cao thanh ro (mm) <- so mau
    basket_gap: float = 10.0       # khe ho TOI THIEU giua hai ro ke nhau (mm)

    # --- quan he giua ray va gian ro ---
    rack_offset: float = 95.0      # tu tam ray toi MEP TRONG cua ro (mm)
    drop_lift: float = 90.0        # khay dung cao hon mieng ro bao nhieu khi do (mm)

    # --- khay dung vat tren dau cong tac ---
    tray_width: float = 200.0      # be rong khay, do theo chieu NO LAT (mm)
    # Mam chi can vua hon cai ro mot chut. Rong theo chieu lat thi phai xap xi
    # be sau cua ro, khong thi vat truot xuong lai roi ra ngoai ro.
    tray_length: float = 220.0     # chieu dai khay, doc theo truc X (mm)

    # --- TRAM NAP = vi tri cho = diem lay goc toa do ---
    # Khong dat dung 0: 0 la gioi han phan mem, do trung vach la PLC bao loi.
    park_x: float = 5.0
    park_y: float = 0.0
    park_z: float = 5.0

    # --- hanh trinh toi da cua tung truc ---
    x_travel: float = 1250.0       # hanh trinh ngang (mm)  <- so mau, cho ra 5 cot
    z_travel: float = 400.0        # hanh trinh len xuong (mm)
    y_max_angle: float = 70.0      # goc lat toi da cho phep (+- do)

    # --- tham so chay may: day xuong PLC bang lenh 14, khong phai sua trong TIA ---
    tilt_angle: float = 60.0       # goc lat khi do vat (do)
    tilt_vel: float = 200.0        # toc do lat (do/s)
    tilt_hold_ms: int = 1000       # giu o goc lat bao lau (ms)
    tilt_count: int = 1            # lat may lan moi chu trinh, 0 = bo qua buoc lat
    vel_x: float = 80.0            # toc do chay ngang (mm/s)
    vel_z: float = 60.0            # toc do len xuong (mm/s) - cham hon vi chong trong luc
    auto_home: bool = True         # tu HOME khi bat dien
    dwell_ms: int = 1000           # dung yen tai ro cho het rung truoc khi lat (ms)

    # --- tham so co khi, PHAI nhap trung voi Technology Object trong TIA ---
    # Server khong ghi duoc may so nay xuong PLC, chi luu de doi chieu va tinh toan.
    x_pulses_per_rev: int = 3200
    x_mm_per_rev: float = 32.0
    z_pulses_per_rev: int = 2000
    z_mm_per_rev: float = 54.0
    y_pulses_per_rev: int = 1000
    y_deg_per_rev: float = 360.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Geometry":
        fields = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in fields})

    # ==================================================== buoc xep theo hai chieu

    # Buoc ngang chat nhat co the: hai ro ke nhau chi cach dung khe ho toi thieu.
    #
    # Dung de DEM xem nhet duoc bao nhieu cot, khong phai de dat toa do.
    @property
    def min_pitch(self) -> float:
        return self.basket_length + self.basket_gap

    # Buoc ngang that su giua hai tam ro.
    #
    # Dem duoc bao nhieu cot roi thi trai deu ra cho KIN hanh trinh, sao cho
    # mep ngoai cua ro cuoi cham dung cuoi hanh trinh X. Phan du khong don het
    # ve mot dau ma chia deu vao cac khe.
    @property
    def x_pitch(self) -> float:
        plan = self.layout()
        columns = plan["columns"]

        # Bi bang toa do trong PLC chan lai thi gian may ro it oi do ra ca hanh
        # trinh la vo ly - luc do cu xep chat tu dau.
        if columns < 2 or plan["capped"]:
            return self.min_pitch

        last_centre = self.x_travel - self.basket_length / 2
        return max(self.min_pitch, (last_centre - self.x_first) / (columns - 1))

    # Khe ho that giua hai ro sau khi da trai deu.
    @property
    def x_gap(self) -> float:
        return self.x_pitch - self.basket_length

    # Mieng ro hang nay toi mieng ro hang ngay tren no.
    #
    # Khong duoc dat sat nhau: khay phuc vu hang duoi chay ngang o cao do
    # mieng_ro + drop_lift, va phai luon lot duoi day ro cua hang tren.
    @property
    def row_pitch(self) -> float:
        return self.basket_height + self.drop_lift + MIN_TRAVEL_GAP

    # ========================================================== so ro xep duoc

    # So cot ro xep duoc theo phan hanh trinh ngang con lai.
    def columns_that_fit(self) -> int:
        # Do tu tam ro dau toi cuoi hanh trinh, tru nua than cai ro cuoi cung.
        room = (self.x_travel - self.basket_length / 2) - self.x_first
        if room < 0 or self.min_pitch <= 0:
            return 0
        return max(0, math.floor(room / self.min_pitch) + 1)

    # So hang xep duoc theo hanh trinh doc.
    #
    # Hang tren cung van phai chua cho cho khay dung cao hon mieng ro, va
    # khong duoc de khay dung dung tren vach gioi han - nen tran that su la
    # z_travel - LIMIT_MARGIN - drop_lift.
    def rows_that_fit(self) -> int:
        room = (self.z_travel - LIMIT_MARGIN - self.drop_lift) - self.z_first
        if room < 0 or self.row_pitch <= 0:
            return 0
        return max(0, math.floor(room / self.row_pitch) + 1)

    # Bo cuc cuoi cung, sau khi cat bot cho vua bang toa do trong PLC.
    def layout(self) -> dict:
        rows = self.rows_that_fit()
        wanted = self.columns_that_fit()

        if rows == 0 or wanted == 0:
            return {"rows": 0, "columns": 0, "slots": 0,
                    "columns_by_travel": wanted, "capped": False}

        # Moi hang phuc vu ca hai ben, nen mot hang an 2 * so_cot o trong bang.
        columns = min(wanted, MAX_PLC_SLOTS // (2 * rows))

        return {
            "rows": rows,
            "columns": columns,
            "slots": rows * columns * 2,
            "columns_by_travel": wanted,      # so cot ma truc X con cho duoc
            "capped": columns < wanted,       # bi bang toa do trong PLC chan lai
        }

    @property
    def slot_count(self) -> int:
        return self.layout()["slots"]

    # ============================================================ toa do tung ro

    # Do cao mieng ro cua mot hang. row_index 0 = hang TREN CUNG.
    def _row_rim(self, row_index: int, rows: int) -> float:
        return self.z_first + (rows - 1 - row_index) * self.row_pitch

    # Ca gian ro, danh so tu 1. Dung de day xuong PLC hoac hien tren web.
    #
    # So chay theo tung hang tu tren xuong, moi hang het ben phai roi toi ben
    # trai. Voi 2 hang x 5 cot ra dung 1-5 phai tren, 6-10 trai tren,
    # 11-15 phai duoi, 16-20 trai duoi - giong het cach danh so cu.
    def all_positions(self) -> list[dict]:
        plan = self.layout()
        rows, columns = plan["rows"], plan["columns"]

        out: list[dict] = []
        slot = 0
        for row_index in range(rows):
            rim = self._row_rim(row_index, rows)
            for direction, side in SIDES:
                for column in range(columns):
                    slot += 1
                    out.append({
                        "slot": slot,
                        "x": round(self.x_first + column * self.x_pitch, 2),
                        "z": round(rim + self.drop_lift, 2),   # cao do khay khi do
                        "rack_z": round(rim, 2),               # cao do mieng ro
                        "dir": direction,
                        "row": row_index,
                        "column": column,
                        "side": side,
                    })
        return out

    # Tra ve (x, z, chieu lat) cua mot ro.
    def slot_position(self, slot: int) -> tuple[float, float, int]:
        for row in self.all_positions():
            if row["slot"] == slot:
                return row["x"], row["z"], row["dir"]
        raise ValueError(f"so khay phai trong khoang 1..{self.slot_count}")

    # --------------------------------------------------------------- doi chieu

    # Dung de kiem tra tay: 1 mm can bao nhieu xung.
    def pulses_per_mm(self, axis: str) -> float:
        if axis == "x":
            return self.x_pulses_per_rev / self.x_mm_per_rev
        if axis == "z":
            return self.z_pulses_per_rev / self.z_mm_per_rev
        raise ValueError("truc phai la 'x' hoac 'z'")

    def pulses_per_degree(self) -> float:
        return self.y_pulses_per_rev / self.y_deg_per_rev

    # Tong so xung de chay het hanh trinh - de doi chieu voi kha nang driver.
    def pulses_for_full_travel(self, axis: str) -> int:
        if axis == "y":
            return round(self.pulses_per_degree() * self.y_max_angle * 2)
        travel = self.x_travel if axis == "x" else self.z_travel
        return round(self.pulses_per_mm(axis) * travel)

    # Toc do tran cua truc, quy doi tu tan so xung toi da cua dong co.
    #
    # Bo trong max_frequency_hz thi lay MAX_PULSE_HZ da do duoc; truyen vao khi
    # muon thu mot tan so khac (vi du doi chieu voi tran 100 kHz cua kenh PTO).
    def max_velocity(self, axis: str, max_frequency_hz: float | None = None) -> float:
        if max_frequency_hz is None:
            max_frequency_hz = MAX_PULSE_HZ
        if axis == "y":
            return max_frequency_hz / self.pulses_per_degree()
        return max_frequency_hz / self.pulses_per_mm(axis)

    # ------------------------------------------------------------- kiem tra

    # Nhung cho cau hinh tu mau thuan. Rong = khong co van de.
    #
    # Kiem o server thay vi de PLC bao loi luc dang chay giua chung.
    def problems(self) -> list[str]:
        issues: list[str] = []

        if self.layout()["slots"] == 0:
            issues.append("hanh trinh khong du de xep noi mot cai ro nao")
            return issues

        for pos in self.all_positions():
            if not 0.0 <= pos["x"] <= self.x_travel:
                issues.append(
                    f"khay {pos['slot']}: X = {pos['x']} mm vuot hanh trinh 0..{self.x_travel}")
            if not 0.0 <= pos["z"] <= self.z_travel:
                issues.append(
                    f"khay {pos['slot']}: Z = {pos['z']} mm vuot hanh trinh 0..{self.z_travel}")

        if not 0.0 <= self.park_x <= self.x_travel:
            issues.append(f"vi tri cho X = {self.park_x} mm vuot hanh trinh 0..{self.x_travel}")
        if not 0.0 <= self.park_z <= self.z_travel:
            issues.append(f"vi tri cho Z = {self.park_z} mm vuot hanh trinh 0..{self.z_travel}")
        if abs(self.park_y) > self.y_max_angle:
            issues.append(f"vi tri cho Y = {self.park_y} do vuot gioi han +-{self.y_max_angle}")

        if self.tilt_angle > self.y_max_angle:
            issues.append(
                f"goc lat {self.tilt_angle} do lon hon gioi han {self.y_max_angle} do")

        issues.extend(self.velocity_limits())
        issues.extend(self.tilt_clearance())
        issues.extend(self.travel_clearance())
        issues.extend(self.reach_clearance())
        return issues

    # Toc do co vuot tran cua Technology Object trong TIA khong.
    #
    # Bat o day de nguoi dung sua lai con so, thay vi de PLC nhan roi chet giua
    # chung: MC_MoveAbsolute tra ErrorID 16#8402 "Velocity khong hop le", FB nhay
    # buoc 900 va may dung im cho lenh Reset. Co ghi chu san o 04_FB_XY_Tray.scl.
    #
    # write_geometry chi day xuong PLC khi problems() rong, nen gia tri qua tran
    # van duoc luu de sua tiep nhung may giu nguyen toc do cu.
    def velocity_limits(self) -> list[str]:
        issues: list[str] = []
        for axis, ten, toc_do, don_vi, moi in (
            ("x", "X", self.vel_x, "mm/s", "xung/mm"),
            ("z", "Z", self.vel_z, "mm/s", "xung/mm"),
            ("y", "Y", self.tilt_vel, "do/s", "xung/do"),
        ):
            tran = self.max_velocity(axis)
            if toc_do > tran:
                moi_don_vi = (self.pulses_per_degree() if axis == "y"
                              else self.pulses_per_mm(axis))
                issues.append(
                    f"{ten}: toc do {toc_do:g} {don_vi} vuot tran {tran:.1f} {don_vi} "
                    f"({MAX_PULSE_HZ:g} xung/s / {moi_don_vi:g} {moi}) - "
                    f"truc se bao loi 16#8402 va may dung tai cho")
        return issues

    # Mep khay co voi toi mieng ro khong.
    #
    # Khay lat quanh truc nam giua ray, nen mep ngoai cua no chi vuon ra duoc
    # tray_width/2 tinh tu tam ray. Neu chua toi mep trong cua ro (rack_offset)
    # thi vat truot khoi khay se roi vao KHE giua ray va ro, khong vao ro.
    #
    # Khong dinh dang gi toi tilt_clearance: cai kia lo mep khay dam vao thanh
    # ro khi lat, cai nay lo khay ngan qua nen khong voi toi.
    def reach_clearance(self) -> list[str]:
        reach = self.tray_width / 2.0
        if reach >= self.rack_offset:
            return []
        return [
            f"khay rong {self.tray_width:g} mm nen mep chi voi ra {reach:.0f} mm, "
            f"trong khi mep ro o {self.rack_offset:g} mm - vat se roi vao khe giua "
            f"ray va ro. Noi khay rong len it nhat {self.rack_offset * 2:.0f} mm "
            f"hoac keo ro vao gan hon"
        ]

    # Kiem tra khi lat, mep khay co va vao thanh ro khong.
    #
    # Khay lat quanh truc nam doc theo X. Mep ngoai cach tam khay tray_width/2,
    # nen khi nghieng goc t no:
    # - vuon ra duoc  (tray_width/2) * cos(t)  tinh tu tam ray
    # - tut xuong     (tray_width/2) * sin(t)  so voi cao do khay dang dung
    # Neu mep tut xuong thap hon mieng ro MA van chua vuot qua thanh ro thi
    # no dang cham vao thanh - phai nang drop_lift len hoac keo ro ra xa.
    def tilt_clearance(self) -> list[str]:
        half = self.tray_width / 2.0
        rad = math.radians(self.tilt_angle)
        drop = half * math.sin(rad)
        reach = half * math.cos(rad)

        if drop <= self.drop_lift or reach >= self.rack_offset:
            return []

        return [
            f"lat {self.tilt_angle:g} do thi mep khay tut xuong {drop:.0f} mm "
            f"trong khi chi cach ray {reach:.0f} mm (thanh ro o {self.rack_offset:g} mm) - "
            f"nang 'khay cao hon mieng ro' len it nhat {drop:.0f} mm hoac keo ro ra xa hon"
        ]

    # Khay chay ngang co lot duoi day ro hang tren khong.
    #
    # row_pitch da chua san khe ho nay, nen ham chi con la luoi an toan phong
    # khi ai do sua cach tinh buoc hang ma quen mat rang buoc nay.
    def travel_clearance(self) -> list[str]:
        plan = self.layout()
        if plan["rows"] < 2:
            return []

        tray_top = self.z_first + self.drop_lift
        underside = self._row_rim(plan["rows"] - 2, plan["rows"]) - self.basket_height
        gap = underside - tray_top

        if gap >= MIN_TRAVEL_GAP:
            return []
        how = (f"khay chay ngang o cao do {tray_top:.0f} mm trong khi day ro hang tren "
               f"o {underside:.0f} mm")
        if gap < 0:
            return [f"{how} - DAM NHAU {abs(gap):.0f} mm"]
        return [f"{how} - chi ho {gap:.0f} mm, nen de it nhat {MIN_TRAVEL_GAP:.0f} mm"]
