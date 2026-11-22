"""engine.worldgen.provider — ChunkProviderOverworld wires ChunkGenerator to World."""
from __future__ import annotations
from engine.world.chunk_provider import ChunkProvider
from engine.worldgen.generator import ChunkGeneratorOverworld


class ChunkProviderOverworld(ChunkProvider):
    def __init__(self, seed: int = 0):
        super().__init__()
        self.seed = seed
        self.generator = ChunkGeneratorOverworld(seed)

    def get_or_create(self, cx: int, cz: int):
        from engine.core import ChunkPos
        pos = ChunkPos(cx, cz)
        c = self._chunks.get(pos)
        if c is None:
            c = self.generator.generate_chunk(cx, cz)
            self._chunks[pos] = c
        return c
