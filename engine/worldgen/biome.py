"""engine.worldgen.biome — 1.12.2 Biome definitions (subset)."""
from __future__ import annotations


class Biome:
    def __init__(self, biome_id, registry_name, temperature, rainfall,
                 base_height, height_variation, top_block_id, filler_block_id,
                 grass_color, foliage_color):
        self.biome_id = biome_id
        self.registry_name = registry_name
        self.temperature = temperature
        self.rainfall = rainfall
        self.base_height = base_height
        self.height_variation = height_variation
        self.top_block_id = top_block_id
        self.filler_block_id = filler_block_id
        self.grass_color = grass_color
        self.foliage_color = foliage_color

    def __repr__(self):
        return f'Biome({self.registry_name})'


BIOMES = {
    0:  Biome(0,  'ocean',       0.5, 0.5, -1.0, 0.1, 12, 12, 0x8EB971, 0x71A74D),
    1:  Biome(1,  'plains',      0.8, 0.4,  0.1, 0.3,  2,  3, 0x91BD59, 0x77AB2F),
    2:  Biome(2,  'desert',      2.0, 0.0,  0.1, 0.2, 12, 12, 0xBFB755, 0xAEA42A),
    3:  Biome(3,  'mountains',   0.2, 0.3,  1.0, 0.5,  2,  3, 0x8AB689, 0x6DA36B),
    4:  Biome(4,  'forest',      0.7, 0.8,  0.1, 0.2,  2,  3, 0x79C05A, 0x59AE30),
    5:  Biome(5,  'taiga',       0.25, 0.8, 0.2, 0.2,  2,  3, 0x86B783, 0x68A464),
    6:  Biome(6,  'swampland',   0.8, 0.9, -0.2, 0.1,  2,  3, 0x6A7039, 0x6A7039),
    7:  Biome(7,  'river',       0.5, 0.5, -0.5, 0.0, 12, 12, 0x8EB971, 0x71A74D),
    8:  Biome(8,  'hell',        2.0, 0.0,  0.1, 0.2, 87, 87, 0x000000, 0x000000),
    9:  Biome(9,  'sky',         0.5, 0.5,  0.1, 0.2,  2,  3, 0x000000, 0x000000),
    10: Biome(10, 'frozen_ocean',0.0, 0.5, -1.0, 0.1, 12, 12, 0x80B497, 0x60A17B),
    11: Biome(11, 'frozen_river',0.0, 0.5, -0.5, 0.0, 12, 12, 0x80B497, 0x60A17B),
    12: Biome(12, 'ice_flats',   0.0, 0.5,  0.1, 0.3,  2,  3, 0x80B497, 0x60A17B),
    13: Biome(13, 'ice_mountains',0.0,0.5,  1.0, 0.5,  2,  3, 0x80B497, 0x60A17B),
    14: Biome(14, 'mushroom_island',0.9,1.0,0.2,0.3, 2,  3, 0x55C93F, 0x2BBB0F),
    15: Biome(15, 'mushroom_island_shore',0.9,1.0,0.1,0.3,2,3,0x55C93F,0x2BBB0F),
    16: Biome(16, 'beaches',     0.8, 0.4,  0.0, 0.1, 12, 12, 0x91BD59, 0x77AB2F),
    17: Biome(17, 'stone_beach', 0.2, 0.3,  0.1, 0.1,  1,  1, 0x8AB689, 0x6DA36B),
    18: Biome(18, 'cold_beach',  0.05,0.3,  0.0, 0.1, 12, 12, 0x80B497, 0x60A17B),
    19: Biome(19, 'roofed_forest',0.7,0.8,  0.1, 0.2,  2,  3, 0x79C05A, 0x59AE30),
    20: Biome(20, 'taiga_cold',  0.05,0.8,  0.2, 0.2,  2,  3, 0x80B497, 0x60A17B),
    21: Biome(21, 'taiga_cold_hills',0.05,0.8,1.0,0.5, 2,  3, 0x80B497, 0x60A17B),
    22: Biome(22, 'redwood_taiga',0.7,0.8,  0.2, 0.2,  2,  3, 0x79C05A, 0x59AE30),
    23: Biome(23, 'redwood_taiga_hills',0.7,0.8,1.0,0.5,2,3, 0x79C05A, 0x59AE30),
    24: Biome(24, 'extreme_hills_with_trees',0.2,0.3,1.0,0.5,2,3,0x8AB689,0x6DA36B),
    25: Biome(25, 'smaller_extreme_hills',0.2,0.3,1.0,0.5,2,3,0x8AB689,0x6DA36B),
    26: Biome(26, 'stone_beach', 0.2, 0.3,  0.1, 0.1,  1,  1, 0x8AB689, 0x6DA36B),
    27: Biome(27, 'birch_forest',0.6, 0.6,  0.1, 0.2,  2,  3, 0x88BB67, 0x6BA941),
    28: Biome(28, 'birch_forest_hills',0.6,0.6,1.0,0.5,2,3,0x88BB67,0x6BA941),
    29: Biome(29, 'roofed_forest',0.7, 0.8, 0.1, 0.2,  2,  3, 0x79C05A, 0x59AE30),
    30: Biome(30, 'cold_taiga',  0.05, 0.8, 0.2, 0.2,  2,  3, 0x80B497, 0x60A17B),
    31: Biome(31, 'cold_taiga_hills',0.05,0.8,1.0,0.5,2,3,0x80B497,0x60A17B),
    32: Biome(32, 'mega_taiga',  0.3, 0.8,  0.2, 0.2,  2,  3, 0x86B87F, 0x68A55F),
    33: Biome(33, 'mega_taiga_hills',0.3,0.8,1.0,0.5,2,3,0x86B87F,0x68A55F),
    34: Biome(34, 'extreme_hills_with_trees',0.2,0.3,1.0,0.5,2,3,0x8AB689,0x6DA36B),
    35: Biome(35, 'savanna',      1.2, 0.0,  0.1, 0.2,  2,  3, 0xBFB755, 0xAEA42A),
    36: Biome(36, 'savanna_rock',1.1, 0.0,  0.1, 0.2,  2,  3, 0xBFB755, 0xAEA42A),
    37: Biome(37, 'mesa',        2.0, 0.0,  0.1, 0.2, 12, 12, 0x90814D, 0x9E814D),
    38: Biome(38, 'mesa_rock',   2.0, 0.0,  0.1, 0.2, 12, 12, 0x90814D, 0x9E814D),
    39: Biome(39, 'mesa_clear_rock',2.0,0.0, 0.1, 0.2, 12, 12, 0x90814D, 0x9E814D),
}

DEFAULT_BIOME = BIOMES[1]


class BiomeProvider:
    def __init__(self, seed: int):
        self.seed = seed

    def get_biome_at(self, x: int, z: int) -> Biome:
        # Simplified: mostly plains with some variety by hash.
        h = (x * 341873128712 + z * 132897987541 + self.seed) & 0xFFFFFFFF
        if h % 17 == 0:
            return BIOMES[4]   # forest
        if h % 23 == 0:
            return BIOMES[3]   # mountains
        if h % 29 == 0:
            return BIOMES[2]   # desert
        if h % 31 == 0:
            return BIOMES[5]   # taiga
        return DEFAULT_BIOME
