"""Minecraft Java 1.12.2 chunk NBT serialization."""
from __future__ import annotations

import numpy as np

from engine.core import ChunkPos
from engine.core.nbt import (NBTDocument, NBTTag, NBTList, NBTError, TAG_BYTE, TAG_INT, TAG_LONG, TAG_COMPOUND)
from engine.world.chunk import Chunk


class ChunkFormatError(ValueError):
    """Invalid or unsupported 1.12.2 chunk NBT."""


def _pack_nibbles(values: np.ndarray) -> bytes:
    flat = np.asarray(values, dtype=np.uint8).reshape(-1)
    if len(flat) % 2:
        raise ValueError("nibble array length must be even")
    return bytes((flat[0::2] & 0x0F) | ((flat[1::2] & 0x0F) << 4))


def _unpack_nibbles(data: bytes, count: int) -> np.ndarray:
    if len(data) != (count + 1) // 2:
        raise ChunkFormatError("invalid nibble array length")
    raw = np.frombuffer(data, dtype=np.uint8)
    result = np.empty(count, dtype=np.uint8)
    result[0::2] = raw & 0x0F
    result[1::2] = raw >> 4
    return result


def chunk_to_nbt(chunk: Chunk, *, last_update: int = 0,
                 inhabited_time: int = 0, terrain_populated: bool = True,
                 light_populated: bool = True) -> NBTDocument:
    if not isinstance(chunk, Chunk):
        raise TypeError("chunk must be Chunk")
    sections = []
    for section_y in range(16):
        y0 = section_y * 16
        block_ids = np.empty(4096, dtype=np.uint16)
        metadata = np.empty(4096, dtype=np.uint8)
        block_light = np.empty(4096, dtype=np.uint8)
        sky_light = np.empty(4096, dtype=np.uint8)
        index = 0
        for y in range(y0, y0 + 16):
            for z in range(16):
                for x in range(16):
                    state = int(chunk.blocks[x, z, y])
                    block_ids[index] = (state >> 4) & 0xFFF
                    metadata[index] = state & 0xF
                    light = int(chunk.light[x, z, y])
                    block_light[index] = light & 0xF
                    sky_light[index] = (light >> 4) & 0xF
                    index += 1
        if not np.any(block_ids) and not np.any(block_light) and not np.any(sky_light):
            continue
        blocks = (block_ids & 0xFF).astype(np.uint8).tobytes()
        add = (block_ids >> 8).astype(np.uint8)
        section = {
            "Y": NBTTag(TAG_BYTE, section_y),
            "Blocks": blocks,
            "Data": _pack_nibbles(metadata),
            "BlockLight": _pack_nibbles(block_light),
            "SkyLight": _pack_nibbles(sky_light),
        }
        if np.any(add):
            section["Add"] = _pack_nibbles(add)
        sections.append(section)

    level = {
        "xPos": NBTTag(TAG_INT, int(chunk.pos.x)),
        "zPos": NBTTag(TAG_INT, int(chunk.pos.z)),
        "LastUpdate": NBTTag(TAG_LONG, int(last_update)),
        "InhabitedTime": NBTTag(TAG_LONG, int(inhabited_time)),
        "TerrainPopulated": NBTTag(TAG_BYTE, 1 if terrain_populated else 0),
        "LightPopulated": NBTTag(TAG_BYTE, 1 if light_populated else 0),
        "V": NBTTag(TAG_BYTE, 1),
        "Sections": NBTList(TAG_COMPOUND, tuple(sections)),
        "Biomes": bytes(256),
        "HeightMap": tuple(0 for _ in range(256)),
        "Entities": NBTList(TAG_COMPOUND, ()),
        "TileEntities": NBTList(TAG_COMPOUND, ()),
        "TileTicks": NBTList(TAG_COMPOUND, ()),
    }
    return NBTDocument("", {"Level": level})


def chunk_from_nbt(document: NBTDocument, *, expected_pos: ChunkPos | None = None) -> Chunk:
    if not isinstance(document, NBTDocument):
        raise TypeError("document must be NBTDocument")
    try:
        level = document.value["Level"]
        cx, cz = int(level["xPos"]), int(level["zPos"])
        raw_sections = level["Sections"]
        if not isinstance(raw_sections, NBTList) or raw_sections.tag_type != TAG_COMPOUND:
            raise ChunkFormatError("Sections must be a compound list")
        if expected_pos is not None and (cx, cz) != (expected_pos.x, expected_pos.z):
            raise ChunkFormatError("chunk coordinates do not match expected position")
        chunk = Chunk(ChunkPos(cx, cz))
        seen = set()
        for section in raw_sections.values:
            sy = int(section["Y"])
            if not 0 <= sy < 16 or sy in seen:
                raise ChunkFormatError("invalid or duplicate section Y")
            seen.add(sy)
            blocks = np.frombuffer(section["Blocks"], dtype=np.uint8)
            if blocks.size != 4096:
                raise ChunkFormatError("Blocks must contain 4096 bytes")
            data = _unpack_nibbles(section["Data"], 4096)
            block_light = _unpack_nibbles(section["BlockLight"], 4096)
            sky_light = _unpack_nibbles(section["SkyLight"], 4096)
            add = (_unpack_nibbles(section["Add"], 4096)
                   if "Add" in section else np.zeros(4096, dtype=np.uint8))
            ids = blocks.astype(np.uint16) | (add.astype(np.uint16) << 8)
            states = (ids << 4) | data.astype(np.uint16)
            index = 0
            for y in range(sy * 16, sy * 16 + 16):
                for z in range(16):
                    for x in range(16):
                        chunk.blocks[x, z, y] = states[index]
                        chunk.light[x, z, y] = (int(sky_light[index]) << 4) | int(block_light[index])
                        index += 1
        chunk.clear_dirty()
        return chunk
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        if isinstance(exc, ChunkFormatError):
            raise
        raise ChunkFormatError("malformed 1.12.2 chunk NBT") from exc


__all__ = ["ChunkFormatError", "chunk_to_nbt", "chunk_from_nbt"]
