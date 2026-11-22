"""engine.world.chunk — 16x16x256 chunk storage using NumPy.

Layout:
  blocks: uint16 array of shape (16, 16, 256), index [x, z, y]
          each element stores the legacy 1.12.2 state value:
          (block_id << 4) | metadata. Public *_block_state_id methods
          intentionally expose the numeric block ID for gameplay callers.
  light:  uint8 array of shape (16, 16, 256)
          low nibble = block light (0..15), high nibble = sky light (0..15)

Coordinate convention: chunk-local x,z in [0,16), y in [0,256).
"""
from __future__ import annotations
import numpy as np
from engine.core import BlockPos, ChunkPos, CHUNK_SIZE, CHUNK_HEIGHT


class Chunk:
    __slots__ = ('pos', 'blocks', 'light', 'biomes', 'heightmap', '_dirty')

    def __init__(self, pos: ChunkPos):
        self.pos = pos
        self.blocks = np.zeros((CHUNK_SIZE, CHUNK_SIZE, CHUNK_HEIGHT), dtype=np.uint16)
        self.light = np.zeros((CHUNK_SIZE, CHUNK_SIZE, CHUNK_HEIGHT), dtype=np.uint8)
        self.biomes = np.zeros((CHUNK_SIZE, CHUNK_SIZE), dtype=np.uint8)
        self.heightmap = np.zeros((CHUNK_SIZE, CHUNK_SIZE), dtype=np.uint32)
        self._dirty = False

    # --- local coords ---
    @staticmethod
    def local_x(world_x: int) -> int:
        return world_x & 15

    @staticmethod
    def local_z(world_z: int) -> int:
        return world_z & 15

    # --- block access ---
    def get_packed_block_state(self, lx: int, ly: int, lz: int) -> int:
        """Return the stored 1.12.2 value: (block ID << 4) | metadata."""
        return int(self.blocks[lx, lz, ly])

    def set_packed_block_state(self, lx: int, ly: int, lz: int, packed_state: int) -> None:
        """Store a packed 1.12.2 block state without losing metadata."""
        if isinstance(packed_state, bool) or not isinstance(packed_state, int):
            raise TypeError("packed_state must be an integer")
        if not 0 <= packed_state <= 0xFFFF:
            raise ValueError("packed_state must fit in uint16")
        self.blocks[lx, lz, ly] = packed_state
        self._dirty = True

    def get_block_state_id(self, lx: int, ly: int, lz: int) -> int:
        """Return the numeric block ID (metadata is intentionally omitted)."""
        return self.get_packed_block_state(lx, ly, lz) >> 4

    def set_block_state_id(self, lx: int, ly: int, lz: int, block_id: int) -> None:
        """Set a block by numeric ID, using metadata zero."""
        if isinstance(block_id, bool) or not isinstance(block_id, int):
            raise TypeError("block_id must be an integer")
        if not 0 <= block_id <= 0xFFF:
            raise ValueError("block_id must fit in the 12-bit Anvil block ID range")
        self.set_packed_block_state(lx, ly, lz, block_id << 4)

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
    def fill_layer(self, ly: int, block_id: int) -> None:
        if isinstance(block_id, bool) or not isinstance(block_id, int) or not 0 <= block_id <= 0xFFF:
            raise ValueError("block_id must be an integer in the 12-bit range")
        self.blocks[:, :, ly] = block_id << 4
        self._dirty = True

    def fill_box(self, x0, y0, z0, x1, y1, z1, block_id: int) -> None:
        if isinstance(block_id, bool) or not isinstance(block_id, int) or not 0 <= block_id <= 0xFFF:
            raise ValueError("block_id must be an integer in the 12-bit range")
        self.blocks[x0:x1, z0:z1, y0:y1] = block_id << 4
        self._dirty = True

    @property
    def dirty(self) -> bool:
        return self._dirty

    def clear_dirty(self) -> None:
        self._dirty = False

    def __repr__(self):
        return f'Chunk({self.pos.x}, {self.pos.z})'
