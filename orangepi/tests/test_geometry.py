# Test cho lop hinh hoc va ton kho. Chay khong can PLC.
#
# cd orangepi && python -m unittest discover -s tests -v
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.geometry import MAX_PLC_SLOTS, MAX_PULSE_HZ, Geometry  # noqa: E402
from app.inventory import (  # noqa: E402
    DEFAULT_CAPACITY,
    SLOT_COUNT,
    Inventory,
    SlotEmptyError,
    SlotFullError,
)


# Bang ro trong bo nho, dung dung nhung ham ma Inventory goi toi - nho vay test
# chay duoc khong can MySQL.
class FakeSlotTable:
    def __init__(self, slot_count=SLOT_COUNT, capacity=DEFAULT_CAPACITY):
        self._capacity = capacity
        self._rows = {
            n: {"slot": n, "code": "", "count": 0, "capacity": capacity, "updated_at": None}
            for n in range(1, slot_count + 1)
        }

    def all(self):
        return [dict(r) for r in self._rows.values()]

    def one(self, slot):
        row = self._rows.get(slot)
        return dict(row) if row else None

    def update(self, slot, **changes):
        if "code" in changes:
            changes["code"] = changes["code"].strip()
        self._rows[slot].update(changes)
        self._rows[slot]["updated_at"] = datetime.now().replace(microsecond=0).isoformat()

    def reset_all(self):
        for row in self._rows.values():
            row.update(code="", count=0, capacity=self._capacity, updated_at=None)


class TestGeometry(unittest.TestCase):
    def setUp(self):
        self.g = Geometry()
        self.cols = self.g.layout()["columns"]

    def test_numbering_is_dense_from_one(self):
        rows = self.g.all_positions()
        self.assertEqual([r["slot"] for r in rows], list(range(1, len(rows) + 1)))

    def test_first_block_goes_right(self):
        # Moi hang: het ben phai roi moi toi ben trai.
        for slot in range(1, self.cols + 1):
            _, _, direction = self.g.slot_position(slot)
            self.assertEqual(direction, +1, f"khay {slot} phai lat sang phai")

    def test_second_block_goes_left(self):
        for slot in range(self.cols + 1, 2 * self.cols + 1):
            _, _, direction = self.g.slot_position(slot)
            self.assertEqual(direction, -1, f"khay {slot} phai lat sang trai")

    def test_columns_step_by_the_pitch(self):
        first = self.g.slot_position(1)[0]
        self.assertEqual(first, self.g.x_first)
        self.assertEqual(self.g.slot_position(self.cols)[0],
                         first + (self.cols - 1) * self.g.x_pitch)

    def test_both_racks_share_the_same_x(self):
        # Hai day nam hai ben cung mot duong ray, chi khac chieu lat.
        for column in range(1, self.cols + 1):
            self.assertEqual(self.g.slot_position(column)[0],
                             self.g.slot_position(column + self.cols)[0])

    def test_tray_stops_above_the_basket_rim(self):
        # Toa do Z gui xuong PLC la do cao KHAY, phai cao hon mieng ro.
        for row in self.g.all_positions():
            self.assertEqual(row["z"], row["rack_z"] + self.g.drop_lift)

    def test_bottom_row_sits_at_the_declared_start(self):
        rows = self.g.all_positions()
        self.assertEqual(min(r["rack_z"] for r in rows), self.g.z_first)

    # ------------------------------------------------- so ro do may tu tinh
    def test_layout_is_computed_not_declared(self):
        plan = self.g.layout()
        self.assertEqual(plan["slots"], plan["rows"] * plan["columns"] * 2)
        self.assertEqual(len(self.g.all_positions()), plan["slots"])

    def test_taller_baskets_leave_room_for_fewer_rows(self):
        low = Geometry(basket_height=40.0).layout()["rows"]
        high = Geometry(basket_height=140.0).layout()["rows"]
        self.assertGreater(low, high)

    def test_longer_baskets_leave_room_for_fewer_columns(self):
        self.assertGreater(Geometry(basket_length=90.0).columns_that_fit(),
                           Geometry(basket_length=300.0).columns_that_fit())

    def test_layout_never_exceeds_the_plc_table(self):
        # Truc X du dai cho rat nhieu cot, nhung mang trong PLC co han.
        roomy = Geometry(x_travel=40_000.0)
        self.assertGreater(roomy.columns_that_fit(), roomy.layout()["columns"])
        self.assertLessEqual(roomy.slot_count, MAX_PLC_SLOTS)
        self.assertTrue(roomy.layout()["capped"])

    def test_longer_x_travel_fits_more_baskets(self):
        # Day la diem chinh: so ro khong co dinh, no bam theo hanh trinh.
        short = Geometry(x_travel=600.0).slot_count
        long = Geometry(x_travel=1300.0).slot_count
        self.assertGreater(long, short)

    def test_top_row_keeps_clear_of_the_z_limit(self):
        # Khay dung o hang tren khong duoc cham vach gioi han phan mem.
        highest = max(r["z"] for r in self.g.all_positions())
        self.assertLess(highest, self.g.z_travel)

    def test_no_room_means_no_slots(self):
        self.assertEqual(Geometry(z_travel=50.0, x_travel=50.0).slot_count, 0)
        self.assertTrue(Geometry(z_travel=50.0, x_travel=50.0).problems())

    def test_bigger_baskets_mean_fewer_columns(self):
        # So sanh hai cau hinh tu dung ra, khong dua vao so mac dinh - mac dinh
        # chi la bo so mau va co the doi bat cu luc nao.
        narrow = Geometry(basket_length=140.0, x_travel=2000.0)
        wide = Geometry(basket_length=290.0, x_travel=2000.0)

        self.assertEqual(narrow.min_pitch, 150.0)
        self.assertEqual(wide.min_pitch, 300.0)
        self.assertLess(wide.layout()["columns"], narrow.layout()["columns"])

    def test_last_basket_ends_flush_with_the_x_travel(self):
        # Phan du khong duoc don ve mot dau: trai deu ra cho ro cuoi cham mep.
        for g in (self.g,
                  Geometry(x_travel=2000.0),
                  Geometry(basket_length=140.0, x_travel=900.0)):
            xs = [r["x"] for r in g.all_positions()]
            self.assertAlmostEqual(max(xs) + g.basket_length / 2, g.x_travel, places=6)

    def test_columns_are_evenly_spaced(self):
        xs = sorted({r["x"] for r in self.g.all_positions()})
        steps = [round(b - a, 6) for a, b in zip(xs, xs[1:])]
        self.assertEqual(len(set(steps)), 1, "cac cot phai cach deu nhau")
        self.assertGreaterEqual(self.g.x_gap, self.g.basket_gap)

    def test_spreading_never_goes_below_the_minimum_gap(self):
        # Hanh trinh vua khit thi khong con gi de trai - buoc phai ve dung muc chat nhat.
        tight = Geometry(basket_length=200.0, x_travel=310.0)
        self.assertEqual(tight.layout()["columns"], 1)
        self.assertGreaterEqual(tight.x_gap, tight.basket_gap)

    # ------------------------------------------------- ba phep kiem va cham
    def test_short_tray_cannot_reach_the_basket(self):
        # Khay hep qua thi vat truot ra roi vao khe giua ray va ro.
        self.assertTrue(Geometry(tray_width=140.0, rack_offset=95.0).reach_clearance())
        self.assertFalse(self.g.reach_clearance())

    def test_pulling_the_rack_closer_fixes_a_short_tray(self):
        self.assertFalse(Geometry(tray_width=140.0, rack_offset=65.0).reach_clearance())

    def test_low_tray_would_scrape_the_basket_wall(self):
        # Lat 60 do voi khay rong 200 lam mep tut xuong 87 mm.
        self.assertTrue(Geometry(drop_lift=10.0).tilt_clearance())
        self.assertFalse(self.g.tilt_clearance())

    def test_row_pitch_keeps_the_tray_clear_when_travelling(self):
        # Buoc hang da chua san khe ho nay nen bo cuc tu tinh khong bao gio dinh.
        self.assertFalse(self.g.travel_clearance())
        for bh in (40.0, 60.0, 90.0, 140.0):
            self.assertFalse(Geometry(basket_height=bh).travel_clearance(),
                             f"thanh ro {bh} mm khong duoc gay va cham")

    def test_a_sane_config_reports_nothing(self):
        self.assertEqual(self.g.problems(), [])

    def test_invalid_slot(self):
        with self.assertRaises(ValueError):
            self.g.slot_position(self.g.slot_count + 1)

    def test_pulses_and_velocity(self):
        # 3200 xung/vong, 32 mm/vong -> 100 xung/mm
        self.assertAlmostEqual(self.g.pulses_per_mm("x"), 100.0)
        # 100 kHz / 100 = 1000 mm/s - tran ly thuyet cua kenh PTO, khong phai dong co
        self.assertAlmostEqual(self.g.max_velocity("x", 100_000), 1000.0, places=2)
        # truc lat: 1000 xung/vong, 360 do/vong -> 2.778 xung/do
        self.assertAlmostEqual(self.g.pulses_per_degree(), 1000 / 360)

    # Bo tan so di thi lay MAX_PULSE_HZ - toc do cao nhat dong co con keo noi,
    # do bang tay o che do phat xung. Day moi la con so quyet dinh.
    def test_max_velocity_comes_from_the_measured_pulse_rate(self):
        self.assertEqual(MAX_PULSE_HZ, 20_000.0)
        # X: 20 000 / 100 xung/mm = 200 mm/s
        self.assertAlmostEqual(self.g.max_velocity("x"), 200.0, places=2)
        # Z: 2000 xung/vong, 54 mm/vong -> 37.04 xung/mm -> 540 mm/s
        self.assertAlmostEqual(self.g.max_velocity("z"), 540.0, places=1)
        # Y: 20 000 / 2.778 xung/do = 7200 do/s
        self.assertAlmostEqual(self.g.max_velocity("y"), 7200.0, places=1)

        # Vi buoc thua hon thi cung tan so xung do cho toc do cao hon.
        thua = Geometry(x_mm_per_rev=64.0)
        self.assertAlmostEqual(thua.max_velocity("x"), 400.0, places=2)

    # Vuot tran thi truc tu choi lenh chay va may dung tai cho, nen chan tu server.
    def test_velocity_over_the_axis_ceiling_is_reported(self):
        self.assertEqual(Geometry(vel_x=200.0).velocity_limits(), [])

        qua = Geometry(vel_x=300.0)
        loi = qua.velocity_limits()
        self.assertEqual(len(loi), 1)
        self.assertIn("300", loi[0])
        self.assertIn("200.0", loi[0])
        self.assertIn("16#8402", loi[0])
        # problems() phai keo theo, vi write_geometry dua vao no de chan day xuong PLC.
        self.assertIn(loi[0], qua.problems())

    def test_tilt_velocity_has_the_same_ceiling(self):
        qua = Geometry(y_pulses_per_rev=100_000, tilt_vel=200.0)
        self.assertEqual(len(qua.velocity_limits()), 1)
        self.assertTrue(qua.velocity_limits()[0].startswith("Y:"))

    def test_round_trip_dict(self):
        data = self.g.to_dict()
        again = Geometry.from_dict(data)
        self.assertEqual(again.to_dict(), data)

    def test_from_dict_ignores_unknown_keys(self):
        g = Geometry.from_dict({"basket_length": 120.0, "rac": "bo qua"})
        self.assertEqual(g.basket_length, 120.0)


class TestInventory(unittest.TestCase):
    def setUp(self):
        self.table = FakeSlotTable()
        self.inv = Inventory(self.table)

    def test_starts_empty(self):
        count = len(self.inv.slots)
        self.assertGreater(count, 0)
        self.assertEqual(self.inv.summary()["total_items"], 0)
        self.assertEqual(self.inv.summary()["empty_slots"], count)

    def test_shrinking_reports_baskets_left_holding_items(self):
        self.inv.add_item(9, 3)
        self.inv.add_item(2, 1)

        orphans = self.inv.stock_beyond(8)          # bo cuc moi chi con 8 ro
        self.assertEqual([o["slot"] for o in orphans], [9])
        self.assertEqual(orphans[0]["count"], 3)

        # Ro con nam trong bo cuc thi khong phai canh bao.
        self.assertEqual(self.inv.stock_beyond(20), [])

    def test_shrinking_does_not_destroy_stock(self):
        self.inv.add_item(9, 3)
        self.inv.set_active(8)
        self.assertEqual(len(self.inv.slots), 8)
        self.inv.set_active(20)                     # noi lai
        self.assertEqual(self.inv.slot(9)["count"], 3)

    def test_active_count_hides_unused_rows(self):
        # Bo cuc quyet dinh co bao nhieu ro that su - phan con lai nam cho san.
        self.inv.set_active(6)
        self.assertEqual(len(self.inv.slots), 6)
        self.assertEqual(self.inv.summary()["slot_count"], 6)

    def test_add_and_remove(self):
        self.inv.add_item(3, 2)
        self.assertEqual(self.inv.slot(3)["count"], 2)
        self.inv.remove_item(3)
        self.assertEqual(self.inv.slot(3)["count"], 1)

    def test_cannot_overfill(self):
        self.inv.set_capacity(4, 2)
        self.inv.add_item(4, 2)
        with self.assertRaises(SlotFullError):
            self.inv.add_item(4)

    def test_cannot_go_negative(self):
        with self.assertRaises(SlotEmptyError):
            self.inv.remove_item(5)

    def test_code_lookup(self):
        self.inv.assign_code(7, "SP-001")
        self.assertEqual(self.inv.find_slot_for_code("SP-001"), 7)
        self.assertEqual(self.inv.find_slot_for_code("sp-001"), 7)   # khong phan biet hoa thuong
        self.assertIsNone(self.inv.find_slot_for_code("KHONG-CO"))

    def test_first_free_slot_skips_full(self):
        self.inv.set_capacity(1, 1)
        self.inv.add_item(1)
        self.assertEqual(self.inv.first_free_slot(), 2)

    def test_summary_counts_full(self):
        self.inv.set_capacity(2, 1)
        self.inv.add_item(2)
        s = self.inv.summary()
        self.assertEqual(s["full_slots"], 1)
        self.assertEqual(s["total_items"], 1)

    def test_survives_restart(self):
        self.inv.assign_code(9, "ABC")
        self.inv.add_item(9, 3)
        again = Inventory(self.table)          # doc lai tu cung mot kho
        self.assertEqual(again.slot(9)["code"], "ABC")
        self.assertEqual(again.slot(9)["count"], 3)

    def test_reset_clears(self):
        self.inv.add_item(1, 2)
        self.inv.reset()
        self.assertEqual(self.inv.summary()["total_items"], 0)

    def test_invalid_slot(self):
        with self.assertRaises(ValueError):
            self.inv.add_item(0)


if __name__ == "__main__":
    unittest.main()
