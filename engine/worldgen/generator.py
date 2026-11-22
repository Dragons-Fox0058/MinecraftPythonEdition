"""engine.worldgen.generator — Overworld terrain generator (1.12.2-like)."""
from __future__ import annotations
import math
import numpy as np
from engine.core import JavaRandom, BlockPos, ChunkPos
from engine.world.chunk import Chunk
from engine.worldgen.noise import NoiseGeneratorOctaves, NoiseGeneratorPerlin
from engine.worldgen.biome import BiomeProvider, DEFAULT_BIOME


AIR = 0
STONE = 1
GRASS = 2
DIRT = 3
BEDROCK = 7
WATER = 9
SAND = 12
GRAVEL = 13
SANDSTONE = 24
SNOW = 80
ICE = 79


class ChunkGeneratorOverworld:
    """Simplified 1.12.2 overworld generator.

    Produces a heightmap from noise, layers stone/dirt/grass, fills oceans
    with water, adds bedrock at y=0, carves simple caves, and scatters ores.
    """

    SEA_LEVEL = 63

    def __init__(self, seed: int):
        self.seed = seed
        self.biome_provider = BiomeProvider(seed)
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
                n_min = self.noise_min.noise3(wx * 0.03, 0, wz * 0.03)
                n_max = self.noise_max.noise3(wx * 0.03, 0, wz * 0.03)
                base = biome.base_height * 30.0
                var = biome.height_variation * 30.0
                avg = (n_min + n_max) * 0.5
                h = 64.0 + base + avg * var
                hm[lx, lz] = int(max(1, min(255, h)))
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
                        sid = biome.top_block_id if height >= self.SEA_LEVEL else SAND
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
            (20, 0, 128, 16, 9),    # coal
            (20, 0, 64, 15, 9),     # iron
            (2, 0, 32, 14, 9),      # gold
            (8, 0, 16, 56, 8),      # diamond
            (1, 0, 32, 73, 7),      # redstone (ore block id 73)
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
        # deterministic rng per chunk
        r = JavaRandom((cx * 341873128712 + cz * 132897987541 + self.seed) & 0xFFFFFFFF)
        self.generate_caves(chunk, r)
        self.generate_ores(chunk, r)
        return chunk
