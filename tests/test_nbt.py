"""NBT codec round-trip and malformed-input tests."""
import unittest
import struct

from engine.core.nbt import (
    NBTDocument, NBTError, NBTList, read_nbt, write_nbt,
    TAG_BYTE, TAG_INT, TAG_COMPOUND, TAG_STRING,
)


class TestNBTCodec(unittest.TestCase):
    def test_round_trip_nested_java_tags(self):
        doc = NBTDocument("root", {
            "byte": 7,
            "short": 300,
            "int": 70000,
            "long": 1 << 40,
            "float": 1.25,
            "double": 3.5,
            "string": "Minecraft 1.12.2",
            "bytes": bytes([0, 1, 127, 128, 255]),
            "ints": (1, -2, 3),
            "list": NBTList(TAG_STRING, ("stone", "dirt")),
            "nested": {"health": 20, "name": "Steve"},
        })
        encoded = write_nbt(doc)
        decoded = read_nbt(encoded)
        self.assertEqual(decoded.name, "root")
        self.assertEqual(decoded.value["string"], "Minecraft 1.12.2")
        self.assertEqual(decoded.value["bytes"], bytes([0, 1, 127, 128, 255]))
        self.assertEqual(decoded.value["list"], NBTList(TAG_STRING, ("stone", "dirt")))
        self.assertEqual(decoded.value["nested"]["health"], 20)

    def test_gzip_and_zlib_compression(self):
        doc = NBTDocument("", {"value": 42})
        self.assertEqual(read_nbt(write_nbt(doc, compression="gzip"), compression="gzip").value["value"], 42)
        self.assertEqual(read_nbt(write_nbt(doc, compression="zlib"), compression="zlib").value["value"], 42)

    def test_rejects_bad_root_truncation_and_trailing_data(self):
        with self.assertRaises(NBTError):
            read_nbt(b"")
        with self.assertRaises(NBTError):
            read_nbt(b"\x03\x00\x00")
        valid = write_nbt({"x": 1})
        with self.assertRaises(NBTError):
            read_nbt(valid[:-1])
        with self.assertRaises(NBTError):
            read_nbt(valid + b"x")

    def test_rejects_duplicate_keys_and_invalid_list(self):
        duplicate = b"\x0a\x00\x00" + b"\x03\x00\x01x\x00\x00\x00\x01" + b"\x03\x00\x01x\x00\x00\x00\x02\x00"
        with self.assertRaises(NBTError):
            read_nbt(duplicate)
        invalid_list = b"\x0a\x00\x00\x09\x00\x01x\x00\x00\x00\x01\x00"
        with self.assertRaises(NBTError):
            read_nbt(invalid_list)

    def test_depth_and_size_limits(self):
        with self.assertRaises(NBTError):
            read_nbt(write_nbt({"a": {"b": 1}}), max_depth=0)
        with self.assertRaises(NBTError):
            read_nbt(write_nbt({"long": "x" * 20}), max_bytes=8)

    def test_int_array_type_is_preserved_by_tag(self):
        # Explicitly write a compound with a TAG_INT_ARRAY payload.
        payload = (b"\x0a\x00\x00\x0b\x00\x01a\x00\x00\x00\x02"
                   b"\x00\x00\x00\x05\xff\xff\xff\xfe\x00")
        decoded = read_nbt(payload)
        self.assertEqual(decoded.value["a"], (5, -2))


if __name__ == "__main__":
    unittest.main()
