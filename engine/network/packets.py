"""Typed packet payload builders for common protocol-340 play actions."""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass

from engine.core import BlockPos, EnumFacing
from engine.network.codec import PacketBuffer, ProtocolError
from engine.network.connection import ConnectionState, PACKET_IDS


def serverbound_chat(message: str) -> tuple[int, bytes]:
    if not isinstance(message, str) or len(message) > 256:
        raise ValueError("chat message must contain at most 256 characters")
    payload = PacketBuffer()
    payload.write_string(message, max_chars=256)
    return PACKET_IDS[ConnectionState.PLAY]["serverbound_chat"], payload.to_bytes()


def serverbound_keep_alive(keep_alive_id: int) -> tuple[int, bytes]:
    if (isinstance(keep_alive_id, bool) or not isinstance(keep_alive_id, int)
            or not -(1 << 63) <= keep_alive_id < (1 << 63)):
        raise ValueError("keep_alive_id must be a signed 64-bit integer")
    return (PACKET_IDS[ConnectionState.PLAY]["serverbound_keep_alive"],
            struct.pack(">q", keep_alive_id))


def serverbound_player(on_ground: bool) -> tuple[int, bytes]:
    if not isinstance(on_ground, bool):
        raise TypeError("on_ground must be bool")
    return PACKET_IDS[ConnectionState.PLAY]["serverbound_player"], bytes([int(on_ground)])


def serverbound_position(x: float, y: float, z: float,
                         on_ground: bool) -> tuple[int, bytes]:
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
               and math.isfinite(v) for v in (x, y, z)):
        raise ValueError("player coordinates must be finite numbers")
    if not isinstance(on_ground, bool):
        raise TypeError("on_ground must be bool")
    return (PACKET_IDS[ConnectionState.PLAY]["serverbound_position"],
            struct.pack(">ddd?", float(x), float(y), float(z), on_ground))


def serverbound_position_look(x: float, y: float, z: float, yaw: float,
                              pitch: float, on_ground: bool) -> tuple[int, bytes]:
    if not isinstance(on_ground, bool):
        raise TypeError("on_ground must be bool")
    values = (x, y, z, yaw, pitch)
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
               and math.isfinite(v) for v in values):
        raise ValueError("position and rotation values must be finite numbers")
    return (PACKET_IDS[ConnectionState.PLAY]["serverbound_position_look"],
            struct.pack(">dddff?", float(x), float(y), float(z),
                        float(yaw), float(pitch), on_ground))


def serverbound_look(yaw: float, pitch: float,
                     on_ground: bool) -> tuple[int, bytes]:
    if not isinstance(on_ground, bool):
        raise TypeError("on_ground must be bool")
    if (not isinstance(yaw, (int, float)) or isinstance(yaw, bool)
            or not isinstance(pitch, (int, float)) or isinstance(pitch, bool)
            or not math.isfinite(yaw) or not math.isfinite(pitch)):
        raise ValueError("yaw and pitch must be finite numbers")
    return (PACKET_IDS[ConnectionState.PLAY]["serverbound_look"],
            struct.pack(">ff?", float(yaw), float(pitch), on_ground))


def serverbound_held_item(slot: int) -> tuple[int, bytes]:
    if isinstance(slot, bool) or not isinstance(slot, int) or not 0 <= slot <= 8:
        raise ValueError("held hotbar slot must be 0..8")
    return PACKET_IDS[ConnectionState.PLAY]["serverbound_held_item"], struct.pack(">h", slot)


def serverbound_digging(status: int, pos: BlockPos, face: EnumFacing) -> tuple[int, bytes]:
    if isinstance(status, bool) or not isinstance(status, int) or not 0 <= status <= 6:
        raise ValueError("digging status must be 0..6")
    if not isinstance(pos, BlockPos) or not isinstance(face, EnumFacing):
        raise TypeError("pos and face must be BlockPos and EnumFacing")
    payload = PacketBuffer()
    payload.write_varint(status)
    payload.write_position(pos.x, pos.y, pos.z)
    payload.write(bytes([face.value]))
    return PACKET_IDS[ConnectionState.PLAY]["serverbound_digging"], payload.to_bytes()


@dataclass(frozen=True)
class JoinGamePacket:
    entity_id: int
    game_mode: int
    dimension: int
    difficulty: int
    max_players: int
    level_type: str
    reduced_debug_info: bool


@dataclass(frozen=True)
class PlayerPositionLookPacket:
    x: float
    y: float
    z: float
    yaw: float
    pitch: float
    flags: int
    teleport_id: int


@dataclass(frozen=True)
class ChunkSectionData:
    section_y: int
    block_states: tuple[int, ...]
    block_light: bytes
    sky_light: bytes


@dataclass(frozen=True)
class ChunkDataPacket:
    chunk_x: int
    chunk_z: int
    ground_up: bool
    primary_bitmask: int
    data: bytes
    sections: tuple[ChunkSectionData, ...]
    biomes: bytes | None
    block_entity_count: int
    block_entities_payload: bytes


def decode_clientbound_join_game(payload: bytes) -> JoinGamePacket:
    buffer = PacketBuffer(payload)
    entity_id = struct.unpack(">i", buffer.read(4))[0]
    game_mode = buffer.read(1)[0]
    dimension = struct.unpack(">i", buffer.read(4))[0]
    difficulty = buffer.read(1)[0]
    max_players = buffer.read(1)[0]
    level_type = buffer.read_string(max_chars=16)
    reduced = buffer.read(1)[0]
    if reduced not in (0, 1) or buffer.remaining:
        raise ProtocolError("invalid Join Game payload")
    return JoinGamePacket(entity_id, game_mode, dimension, difficulty,
                          max_players, level_type, bool(reduced))


def decode_clientbound_player_position_look(payload: bytes) -> PlayerPositionLookPacket:
    buffer = PacketBuffer(payload)
    x, y, z = struct.unpack(">ddd", buffer.read(24))
    yaw, pitch = struct.unpack(">ff", buffer.read(8))
    flags = buffer.read(1)[0]
    teleport_id = buffer.read_varint()
    if buffer.remaining:
        raise ProtocolError("trailing Player Position And Look payload")
    return PlayerPositionLookPacket(x, y, z, yaw, pitch, flags, teleport_id)


def decode_clientbound_chunk_data(payload: bytes, *, has_sky_light: bool = True) -> ChunkDataPacket:
    if not isinstance(has_sky_light, bool):
        raise TypeError("has_sky_light must be bool")
    buffer = PacketBuffer(payload)
    chunk_x, chunk_z = struct.unpack(">ii", buffer.read(8))
    ground_up = buffer.read(1)[0]
    if ground_up not in (0, 1):
        raise ProtocolError("invalid chunk ground-up flag")
    bitmask = buffer.read_varint()
    data_length = buffer.read_varint()
    if bitmask < 0 or bitmask > 0xFFFF or data_length < 0 or data_length > buffer.remaining:
        raise ProtocolError("invalid chunk data length or primary bitmask")
    chunk_data = buffer.read(data_length)
    section_buffer = PacketBuffer(chunk_data)
    sections = []
    for section_y in range(16):
        if not (bitmask & (1 << section_y)):
            continue
        bits_per_block = section_buffer.read(1)[0]
        if not 4 <= bits_per_block <= 16:
            raise ProtocolError("invalid chunk section bits-per-block")
        palette = None
        palette_length = section_buffer.read_varint()
        if bits_per_block <= 8:
            if not 1 <= palette_length <= (1 << bits_per_block):
                raise ProtocolError("invalid indirect chunk palette length")
            palette = tuple(section_buffer.read_varint() for _ in range(palette_length))
            if any(value < 0 or value > 0xFFFF for value in palette):
                raise ProtocolError("chunk palette state ID is out of range")
        elif palette_length != 0:
            raise ProtocolError("direct chunk palette must have zero entries")
        long_count = section_buffer.read_varint()
        expected_longs = 64 * bits_per_block
        if long_count != expected_longs:
            raise ProtocolError("invalid compacted chunk data array length")
        packed = struct.unpack(">" + "Q" * long_count,
                               section_buffer.read(long_count * 8))
        value_mask = (1 << bits_per_block) - 1
        states = []
        for index in range(4096):
            bit_index = index * bits_per_block
            long_index = bit_index >> 6
            bit_offset = bit_index & 63
            value = packed[long_index] >> bit_offset
            if bit_offset + bits_per_block > 64:
                value |= packed[long_index + 1] << (64 - bit_offset)
            value &= value_mask
            if palette is not None:
                if value >= len(palette):
                    raise ProtocolError("chunk palette index is out of range")
                value = palette[value]
            states.append(value)
        block_light = section_buffer.read(2048)
        sky_light = section_buffer.read(2048) if has_sky_light else b""
        sections.append(ChunkSectionData(section_y, tuple(states), block_light, sky_light))
    biomes = section_buffer.read(256) if ground_up else None
    if section_buffer.remaining:
        raise ProtocolError("trailing chunk section data")
    block_entity_count = buffer.read_varint()
    if not 0 <= block_entity_count <= 4096:
        raise ProtocolError("invalid chunk block-entity count")
    block_entities_payload = buffer.read_remaining()
    return ChunkDataPacket(
        chunk_x, chunk_z, bool(ground_up), bitmask, chunk_data,
        tuple(sections), biomes, block_entity_count, block_entities_payload,
    )


def decode_clientbound_keep_alive(payload: bytes) -> int:
    if len(payload) != 8:
        raise ProtocolError("Keep Alive payload must be exactly 8 bytes")
    return struct.unpack(">q", payload)[0]


def decode_clientbound_chat(payload: bytes) -> tuple[str, int]:
    buffer = PacketBuffer(payload)
    message = buffer.read_string()
    position = buffer.read(1)[0]
    if position not in (0, 1, 2) or buffer.remaining:
        raise ProtocolError("invalid chat message payload")
    return message, position


__all__ = ["serverbound_chat", "serverbound_keep_alive", "serverbound_player",
           "serverbound_position", "serverbound_position_look", "serverbound_look",
           "serverbound_held_item", "serverbound_digging",
           "decode_clientbound_keep_alive", "decode_clientbound_chat",
           "JoinGamePacket", "PlayerPositionLookPacket", "ChunkSectionData", "ChunkDataPacket",
           "decode_clientbound_join_game", "decode_clientbound_player_position_look",
           "decode_clientbound_chunk_data"]
