"""engine.worldgen.generator — Overworld terrain generator (1.12.2-like)."""
from __future__ import annotations
import math
import numpy as np
from engine.core import JavaRandom, BlockPos, ChunkPos
from engine.world.chunk import Chunk
from engine.worldgen.noise import NoiseGeneratorOctaves, NoiseGeneratorPerlin
from engine.worldgen.biome import BiomeProvider, DEFAULT_BIOME


# Chunk.blocks stores the Java 1.12.2 legacy state word:
# (numeric block ID << 4) | metadata. Generated terrain uses metadata 0.
AIR = 0
STONE = 1 << 4
GRASS = 2 << 4
DIRT = 3 << 4
BEDROCK = 7 << 4
WATER = 9 << 4
SAND = 12 << 4
GRAVEL = 13 << 4
SANDSTONE = 24 << 4
SNOW = 80 << 4
ICE = 79 << 4


def _signed_long(value: int) -> int:
    value &= 0xFFFFFFFFFFFFFFFF
    return value - (1 << 64) if value >= (1 << 63) else value


def _mapgen_chunk_random(world_seed: int, chunk_x: int, chunk_z: int) -> JavaRandom:
    """Java 1.12.2 MapGenBase chunk RNG seed derivation."""
    seed_rng = JavaRandom(world_seed)
    x_seed = seed_rng.next_long()
    z_seed = seed_rng.next_long()
    chunk_seed = _signed_long((chunk_x * x_seed) ^ (chunk_z * z_seed) ^ world_seed)
    return JavaRandom(chunk_seed)


def _java_make_odd(value: int) -> int:
    """Java's value / 2L * 2L + 1L, including truncation toward zero."""
    half = value // 2 if value >= 0 else -((-value) // 2)
    return _signed_long(half * 2 + 1)


def _population_chunk_random(world_seed: int, chunk_x: int, chunk_z: int) -> JavaRandom:
    """Java 1.12.2 feature-population chunk RNG seed derivation."""
    seed_rng = JavaRandom(world_seed)
    x_seed = _java_make_odd(seed_rng.next_long())
    z_seed = _java_make_odd(seed_rng.next_long())
    chunk_seed = _signed_long(((chunk_x * x_seed) + (chunk_z * z_seed)) ^ world_seed)
    return JavaRandom(chunk_seed)


class ChunkGeneratorOverworld:
    """Simplified 1.12.2 overworld generator.

    Produces a heightmap from noise, layers stone/dirt/grass, fills oceans
    with water, adds bedrock at y=0, carves simple caves, and scatters ores.
    """

    SEA_LEVEL = 63

    def __init__(self, seed: int):
        self.seed = seed
        self.biome_provider = BiomeProvider(seed)
        # Seeded domain offsets prevent nearby seed values from quantizing to
        # identical low-relief heightmaps in this simplified terrain model.
        seed_value = int(seed) & 0xFFFFFFFFFFFFFFFF
        self._seed_offset_x = ((seed_value * 0x9E3779B1) & 0xFFFF) / 257.0
        self._seed_offset_z = ((seed_value * 0x85EBCA77) & 0xFFFF) / 263.0
        seed_mix = ((seed_value & 0xFFFFFFFF) * 1664525 + 1013904223) & 0xFFFFFFFF
        self._seed_height_bias = (seed_mix / 0xFFFFFFFF) * 64.0 - 32.0
        rng = JavaRandom(seed)
        self.noise_min = NoiseGeneratorOctaves(rng, 16)
        self.noise_max = NoiseGeneratorOctaves(rng, 16)
        self.noise_main = NoiseGeneratorOctaves(rng, 8)
        self.surface_noise = NoiseGeneratorPerlin(rng)

    # ---------------- heightmap ----------------
    def generate_heightmap(self, cx: int, cz: int) -> np.ndarray:
        hm = np.zeros((16, 16), dtype=np.int32)
        for lx in range(16):
            for lz in range(16):
                wx = cx * 16 + lx
                wz = cz * 16 + lz
                biome = self.biome_provider.get_biome_at(wx, wz)
                n_min = self.noise_min.noise3((wx + self._seed_offset_x) * 0.03, 0, (wz + self._seed_offset_z) * 0.03)
                n_max = self.noise_max.noise3((wx + self._seed_offset_x) * 0.03, 0, (wz + self._seed_offset_z) * 0.03)
                base = biome.base_height * 30.0
                var = biome.height_variation * 80.0
                avg = (n_min + n_max) * 0.5
                h = 64.0 + base + avg * var + self._seed_height_bias
                hm[lx, lz] = int(max(1, min(254, h)))
        return hm

    # ---------------- terrain blocks ----------------
    def set_blocks_in_chunk(self, chunk: Chunk, hm: np.ndarray) -> None:
        for lx in range(16):
            for lz in range(16):
                wx = chunk.pos.x * 16 + lx
                wz = chunk.pos.z * 16 + lz
                biome = self.biome_provider.get_biome_at(wx, wz)
                height = int(hm[lx, lz])
                for y in range(256):
                    if y == 0:
                        sid = BEDROCK
                    elif y < height - 4:
                        sid = STONE
                    elif y < height:
                        sid = DIRT
                    elif y == height:
                        sid = (biome.top_block_id << 4) if height >= self.SEA_LEVEL else SAND
                    else:
                        sid = AIR
                    chunk.blocks[lx, lz, y] = sid
                # water fill above terrain if below sea level
                if height < self.SEA_LEVEL:
                    for y in range(height + 1, self.SEA_LEVEL + 1):
                        chunk.blocks[lx, lz, y] = WATER
                    # ice on top for cold biomes
                    if biome.temperature < 0.15 and self.SEA_LEVEL < 255:
                        chunk.blocks[lx, lz, self.SEA_LEVEL] = ICE

    # ---------------- caves ----------------
    def generate_caves(self, chunk: Chunk, rng: JavaRandom) -> None:
        # Simple: carve a few random tunnels. Full 1.12.2 cave carving is huge;
        # this produces plausible caves with deterministic seed behaviour.
        for _ in range(6):
            x = rng.next_int(16)
            y = 8 + rng.next_int(48)
            z = rng.next_int(16)
            length = 20 + rng.next_int(60)
            dx = (rng.next_float() - 0.5) * 0.6
            dy = (rng.next_float() - 0.5) * 0.4
            dz = (rng.next_float() - 0.5) * 0.6
            for _ in range(length):
                x += dx; y += dy; z += dz
                ix = int(x); iy = int(y); iz = int(z)
                if 1 <= ix < 15 and 1 <= iz < 15 and 1 < iy < 250:
                    for ox in range(-1, 2):
                        for oy in range(-1, 2):
                            for oz in range(-1, 2):
                                px = ix + ox; py = iy + oy; pz = iz + oz
                                if 0 <= px < 16 and 0 <= pz < 16 and 1 <= py < 250:
                                    if chunk.blocks[px, pz, py] in (STONE, DIRT, GRASS):
                                        chunk.blocks[px, pz, py] = AIR

    # ---------------- ores ----------------
    def generate_ores(self, chunk: Chunk, rng: JavaRandom) -> None:
        # 1.12.2-ish ore distribution by y-level.
        # Each vein: count, min_y, max_y, block id, size
        ores = [
            (20, 0, 128, 16 << 4, 9),    # coal
            (20, 0, 64, 15 << 4, 9),      # iron
            (2, 0, 32, 14 << 4, 9),       # gold
            (8, 0, 16, 56 << 4, 8),       # diamond
            (1, 0, 32, 73 << 4, 7),       # redstone
        ]
        for count, ymin, ymax, ore_id, size in ores:
            for _ in range(count):
                ox = rng.next_int(16)
                oy = ymin + rng.next_int(max(1, ymax - ymin))
                oz = rng.next_int(16)
                for _ in range(size):
                    x = ox + rng.next_int(3) - 1
                    y = oy + rng.next_int(3) - 1
                    z = oz + rng.next_int(3) - 1
                    if 0 <= x < 16 and 0 <= z < 16 and 1 <= y < 250:
                        if chunk.blocks[x, z, y] == STONE:
                            chunk.blocks[x, z, y] = ore_id

    # ---------------- provider interface ----------------
    def generate_chunk(self, cx: int, cz: int) -> Chunk:
        chunk = Chunk(ChunkPos(cx, cz))
        hm = self.generate_heightmap(cx, cz)
        self.set_blocks_in_chunk(chunk, hm)
        # Persist biome IDs and the generated surface height with the chunk.
        for lx in range(16):
            for lz in range(16):
                wx = cx * 16 + lx
                wz = cz * 16 + lz
                biome = self.biome_provider.get_biome_at(wx, wz)
                chunk.biomes[lx, lz] = biome.biome_id
                chunk.heightmap[lx, lz] = int(hm[lx, lz]) + 1
        # Vanilla derives independent streams for MapGenBase and population.
        # This fixes the previous ad-hoc linear coordinate hash, but the
        # simplified cave/ore algorithms below are not full vanilla generators.
        self.generate_caves(chunk, _mapgen_chunk_random(self.seed, cx, cz))
        self.generate_ores(chunk, _population_chunk_random(self.seed, cx, cz))
        return chunk
