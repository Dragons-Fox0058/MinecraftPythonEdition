"""Anvil region file tests."""
import tempfile
import unittest
from pathlib import Path

from engine.core.nbt import NBTDocument
from engine.persistence.region import RegionFile, RegionError, region_coordinates


class TestRegionFile(unittest.TestCase):
    def test_chunk_round_trip_and_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "r.0.0.mca"
            region = RegionFile(path)
            doc = NBTDocument("", {"Level": {"xPos": 3, "zPos": -2, "Status": "full"}})
            region.write_chunk(3, 30, doc, timestamp=123456)
            self.assertEqual(region.read_chunk(3, 30), doc)
            raw = path.read_bytes()
            index = 3 + 30 * 32
            import struct
            self.assertEqual(struct.unpack_from(">I", raw, 4096 + index * 4)[0], 123456)

    def test_multiple_slots_survive_compaction(self):
        with tempfile.TemporaryDirectory() as directory:
            region = RegionFile(Path(directory) / "r.0.0.mca")
            first = NBTDocument("", {"v": "first"})
            second = NBTDocument("", {"v": "second"})
            region.write_chunk(0, 0, first, timestamp=1)
            region.write_chunk(31, 31, second, timestamp=2)
            region.write_chunk(0, 0, NBTDocument("", {"v": "updated"}), timestamp=3)
            self.assertEqual(region.read_chunk(0, 0).value["v"], "updated")
            self.assertEqual(region.read_chunk(31, 31), second)

    def test_missing_slot_and_file(self):
        with tempfile.TemporaryDirectory() as directory:
            region = RegionFile(Path(directory) / "missing.mca")
            self.assertIsNone(region.read_chunk(0, 0))
            region.write_chunk(2, 4, {"x": 1}, timestamp=0)
            self.assertIsNone(region.read_chunk(0, 0))

    def test_rejects_invalid_coordinates_and_truncated_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.mca"
            path.write_bytes(b"short")
            with self.assertRaises(RegionError):
                RegionFile(path).read_chunk(0, 0)
            with self.assertRaises(ValueError):
                RegionFile(path).read_chunk(32, 0)

    def test_region_coordinates_for_negative_chunks(self):
        self.assertEqual(region_coordinates(-1, -1), (-1, -1, 1023))
        self.assertEqual(region_coordinates(32, 64), (1, 2, 0))


if __name__ == "__main__":
    unittest.main()
