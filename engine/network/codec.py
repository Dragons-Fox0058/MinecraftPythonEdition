"""Minecraft Java Edition 1.12.2 (protocol 340) packet primitives."""
from __future__ import annotations

import struct
import uuid
import zlib


PROTOCOL_VERSION = 340
MAX_PACKET_LENGTH = 2 * 1024 * 1024


class ProtocolError(ValueError):
    """Malformed Minecraft protocol data."""


class PacketBuffer:
    def __init__(self, data: bytes = b""):
        self.data = bytearray(data)
        self.offset = 0

    @property
    def remaining(self) -> int:
        return len(self.data) - self.offset

    def read(self, size: int) -> bytes:
        if size < 0 or size > self.remaining:
            raise ProtocolError("packet ended unexpectedly")
        result = bytes(self.data[self.offset:self.offset + size])
        self.offset += size
        return result

    def write(self, value: bytes) -> None:
        self.data.extend(value)

    def read_varint(self) -> int:
        result = 0
        for index in range(5):
            byte = self.read(1)[0]
            result |= (byte & 0x7F) << (7 * index)
            if not byte & 0x80:
                if result & (1 << 31):
                    result -= 1 << 32
                return result
        raise ProtocolError("VarInt exceeds five bytes")

    def write_varint(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or not -(1 << 31) <= value < (1 << 31):
            raise ValueError("VarInt must be a signed 32-bit integer")
        value &= 0xFFFFFFFF
        while True:
            if value & ~0x7F == 0:
                self.write(bytes([value]))
                return
            self.write(bytes([(value & 0x7F) | 0x80]))
            value >>= 7

    def read_string(self, max_chars: int = 32767) -> str:
        length = self.read_varint()
        if length < 0 or length > max_chars * 4:
            raise ProtocolError("invalid protocol string length")
        try:
            value = self.read(length).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolError("invalid UTF-8 protocol string") from exc
        if len(value) > max_chars:
            raise ProtocolError("protocol string exceeds character limit")
        return value

    def write_string(self, value: str, max_chars: int = 32767) -> None:
        if not isinstance(value, str) or len(value) > max_chars:
            raise ValueError("protocol string exceeds character limit")
        encoded = value.encode("utf-8")
        if len(encoded) > max_chars * 4:
            raise ValueError("encoded protocol string is too long")
        self.write_varint(len(encoded))
        self.write(encoded)

    def read_uuid(self) -> uuid.UUID:
        return uuid.UUID(bytes=self.read(16))

    def write_uuid(self, value: uuid.UUID) -> None:
        if not isinstance(value, uuid.UUID):
            raise TypeError("value must be UUID")
        self.write(value.bytes)

    def read_position(self) -> tuple[int, int, int]:
        raw = struct.unpack(">Q", self.read(8))[0]
        x = raw >> 38
        y = raw & 0xFFF
        z = (raw >> 12) & 0x3FFFFFF
        if x >= 1 << 25: x -= 1 << 26
        if y >= 1 << 11: y -= 1 << 12
        if z >= 1 << 25: z -= 1 << 26
        return x, y, z

    def write_position(self, x: int, y: int, z: int) -> None:
        if not (-(1 << 25) <= x < (1 << 25) and -(1 << 11) <= y < (1 << 11)
                and -(1 << 25) <= z < (1 << 25)):
            raise ValueError("block position outside protocol packed range")
        raw = ((x & 0x3FFFFFF) << 38) | ((z & 0x3FFFFFF) << 12) | (y & 0xFFF)
        self.write(struct.pack(">Q", raw))

    def read_remaining(self) -> bytes:
        return self.read(self.remaining)

    def to_bytes(self) -> bytes:
        return bytes(self.data)


def encode_packet(packet_id: int, payload: bytes = b"") -> bytes:
    body = PacketBuffer()
    body.write_varint(packet_id)
    body.write(payload)
    encoded = body.to_bytes()
    if len(encoded) > MAX_PACKET_LENGTH:
        raise ProtocolError("packet exceeds maximum length")
    frame = PacketBuffer()
    frame.write_varint(len(encoded))
    frame.write(encoded)
    return frame.to_bytes()


def decode_packet(frame: bytes, *, max_length: int = MAX_PACKET_LENGTH) -> tuple[int, bytes]:
    buffer = PacketBuffer(frame)
    length = buffer.read_varint()
    if length < 1 or length > max_length or length != buffer.remaining:
        raise ProtocolError("invalid packet frame length")
    packet = PacketBuffer(buffer.read(length))
    packet_id = packet.read_varint()
    if packet_id < 0:
        raise ProtocolError("negative packet ID")
    return packet_id, packet.read_remaining()


def encode_compressed_packet(packet_id: int, payload: bytes, threshold: int) -> bytes:
    if threshold < 0:
        raise ValueError("compression threshold must be non-negative")
    body = PacketBuffer()
    body.write_varint(packet_id)
    body.write(payload)
    raw = body.to_bytes()
    inner = PacketBuffer()
    if len(raw) >= threshold:
        inner.write_varint(len(raw))
        inner.write(zlib.compress(raw))
    else:
        inner.write_varint(0)
        inner.write(raw)
    encoded = inner.to_bytes()
    outer = PacketBuffer()
    outer.write_varint(len(encoded))
    outer.write(encoded)
    return outer.to_bytes()


def decode_compressed_packet(frame: bytes, threshold: int,
                             *, max_length: int = MAX_PACKET_LENGTH) -> tuple[int, bytes]:
    outer = PacketBuffer(frame)
    length = outer.read_varint()
    if length < 1 or length > max_length or length != outer.remaining:
        raise ProtocolError("invalid compressed frame length")
    inner = PacketBuffer(outer.read(length))
    uncompressed_length = inner.read_varint()
    encoded = inner.read_remaining()
    if uncompressed_length == 0:
        if len(encoded) >= threshold:
            raise ProtocolError("packet should have been compressed")
        raw = encoded
    else:
        if uncompressed_length < threshold or uncompressed_length > max_length:
            raise ProtocolError("invalid uncompressed packet length")
        try:
            decompressor = zlib.decompressobj()
            raw = decompressor.decompress(encoded, max_length + 1)
            raw += decompressor.flush()
        except zlib.error as exc:
            raise ProtocolError("invalid compressed packet payload") from exc
        if len(raw) != uncompressed_length or len(raw) > max_length or not decompressor.eof:
            raise ProtocolError("compressed packet length mismatch")
    packet = PacketBuffer(raw)
    packet_id = packet.read_varint()
    if packet_id < 0:
        raise ProtocolError("negative packet ID")
    return packet_id, packet.read_remaining()


__all__ = ["PROTOCOL_VERSION", "MAX_PACKET_LENGTH", "ProtocolError",
           "PacketBuffer", "encode_packet", "decode_packet",
           "encode_compressed_packet", "decode_compressed_packet"]
