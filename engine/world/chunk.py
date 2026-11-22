"""engine.world.chunk — 16x16x256 chunk storage using NumPy.

Layout:
  blocks: uint16 array of shape (16, 16, 256), index [x, z, y]
          each element is a block state ID into a global palette
          (we use block_id << 4 | meta for now; proper palette in phase 3.5)
  light:  uint8 array of shape (16, 16, 256)
          low nibble = block light (0..15), high nibble = sky light (0..15)

Coordinate convention: chunk-local x,z in [0,16), y in [0,256).
"""
from __future__ import annotations
import numpy as np
from engine.core import BlockPos, ChunkPos, CHUNK_SIZE, CHUNK_HEIGHT


class Chunk:
    __slots__ = ('pos', 'blocks', 'light', '_dirty')

    def __init__(self, pos: ChunkPos):
        self.pos = pos
        self.blocks = np.zeros((CHUNK_SIZE, CHUNK_SIZE, CHUNK_HEIGHT), dtype=np.uint16)
        self.light = np.zeros((CHUNK_SIZE, CHUNK_SIZE, CHUNK_HEIGHT), dtype=np.uint8)
        self._dirty = False

    # --- local coords ---
    @staticmethod
    def local_x(world_x: int) -> int:
        return world_x & 15

    @staticmethod
    def local_z(world_z: int) -> int:
        return world_z & 15

    # --- block access ---
    def get_block_state_id(self, lx: int, ly: int, lz: int) -> int:
        return int(self.blocks[lx, lz, ly])

    def set_block_state_id(self, lx: int, ly: int, lz: int, state_id: int) -> None:
        self.blocks[lx, lz, ly] = state_id
        self._dirty = True

    # --- light access ---
    def get_sky_light(self, lx: int, ly: int, lz: int) -> int:
        return int(self.light[lx, lz, ly] >> 4)

    def get_block_light(self, lx: int, ly: int, lz: int) -> int:
        return int(self.light[lx, lz, ly] & 0xF)

    def set_sky_light(self, lx: int, ly: int, lz: int, level: int) -> None:
        level = max(0, min(15, level))
        cur = int(self.light[lx, lz, ly])
        self.light[lx, lz, ly] = (level << 4) | (cur & 0xF)

    def set_block_light(self, lx: int, ly: int, lz: int, level: int) -> None:
        level = max(0, min(15, level))
        cur = int(self.light[lx, lz, ly])
        self.light[lx, lz, ly] = (cur & 0xF0) | level

    # --- fill helpers ---
    def fill_layer(self, ly: int, state_id: int) -> None:
        self.blocks[:, :, ly] = state_id
        self._dirty = True

    def fill_box(self, x0, y0, z0, x1, y1, z1, state_id: int) -> None:
        self.blocks[x0:x1, z0:z1, y0:y1] = state_id
        self._dirty = True

    @property
    def dirty(self) -> bool:
        return self._dirty

    def clear_dirty(self) -> None:
        self._dirty = False

    def __repr__(self):
        return f'Chunk({self.pos.x}, {self.pos.z})'
