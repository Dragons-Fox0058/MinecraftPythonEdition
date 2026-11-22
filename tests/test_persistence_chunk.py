"""1.12.2 chunk NBT round-trip tests."""
import unittest

from engine.core import ChunkPos, NBTList, TAG_COMPOUND
from engine.world.chunk import Chunk
from engine.persistence.chunk import chunk_from_nbt, chunk_to_nbt


class TestChunkPersistence(unittest.TestCase):
    def test_sparse_and_extended_block_ids_round_trip(self):
        chunk = Chunk(ChunkPos(-3, 7))
        chunk.blocks[1, 2, 3] = (54 << 4) | 5
        chunk.blocks[15, 15, 255] = (300 << 4) | 12
        chunk.light[1, 2, 3] = 0xA7
        chunk.light[15, 15, 255] = 0xF3
        restored = chunk_from_nbt(chunk_to_nbt(chunk))
        self.assertEqual(restored.pos, chunk.pos)
        self.assertEqual(int(restored.blocks[1, 2, 3]), (54 << 4) | 5)
        self.assertEqual(int(restored.blocks[15, 15, 255]), (300 << 4) | 12)
        self.assertEqual(int(restored.light[1, 2, 3]), 0xA7)
        self.assertEqual(int(restored.light[15, 15, 255]), 0xF3)
        self.assertFalse(restored.dirty)

    def test_empty_chunk_has_valid_empty_sections(self):
        chunk = Chunk(ChunkPos(0, 0))
        document = chunk_to_nbt(chunk)
        self.assertIsInstance(document.value["Level"]["Sections"], NBTList)
        self.assertEqual(document.value["Level"]["Sections"].tag_type, TAG_COMPOUND)
        restored = chunk_from_nbt(document)
        self.assertEqual(int(restored.blocks.sum()), 0)

    def test_rejects_wrong_expected_coordinates(self):
        chunk = Chunk(ChunkPos(2, 3))
        with self.assertRaises(ValueError):
            chunk_from_nbt(chunk_to_nbt(chunk), expected_pos=ChunkPos(2, 4))


if __name__ == "__main__":
    unittest.main()
