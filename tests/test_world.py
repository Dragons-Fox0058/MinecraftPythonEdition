"""tests/test_world.py — World/Chunk/ChunkProvider tests."""
import unittest
from engine.core import BlockPos, AxisAlignedBB
from engine.world import World, Chunk, ChunkProvider
import engine.blocks.vanilla_blocks as VB


class TestChunk(unittest.TestCase):
    def test_empty_chunk(self):
        c = Chunk.__new__(Chunk)
        from engine.core import ChunkPos
        c = Chunk(ChunkPos(0, 0))
        self.assertEqual(c.get_block_state_id(0, 0, 0), 0)
        self.assertFalse(c.dirty)

    def test_set_get_local(self):
        c = Chunk.__new__(Chunk)
        from engine.core import ChunkPos
        c = Chunk(ChunkPos(0, 0))
        c.set_block_state_id(3, 64, 7, 1)  # stone
        self.assertEqual(c.get_block_state_id(3, 64, 7), 1)
        self.assertTrue(c.dirty)

    def test_light_packing(self):
        from engine.core import ChunkPos
        c = Chunk(ChunkPos(0, 0))
        c.set_sky_light(0, 10, 0, 15)
        c.set_block_light(0, 10, 0, 7)
        self.assertEqual(c.get_sky_light(0, 10, 0), 15)
        self.assertEqual(c.get_block_light(0, 10, 0), 7)
        # Set sky, ensure block preserved
        c.set_sky_light(0, 10, 0, 5)
        self.assertEqual(c.get_sky_light(0, 10, 0), 5)
        self.assertEqual(c.get_block_light(0, 10, 0), 7)

    def test_fill_layer(self):
        from engine.core import ChunkPos
        c = Chunk(ChunkPos(0, 0))
        c.fill_layer(0, 7)  # bedrock layer
        for x in range(16):
            for z in range(16):
                self.assertEqual(c.get_block_state_id(x, 0, z), 7)


class TestChunkProvider(unittest.TestCase):
    def test_get_or_create(self):
        p = ChunkProvider()
        c1 = p.get_or_create(0, 0)
        c2 = p.get_or_create(0, 0)
        self.assertIs(c1, c2)
        self.assertEqual(len(p), 1)

    def test_multiple_chunks(self):
        p = ChunkProvider()
        p.get_or_create(0, 0)
        p.get_or_create(1, 0)
        p.get_or_create(0, 1)
        self.assertEqual(len(p), 3)

    def test_unload(self):
        p = ChunkProvider()
        p.get_or_create(5, 5)
        self.assertTrue(p.has_chunk(5, 5))
        p.unload(5, 5)
        self.assertFalse(p.has_chunk(5, 5))


class TestWorld(unittest.TestCase):
    def test_block_in_same_chunk(self):
        w = World()
        p = BlockPos(0, 64, 0)
        w.set_block_state_id(p, 1)  # stone
        self.assertEqual(w.get_block_state_id(p), 1)
        self.assertFalse(w.is_air(p))

    def test_block_across_chunks(self):
        w = World()
        p1 = BlockPos(0, 64, 0)
        p2 = BlockPos(16, 64, 0)  # different chunk
        w.set_block_state_id(p1, 1)
        w.set_block_state_id(p2, 2)
        self.assertEqual(w.get_block_state_id(p1), 1)
        self.assertEqual(w.get_block_state_id(p2), 2)

    def test_negative_coords(self):
        w = World()
        p = BlockPos(-1, 64, -1)
        w.set_block_state_id(p, 3)
        self.assertEqual(w.get_block_state_id(p), 3)
        self.assertEqual(w.get_block_state_id(BlockPos(-1, 64, -1)), 3)

    def test_out_of_bounds_y(self):
        w = World()
        self.assertEqual(w.get_block_state_id(BlockPos(0, -1, 0)), 0)
        self.assertEqual(w.get_block_state_id(BlockPos(0, 256, 0)), 0)
        # Setting out-of-bounds is silently ignored
        w.set_block_state_id(BlockPos(0, -1, 0), 5)
        self.assertEqual(w.get_block_state_id(BlockPos(0, -1, 0)), 0)

    def test_get_block_state(self):
        w = World()
        w.set_block_state_id(BlockPos(0, 64, 0), 1)  # stone
        st = w.get_block_state(BlockPos(0, 64, 0))
        self.assertIs(st.block, VB.STONE)

    def test_sky_light_default(self):
        w = World()
        # Uninitialized chunk has 0 sky light; we may want 15 above ground later.
        self.assertEqual(w.get_sky_light(BlockPos(0, 64, 0)), 0)

    def test_combined_light(self):
        w = World()
        w.chunk_provider.get_or_create(0, 0).set_sky_light(0, 64, 0, 15)
        w.chunk_provider.get_or_create(0, 0).set_block_light(0, 64, 0, 3)
        self.assertEqual(w.get_combined_light(BlockPos(0, 64, 0)), 15)

    def test_collision_boxes_empty(self):
        w = World()
        aabb = AxisAlignedBB(0, 64, 0, 1, 65, 1)
        self.assertEqual(len(w.get_collision_boxes(aabb)), 0)

    def test_collision_boxes_with_stone(self):
        w = World()
        w.set_block_state_id(BlockPos(0, 64, 0), 1)  # stone
        aabb = AxisAlignedBB(0, 64, 0, 1, 65, 1)
        boxes = w.get_collision_boxes(aabb)
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].min_x, 0.0)
        self.assertEqual(boxes[0].max_x, 1.0)

    def test_collision_boxes_with_air(self):
        w = World()
        aabb = AxisAlignedBB(0, 64, 0, 1, 65, 1)
        self.assertEqual(len(w.get_collision_boxes(aabb)), 0)

    def test_world_bounds(self):
        w = World()
        self.assertTrue(w.is_in_world_bounds(0))
        self.assertTrue(w.is_in_world_bounds(255))
        self.assertFalse(w.is_in_world_bounds(-1))
        self.assertFalse(w.is_in_world_bounds(256))


if __name__ == '__main__':
    unittest.main()
