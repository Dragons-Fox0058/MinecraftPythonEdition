"""engine.world.chunk_provider — In-memory chunk storage keyed by ChunkPos."""
from __future__ import annotations
from typing import Dict, Iterable, Optional
from engine.core import ChunkPos
from engine.world.chunk import Chunk


class ChunkProvider:
    """Simple in-memory chunk storage. Terrain generation comes in phase 4."""

    def __init__(self):
        self._chunks: Dict[ChunkPos, Chunk] = {}

    def has_chunk(self, cx: int, cz: int) -> bool:
        return ChunkPos(cx, cz) in self._chunks

    def get_chunk(self, cx: int, cz: int) -> Optional[Chunk]:
        return self._chunks.get(ChunkPos(cx, cz))

    def get_or_create(self, cx: int, cz: int) -> Chunk:
        pos = ChunkPos(cx, cz)
        c = self._chunks.get(pos)
        if c is None:
            c = Chunk(pos)
            self._chunks[pos] = c
        return c

    def unload(self, cx: int, cz: int) -> None:
        self._chunks.pop(ChunkPos(cx, cz), None)

    def all_chunks(self) -> Iterable[Chunk]:
        return list(self._chunks.values())

    def __len__(self):
        return len(self._chunks)
