"""tests/test_core.py — Unit tests for engine.core primitives."""

import unittest
from engine.core import (
    BlockPos, ChunkPos, Vec3d, Vec3i, EnumFacing,
    AxisAlignedBB, JavaRandom, java_string_hash,
)

class TestEnumFacing(unittest.TestCase):
    def test_opposite(self):
        self.assertEqual(EnumFacing.DOWN.opposite, EnumFacing.UP)
        self.assertEqual(EnumFacing.NORTH.opposite, EnumFacing.SOUTH)
        self.assertEqual(EnumFacing.WEST.opposite, EnumFacing.EAST)

    def test_axis(self):
        self.assertEqual(EnumFacing.UP.axis, 'Y')
        self.assertEqual(EnumFacing.NORTH.axis, 'Z')
        self.assertEqual(EnumFacing.EAST.axis, 'X')

    def test_offset(self):
        self.assertEqual(EnumFacing.UP.offset, (0, 1, 0))
        self.assertEqual(EnumFacing.NORTH.offset, (0, 0, -1))

    def test_rotate_y(self):
        self.assertEqual(EnumFacing.NORTH.rotate_y(), EnumFacing.EAST)
        self.assertEqual(EnumFacing.EAST.rotate_y(), EnumFacing.SOUTH)
        self.assertEqual(EnumFacing.SOUTH.rotate_y(), EnumFacing.WEST)
        self.assertEqual(EnumFacing.WEST.rotate_y(), EnumFacing.NORTH)

class TestBlockPos(unittest.TestCase):
    def test_chunk_coords(self):
        self.assertEqual(BlockPos(0, 64, 0).chunk_x, 0)
        self.assertEqual(BlockPos(15, 64, 15).chunk_x, 0)
        self.assertEqual(BlockPos(16, 64, 16).chunk_x, 1)
        self.assertEqual(BlockPos(-1, 64, -1).chunk_x, -1)
        self.assertEqual(BlockPos(-16, 64, -16).chunk_x, -1)
        self.assertEqual(BlockPos(-17, 64, -17).chunk_x, -2)

    def test_offset_facing(self):
        p = BlockPos(10, 64, 10)
        self.assertEqual(p.offset(EnumFacing.UP), BlockPos(10, 65, 10))
        self.assertEqual(p.offset(EnumFacing.NORTH), BlockPos(10, 64, 9))

    def test_chunkpos_long_roundtrip(self):
        for pos in [ChunkPos(0,0), ChunkPos(1,2), ChunkPos(-100, 200)]:
            self.assertEqual(ChunkPos.from_long(pos.as_long()), pos)

class TestVec3d(unittest.TestCase):
    def test_add_sub(self):
        a = Vec3d(1, 2, 3); b = Vec3d(4, 5, 6)
        self.assertEqual(a + b, Vec3d(5, 7, 9))
        self.assertEqual(b - a, Vec3d(3, 3, 3))

    def test_dot_cross(self):
        a = Vec3d(1, 0, 0); b = Vec3d(0, 1, 0)
        self.assertEqual(a.dot(b), 0)
        self.assertEqual(a.cross(b), Vec3d(0, 0, 1))

    def test_length(self):
        self.assertAlmostEqual(Vec3d(3, 4, 0).length(), 5.0)

class TestAABB(unittest.TestCase):
    def test_intersects(self):
        a = AxisAlignedBB(0, 0, 0, 1, 1, 1)
        b = AxisAlignedBB(0.5, 0.5, 0.5, 1.5, 1.5, 1.5)
        c = AxisAlignedBB(2, 2, 2, 3, 3, 3)
        self.assertTrue(a.intersects(b))
        self.assertFalse(a.intersects(c))

    def test_contains(self):
        a = AxisAlignedBB(0, 0, 0, 1, 1, 1)
        self.assertTrue(a.contains(Vec3d(0.5, 0.5, 0.5)))
        self.assertFalse(a.contains(Vec3d(2, 2, 2)))

    def test_x_offset_blocks_full_approach(self):
        # A at (0..1), B at (2..3), moving A by +2: vanilla returns 2.0
        # because B.maxX=3 > A.minX=0 (condition other.maxX <= minX fails).
        a = AxisAlignedBB(0, 0, 0, 1, 1, 1)
        b = AxisAlignedBB(2, 0, 0, 3, 1, 1)
        self.assertAlmostEqual(a.calculate_x_offset(b, 2.0), 2.0)

    def test_x_offset_blocked_by_other(self):
        # A at (0..1), B at (2..3), moving A by +3 would land at 3..4,
        # but vanilla only clamps when other.maxX <= minX. So still 3.0.
        # Use the reverse scenario where the check fires: A at (5..6),
        # B at (1..2), moving A by -10 -> other.minX=1 >= maxX=6? no.
        # Correct clamp scenario: moving left, B to the left.
        a = AxisAlignedBB(5, 0, 0, 6, 1, 1)
        b = AxisAlignedBB(1, 0, 0, 2, 1, 1)
        # offset=-10, B.minX=1 >= A.maxX=6? false (1 < 6). No clamp.
        # Real clamp: A at (5..6), offset=-2 would land at 3..4, no overlap.
        # Offset=-5 would land at 0..1, overlapping B's right edge at 2.
        # Vanilla check: other.minX(1) >= self.maxX(6)? false. So returns -5.
        self.assertAlmostEqual(a.calculate_x_offset(b, -5.0), -5.0)

    def test_x_offset_bounds_check(self):
        # Direct test of the vanilla branch: other.maxX <= minX.
        a = AxisAlignedBB(10, 0, 0, 11, 1, 1)
        b = AxisAlignedBB(0, 0, 0, 1, 1, 1)  # b.maxX=1 <= a.minX=10 -> clamp
        # moving +20: min(20, 10 - 1) = 9.0
        self.assertAlmostEqual(a.calculate_x_offset(b, 20.0), 9.0)

class TestJavaRandom(unittest.TestCase):
    def test_known_sequence_seed_0(self):
        # java.util.Random(0) verified against OpenJDK:
        # -1155484576, -723955400, 1033096058
        r = JavaRandom(0)
        self.assertEqual(r.next_int(), -1155484576)
        self.assertEqual(r.next_int(), -723955400)
        self.assertEqual(r.next_int(), 1033096058)

    def test_known_sequence_seed_12345(self):
        # Verified against OpenJDK on this machine (see research/java_random_reference.txt).
        r = JavaRandom(12345)
        self.assertEqual(r.next_int(), 1553932502)

    def test_known_sequence_seed_1(self):
        r = JavaRandom(1)
        self.assertEqual(r.next_int(), -1155869325)
        self.assertEqual(r.next_int(), 431529176)

    def test_bound100_seed42(self):
        # OpenJDK: new Random(42) nextInt(100) -> 30, 63, 48
        r = JavaRandom(42)
        self.assertEqual(r.next_int(100), 30)
        self.assertEqual(r.next_int(100), 63)
        self.assertEqual(r.next_int(100), 48)

    def test_next_int_bound(self):
        r = JavaRandom(42)
        for _ in range(100):
            v = r.next_int(100)
            self.assertGreaterEqual(v, 0)
            self.assertLess(v, 100)

    def test_string_hash(self):
        self.assertEqual(java_string_hash('abc'), 96354)

if __name__ == '__main__':
    unittest.main()
