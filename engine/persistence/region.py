"""Anvil .mca region-file reader/writer (Minecraft Java 1.12.2)."""
from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path

from engine.core.nbt import NBTDocument, NBTError, read_nbt, write_nbt

SECTOR_BYTES = 4096
HEADER_BYTES = 8192
SECTOR_INTS = 1024
COMPRESSION_GZIP = 1
COMPRESSION_ZLIB = 2
COMPRESSION_NONE = 3


class RegionError(ValueError):
    """Invalid Anvil region data."""


def region_coordinates(chunk_x: int, chunk_z: int) -> tuple[int, int, int]:
    return chunk_x >> 5, chunk_z >> 5, (chunk_x & 31) + (chunk_z & 31) * 32


class RegionFile:
    """Random-access region file with validated sector allocation."""

    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)

    @staticmethod
    def _read_location_table(data: bytes):
        if len(data) < HEADER_BYTES:
            raise RegionError("region file is smaller than its 8 KiB header")
        locations = []
        used = set()
        file_sectors = (len(data) + SECTOR_BYTES - 1) // SECTOR_BYTES
        for index in range(SECTOR_INTS):
            offset, count = struct.unpack_from(">I", data, index * 4)[0] >> 8, data[index * 4 + 3]
            if offset == 0 and count == 0:
                locations.append((0, 0))
                continue
            if offset < 2 or count == 0 or offset + count > file_sectors:
                raise RegionError(f"invalid location entry {index}")
            sectors = set(range(offset, offset + count))
            if used.intersection(sectors):
                raise RegionError("overlapping chunk sector allocations")
            used.update(sectors)
            locations.append((offset, count))
        return locations

    def read_chunk(self, local_x: int, local_z: int) -> NBTDocument | None:
        if not (0 <= local_x < 32 and 0 <= local_z < 32):
            raise ValueError("local chunk coordinates must be 0..31")
        if not self.path.exists():
            return None
        data = self.path.read_bytes()
        locations = self._read_location_table(data)
        index = local_x + local_z * 32
        offset, sectors = locations[index]
        if not offset:
            return None
        start = offset * SECTOR_BYTES
        length = struct.unpack_from(">I", data, start)[0]
        if length < 1 or length > sectors * SECTOR_BYTES - 4:
            raise RegionError("invalid chunk payload length")
        compression = data[start + 4]
        payload = data[start + 5:start + 4 + length]
        try:
            if compression == COMPRESSION_GZIP:
                return read_nbt(payload, compression="gzip")
            if compression == COMPRESSION_ZLIB:
                return read_nbt(payload, compression="zlib")
            if compression == COMPRESSION_NONE:
                return read_nbt(payload)
        except (NBTError, OSError, zlib.error) as exc:
            raise RegionError("invalid chunk NBT payload") from exc
        raise RegionError(f"unknown chunk compression type: {compression}")

    def write_chunk(self, local_x: int, local_z: int, document: NBTDocument | dict,
                    *, timestamp: int | None = None) -> None:
        if not (0 <= local_x < 32 and 0 <= local_z < 32):
            raise ValueError("local chunk coordinates must be 0..31")
        if timestamp is None:
            import time
            timestamp = int(time.time())
        if isinstance(timestamp, bool) or not isinstance(timestamp, int) or not 0 <= timestamp <= 0xFFFFFFFF:
            raise ValueError("timestamp must be an unsigned 32-bit integer")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        old = self.path.read_bytes() if self.path.exists() else bytes(HEADER_BYTES)
        if len(old) < HEADER_BYTES:
            raise RegionError("region file is smaller than its header")
        locations = self._read_location_table(old)
        index = local_x + local_z * 32

        # Rebuild a compact file, preserving every other allocated chunk.
        payloads = {}
        times = []
        for i, (offset, sectors) in enumerate(locations):
            times.append(struct.unpack_from(">I", old, SECTOR_BYTES + i * 4)[0])
            if not offset or i == index:
                payloads[i] = None
                continue
            start = offset * SECTOR_BYTES
            length = struct.unpack_from(">I", old, start)[0]
            if length < 1 or length > sectors * SECTOR_BYTES - 4:
                raise RegionError(f"invalid chunk length in slot {i}")
            payloads[i] = old[start:start + 4 + length]

        raw = write_nbt(document)
        compressed = zlib.compress(raw)
        record = struct.pack(">I", len(compressed) + 1) + bytes([COMPRESSION_ZLIB]) + compressed
        sector_count = (len(record) + SECTOR_BYTES - 1) // SECTOR_BYTES
        if sector_count > 255:
            raise RegionError("chunk exceeds Anvil 255-sector limit")
        payloads[index] = record
        times[index] = timestamp

        output = bytearray(HEADER_BYTES)
        next_sector = 2
        for i in range(SECTOR_INTS):
            record_data = payloads.get(i)
            if record_data is None:
                continue
            count = (len(record_data) + SECTOR_BYTES - 1) // SECTOR_BYTES
            if count > 255 or next_sector > 0xFFFFFF or next_sector + count > 0x1000000:
                raise RegionError("region file sector allocation overflow")
            struct.pack_into(">I", output, i * 4, (next_sector << 8) | count)
            padded = record_data + bytes(count * SECTOR_BYTES - len(record_data))
            output.extend(padded)
            next_sector += count
        for i, stamp in enumerate(times):
            struct.pack_into(">I", output, SECTOR_BYTES + i * 4, stamp)

        temp = self.path.with_name(self.path.name + ".tmp")
        try:
            with open(temp, "wb") as handle:
                handle.write(output)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.path)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass


__all__ = ["RegionError", "RegionFile", "region_coordinates",
           "SECTOR_BYTES", "HEADER_BYTES", "COMPRESSION_GZIP",
           "COMPRESSION_ZLIB", "COMPRESSION_NONE"]
