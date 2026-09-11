# Duong SSE va duong phat ban app. Khong can PLC, khong can MySQL.
import json
import unittest
from unittest import mock

from app.api import appdist
from app.api.sse import frame


class TestFrame(unittest.TestCase):
    def test_dung_dinh_dang_su_kien(self):
        out = frame("status", {"online": True})
        self.assertEqual(out, 'event: status\ndata: {"online": true}\n\n')

    def test_ket_thuc_bang_dong_trong(self):
        # Thieu dong trong la trinh doc SSE khong biet ban tin da het.
        self.assertTrue(frame("layout", {}).endswith("\n\n"))

    def test_giu_nguyen_tieng_viet(self):
        out = frame("layout", {"note": "hàng dưới cùng"})
        self.assertIn("hàng dưới cùng", out)

    def test_khong_xuong_dong_giua_ban_tin(self):
        # Mot dong "data:" duy nhat. Xuong dong giua chung la vo khung ban tin.
        out = frame("status", {"loi": "mat\nket noi"})
        self.assertEqual(out.count("\n"), 3)

    def test_kieu_la_thi_doi_ra_chuoi_chu_khong_no(self):
        import datetime
        out = frame("inventory", {"updated_at": datetime.date(2026, 8, 26)})
        self.assertIn("2026-08-26", json.loads(out.split("data: ", 1)[1]).values())


class TestAppDist(unittest.TestCase):
    def _manifest(self, data):
        return mock.patch.object(appdist, "_manifest", return_value=data)

    def test_to_khai_chi_ten_file_khong_lay_duong_dan(self):
        # To khai bi sua bay cung khong doc duoc file ngoai thu muc updates.
        from fastapi import HTTPException

        with self._manifest({"file": "../../../etc/passwd"}):
            with self.assertRaises(HTTPException) as caught:
                import asyncio
                asyncio.run(appdist.download())
        self.assertEqual(caught.exception.status_code, 404)

    def test_thieu_file_thi_bao_404_chu_khong_do(self):
        from fastapi import HTTPException

        with self._manifest({"file": "khong-co-that.apk"}):
            with self.assertRaises(HTTPException) as caught:
                import asyncio
                asyncio.run(appdist.download())
        self.assertEqual(caught.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
