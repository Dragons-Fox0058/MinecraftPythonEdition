"""CPU-side opaque chunk mesh builder for the 1.12.2 voxel renderer."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from engine.world.chunk import Chunk


@dataclass(frozen=True)
class MeshData:
    positions: np.ndarray
    colors: np.ndarray
    indices: np.ndarray

    @property
    def vertex_count(self) -> int:
        return int(self.positions.shape[0])

    @property
    def triangle_count(self) -> int:
        return int(self.indices.size // 3)

    @property
    def is_empty(self) -> bool:
        return self.indices.size == 0


# Corners are ordered for outward-facing triangles in a right-handed XYZ space.
_FACES = (
    # direction, corners
    ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))),
    ((1, 0, 0), ((1, 0, 1), (1, 0, 0), (1, 1, 0), (1, 1, 1))),
    ((0, -1, 0), ((0, 0, 1), (0, 0, 0), (1, 0, 0), (1, 0, 1))),
    ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0))),
    ((0, 0, -1), ((1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0))),
    ((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
)


def _block_color(block_id: int) -> tuple[float, float, float]:
    # Temporary deterministic palette; resource-pack atlas support is a later step.
    value = (block_id * 0x45D9F3B) & 0xFFFFFFFF
    return (0.25 + ((value >> 16) & 0xFF) / 510.0,
            0.25 + ((value >> 8) & 0xFF) / 510.0,
            0.25 + (value & 0xFF) / 510.0)


class ChunkMeshBuilder:
    """Build visible faces for non-air blocks; mesh coordinates are world XYZ."""

    def build(self, chunk: Chunk, *, neighbors: dict[tuple[int, int], Chunk] | None = None) -> MeshData:
        if not isinstance(chunk, Chunk):
            raise TypeError("chunk must be a Chunk")
        neighbors = neighbors or {}
        blocks = chunk.blocks
        occupied = blocks != 0
        positions: list[np.ndarray] = []
        colors: list[np.ndarray] = []
        indices: list[np.ndarray] = []
        base_vertex = 0

        for (dx, dy, dz), corners in _FACES:
            visible = occupied.copy()
            if dx == -1:
                visible[1:, :, :] &= ~occupied[:-1, :, :]
                edge = neighbors.get((chunk.pos.x - 1, chunk.pos.z))
                if edge is None:
                    visible[0, :, :] = occupied[0, :, :]
                else:
                    visible[0, :, :] &= edge.blocks[15, :, :] == 0
            elif dx == 1:
                visible[:-1, :, :] &= ~occupied[1:, :, :]
                edge = neighbors.get((chunk.pos.x + 1, chunk.pos.z))
                if edge is None:
                    visible[-1, :, :] = occupied[-1, :, :]
                else:
                    visible[-1, :, :] &= edge.blocks[0, :, :] == 0
            elif dy == -1:
                visible[:, :, 1:] &= ~occupied[:, :, :-1]
                visible[:, :, 0] = occupied[:, :, 0]
            elif dy == 1:
                visible[:, :, :-1] &= ~occupied[:, :, 1:]
                visible[:, :, -1] = occupied[:, :, -1]
            elif dz == -1:
                visible[:, 1:, :] &= ~occupied[:, :-1, :]
                edge = neighbors.get((chunk.pos.x, chunk.pos.z - 1))
                if edge is None:
                    visible[:, 0, :] = occupied[:, 0, :]
                else:
                    visible[:, 0, :] &= edge.blocks[:, 15, :] == 0
            elif dz == 1:
                visible[:, :-1, :] &= ~occupied[:, 1:, :]
                edge = neighbors.get((chunk.pos.x, chunk.pos.z + 1))
                if edge is None:
                    visible[:, -1, :] = occupied[:, -1, :]
                else:
                    visible[:, -1, :] &= edge.blocks[:, 0, :] == 0

            cells = np.argwhere(visible)
            if not len(cells):
                continue
            # Stored array order is [x, z, y]; convert to world [x, y, z].
            xyz = np.column_stack((
                cells[:, 0] + chunk.pos.x * 16,
                cells[:, 2],
                cells[:, 1] + chunk.pos.z * 16,
            )).astype(np.float32)
            face_vertices = np.asarray(corners, dtype=np.float32)
            positions.append((xyz[:, None, :] + face_vertices[None, :, :]).reshape(-1, 3))
            block_ids = blocks[visible].astype(np.int64)
            face_colors = np.asarray([_block_color(int(i)) for i in block_ids], dtype=np.float32)
            colors.append(np.repeat(face_colors, 4, axis=0))
            face_indices = np.asarray((0, 1, 2, 0, 2, 3), dtype=np.uint32)
            per_block = np.arange(len(cells), dtype=np.uint32)[:, None] * 4
            indices.append((per_block + face_indices[None, :] + base_vertex).reshape(-1))
            base_vertex += len(cells) * 4

        if not positions:
            return MeshData(np.empty((0, 3), np.float32),
                            np.empty((0, 3), np.float32),
                            np.empty((0,), np.uint32))
        return MeshData(np.concatenate(positions), np.concatenate(colors),
                        np.concatenate(indices))


__all__ = ["MeshData", "ChunkMeshBuilder"]
