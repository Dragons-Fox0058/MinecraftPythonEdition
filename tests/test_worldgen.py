"""tests/test_worldgen.py — Noise, biome, terrain generator tests."""
import unittest
import numpy as np
from engine.core import JavaRandom, ChunkPos
from engine.worldgen import (
    NoiseGeneratorPerlin, NoiseGeneratorOctaves, NoiseGeneratorSimplex,
    BiomeProvider, BIOMES, DEFAULT_BIOME,
    ChunkGeneratorOverworld, ChunkProviderOverworld,
)


class TestNoisePerlin(unittest.TestCase):
    def test_constructor_offsets_match_java_random_seed_zero(self):
        noise = NoiseGeneratorPerlin(JavaRandom(0))
        self.assertAlmostEqual(noise.x_offset, 0.730967787376657 * 256.0, places=12)
        self.assertAlmostEqual(noise.y_offset, 0.24053641567148587 * 256.0, places=12)
        self.assertAlmostEqual(noise.z_offset, 0.6374174253501083 * 256.0, places=12)

    def test_deterministic(self):
        r1 = JavaRandom(42)
        r2 = JavaRandom(42)
        n1 = NoiseGeneratorPerlin(r1)
        n2 = NoiseGeneratorPerlin(r2)
        for _ in range(10):
            x, y, z = 1.5, 2.5, 3.5
            self.assertAlmostEqual(n1.noise3(x, y, z), n2.noise3(x, y, z), places=10)

    def test_range(self):
        n = NoiseGeneratorPerlin(JavaRandom(0))
        for i in range(20):
            v = n.noise3(i * 0.3, 0.0, i * 0.3)
            self.assertLess(abs(v), 5.0)


class TestNoiseOctaves(unittest.TestCase):
    def test_deterministic(self):
        o1 = NoiseGeneratorOctaves(JavaRandom(0), 4)
        o2 = NoiseGeneratorOctaves(JavaRandom(0), 4)
        self.assertAlmostEqual(o1.noise3(1.0, 2.0, 3.0),
                               o2.noise3(1.0, 2.0, 3.0), places=10)

    def test_different_seed(self):
        o1 = NoiseGeneratorOctaves(JavaRandom(0), 4)
        o2 = NoiseGeneratorOctaves(JavaRandom(1), 4)
        v1 = o1.noise3(1.0, 2.0, 3.0)
        v2 = o2.noise3(1.0, 2.0, 3.0)
        self.assertNotEqual(v1, v2)


class TestNoiseSimplex(unittest.TestCase):
    def test_deterministic(self):
        s1 = NoiseGeneratorSimplex(JavaRandom(7))
        s2 = NoiseGeneratorSimplex(JavaRandom(7))
        self.assertAlmostEqual(s1.noise2(1.0, 2.0), s2.noise2(1.0, 2.0), places=10)


class TestBiomeProvider(unittest.TestCase):
    def test_deterministic(self):
        bp1 = BiomeProvider(123)
        bp2 = BiomeProvider(123)
        for x in range(-20, 20, 3):
            for z in range(-20, 20, 3):
                self.assertEqual(bp1.get_biome_at(x, z).biome_id,
                                 bp2.get_biome_at(x, z).biome_id)

    def test_returns_biome(self):
        bp = BiomeProvider(0)
        b = bp.get_biome_at(0, 0)
        self.assertIn(b.biome_id, BIOMES)

    def test_known_biome_ids(self):
        self.assertEqual(BIOMES[1].registry_name, 'plains')
        self.assertEqual(BIOMES[0].registry_name, 'ocean')


class TestChunkGenerator(unittest.TestCase):
    def test_deterministic_heightmap(self):
        g1 = ChunkGeneratorOverworld(0)
        g2 = ChunkGeneratorOverworld(0)
        h1 = g1.generate_heightmap(0, 0)
        h2 = g2.generate_heightmap(0, 0)
        self.assertTrue(np.array_equal(h1, h2))

    def test_heightmap_in_range(self):
        g = ChunkGeneratorOverworld(0)
        hm = g.generate_heightmap(0, 0)
        self.assertEqual(hm.shape, (16, 16))
        self.assertTrue((hm >= 1).all())
        self.assertTrue((hm <= 255).all())

    def test_terrain_has_bedrock_at_y0(self):
        g = ChunkGeneratorOverworld(0)
        c = g.generate_chunk(0, 0)
        for x in range(16):
            for z in range(16):
                self.assertEqual(c.get_block_state_id(x, 0, z), 7)  # bedrock

    def test_terrain_has_air_at_top(self):
        g = ChunkGeneratorOverworld(0)
        c = g.generate_chunk(0, 0)
        # y=255 should be air
        for x in range(16):
            for z in range(16):
                self.assertEqual(c.blocks[x, z, 255], 0)

    def test_generated_chunk_stores_biomes_and_heightmap(self):
        generator = ChunkGeneratorOverworld(12345)
        chunk = generator.generate_chunk(-2, 3)
        heights = generator.generate_heightmap(-2, 3)
        for x in range(16):
            for z in range(16):
                biome = generator.biome_provider.get_biome_at(-32 + x, 48 + z)
                self.assertEqual(int(chunk.biomes[x, z]), biome.biome_id)
                self.assertEqual(int(chunk.heightmap[x, z]), int(heights[x, z]) + 1)

    def test_terrain_has_stone_somewhere(self):
        g = ChunkGeneratorOverworld(0)
        c = g.generate_chunk(0, 0)
        self.assertTrue((c.blocks == (1 << 4)).any())

    def test_different_seeds_differ(self):
        g1 = ChunkGeneratorOverworld(0)
        g2 = ChunkGeneratorOverworld(9999)
        h1 = g1.generate_heightmap(0, 0)
        h2 = g2.generate_heightmap(0, 0)
        self.assertFalse(np.array_equal(h1, h2))


class TestChunkProviderOverworld(unittest.TestCase):
    def test_provides_generated_chunks(self):
        p = ChunkProviderOverworld(0)
        c = p.get_or_create(0, 0)
        self.assertEqual(c.pos, ChunkPos(0, 0))
        # Should have terrain, not just air
        self.assertTrue((c.blocks == (1 << 4)).any())

    def test_caches_chunks(self):
        p = ChunkProviderOverworld(0)
        c1 = p.get_or_create(0, 0)
        c2 = p.get_or_create(0, 0)
        self.assertIs(c1, c2)


if __name__ == '__main__':
    unittest.main()
