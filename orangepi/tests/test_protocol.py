# Test cho lop giao thuc. Chay duoc khong can PLC, khong can cai them thu vien.
#
# cd orangepi && python -m unittest discover -s tests -v
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.plc.protocol import (  # noqa: E402
    ADDR_STATUS_BLOCK,
    ADDR_WRITE_BLOCK,
    SIZE_STATUS_BLOCK,
    SIZE_WRITE_BLOCK,
    Command,
    CtrlBit,
    PlcStatus,
    Result,
    build_command_frame,
    decode_f32,
    encode_f32,
    next_seq,
)


# Real cua S7 phai la big-endian, word cao truoc.
class TestFloatEncoding(unittest.TestCase):
    def test_round_trip(self):
        for value in (0.0, 1.5, -273.25, 1100.0, 0.001):
            hi, lo = encode_f32(value)
            self.assertAlmostEqual(decode_f32(hi, lo), value, places=3)

    def test_word_order_matches_s7(self):
        # 1100.0 = 0x44898000 -> word cao 0x4489, word thap 0x8000
        hi, lo = encode_f32(1100.0)
        self.assertEqual((hi, lo), (0x4489, 0x8000))

    def test_decode_matches_struct(self):
        raw = struct.pack(">f", 250.75)
        hi, lo = struct.unpack(">HH", raw)
        self.assertAlmostEqual(decode_f32(hi, lo), 250.75, places=3)


class TestCommandFrame(unittest.TestCase):
    def test_frame_size_matches_write_block(self):
        frame = build_command_frame(Command.AUTO, 1, slot=5)
        self.assertEqual(len(frame), SIZE_WRITE_BLOCK)
        self.assertEqual(SIZE_WRITE_BLOCK, 10)
        self.assertEqual(ADDR_WRITE_BLOCK, 0)

    def test_field_order(self):
        frame = build_command_frame(Command.AUTO, 42, slot=5, x=1100.0, y=300.0, z=-15.0)
        command, slot, ctrl, seq, hi_x, lo_x, hi_y, lo_y, hi_z, lo_z = frame

        self.assertEqual(command, 1)
        self.assertEqual(slot, 5)
        self.assertEqual(seq, 42)
        self.assertEqual(ctrl & int(CtrlBit.AXES_ENABLE), 256)   # luon cap dien truc
        self.assertAlmostEqual(decode_f32(hi_x, lo_x), 1100.0, places=3)
        self.assertAlmostEqual(decode_f32(hi_y, lo_y), 300.0, places=3)
        self.assertAlmostEqual(decode_f32(hi_z, lo_z), -15.0, places=3)

    def test_jog_bits_have_expected_values(self):
        self.assertEqual(int(CtrlBit.JOG_X_POS), 1)
        self.assertEqual(int(CtrlBit.JOG_X_NEG), 2)
        self.assertEqual(int(CtrlBit.JOG_Y_POS), 4)
        self.assertEqual(int(CtrlBit.JOG_Y_NEG), 8)
        self.assertEqual(int(CtrlBit.JOG_Z_POS), 16)
        self.assertEqual(int(CtrlBit.JOG_Z_NEG), 32)
        self.assertEqual(int(CtrlBit.AXES_ENABLE), 256)


class TestSequence(unittest.TestCase):
    def test_increments(self):
        self.assertEqual(next_seq(0), 1)
        self.assertEqual(next_seq(41), 42)

    def test_never_returns_zero_on_wrap(self):
        self.assertEqual(next_seq(65535), 1)


class TestStatusParsing(unittest.TestCase):
    def _registers(self, bits=0, step=0, error_id=0, ack=0, done=0, result=0,
                   x=0.0, y=0.0, z=0.0, slot=0):
        hi_x, lo_x = encode_f32(x)
        hi_y, lo_y = encode_f32(y)
        hi_z, lo_z = encode_f32(z)
        return [bits, step, error_id, ack, done, result,
                hi_x, lo_x, hi_y, lo_y, hi_z, lo_z, slot, 0]

    def test_block_size_constant(self):
        self.assertEqual(len(self._registers()), SIZE_STATUS_BLOCK)
        self.assertEqual(SIZE_STATUS_BLOCK, 14)
        self.assertEqual(ADDR_STATUS_BLOCK, 10)

    def test_parses_ready_and_homed(self):
        # bit0 Ready + bit3 Homed = 1 + 8 = 9
        status = PlcStatus.from_registers(
            self._registers(bits=9, x=1100.0, y=300.0, z=-15.0, slot=5))
        self.assertTrue(status.ready)
        self.assertTrue(status.homed)
        self.assertFalse(status.busy)
        self.assertFalse(status.error)
        self.assertAlmostEqual(status.x, 1100.0, places=2)
        self.assertAlmostEqual(status.z, -15.0, places=2)
        self.assertEqual(status.slot, 5)

    def test_parses_busy_cycle(self):
        # bit1 Busy = 2
        status = PlcStatus.from_registers(
            self._registers(bits=2, step=110, ack=7, result=int(Result.RUNNING))
        )
        self.assertTrue(status.busy)
        self.assertEqual(status.step, 110)
        self.assertEqual(status.ack_seq, 7)
        self.assertEqual(status.result_text, "dang chay")

    def test_parses_error(self):
        # bit4 Error = 16
        status = PlcStatus.from_registers(
            self._registers(bits=16, error_id=0x8001, result=int(Result.ERROR))
        )
        self.assertTrue(status.error)
        self.assertEqual(status.to_dict()["error_id_hex"], "0x8001")

    def test_rejects_short_block(self):
        with self.assertRaises(ValueError):
            PlcStatus.from_registers([0, 0, 0])

    def test_to_dict_is_json_friendly(self):
        import json
        status = PlcStatus.from_registers(self._registers(bits=9, x=12.5, y=7.25, z=3.5))
        json.dumps(status.to_dict())   # khong duoc nem loi


if __name__ == "__main__":
    unittest.main()
