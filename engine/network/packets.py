"""Typed packet payload builders for common protocol-340 play actions."""
from __future__ import annotations

import struct
from dataclasses import dataclass

from engine.core import BlockPos, EnumFacing
from engine.network.codec import PacketBuffer, ProtocolError
from engine.network.connection import ConnectionState, PACKET_IDS


def serverbound_chat(message: str) -> tuple[int, bytes]:
    if not isinstance(message, str) or len(message) > 100:
        raise ValueError("chat message must contain at most 100 characters")
    payload = PacketBuffer()
    payload.write_string(message, max_chars=100)
    return PACKET_IDS[ConnectionState.PLAY]["serverbound_chat"], payload.to_bytes()


def serverbound_keep_alive(keep_alive_id: int) -> tuple[int, bytes]:
    payload = PacketBuffer()
    payload.write_varint(keep_alive_id)
    return PACKET_IDS[ConnectionState.PLAY]["serverbound_keep_alive"], payload.to_bytes()


def serverbound_player(on_ground: bool) -> tuple[int, bytes]:
    if not isinstance(on_ground, bool):
        raise TypeError("on_ground must be bool")
    return PACKET_IDS[ConnectionState.PLAY]["serverbound_player"], bytes([int(on_ground)])


def serverbound_position(x: float, y: float, z: float,
                         on_ground: bool) -> tuple[int, bytes]:
    if not all(isinstance(v, (int, float)) for v in (x, y, z)):
        raise TypeError("player coordinates must be numeric")
    if not isinstance(on_ground, bool):
        raise TypeError("on_ground must be bool")
    return (PACKET_IDS[ConnectionState.PLAY]["serverbound_position"],
            struct.pack(">ddd?", float(x), float(y), float(z), on_ground))


def serverbound_position_look(x: float, y: float, z: float, yaw: float,
                              pitch: float, on_ground: bool) -> tuple[int, bytes]:
    if not isinstance(on_ground, bool):
        raise TypeError("on_ground must be bool")
    values = (x, y, z, yaw, pitch)
    if not all(isinstance(v, (int, float)) for v in values):
        raise TypeError("position and rotation values must be numeric")
    return (PACKET_IDS[ConnectionState.PLAY]["serverbound_position_look"],
            struct.pack(">dddff?", float(x), float(y), float(z),
                        float(yaw), float(pitch), on_ground))


def serverbound_look(yaw: float, pitch: float,
                     on_ground: bool) -> tuple[int, bytes]:
    if not isinstance(on_ground, bool):
        raise TypeError("on_ground must be bool")
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
class ChunkDataPacket:
    chunk_x: int
    chunk_z: int
    ground_up: bool
    primary_bitmask: int
    data: bytes


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


def decode_clientbound_chunk_data(payload: bytes) -> ChunkDataPacket:
    buffer = PacketBuffer(payload)
    chunk_x, chunk_z = struct.unpack(">ii", buffer.read(8))
    ground_up = buffer.read(1)[0]
    if ground_up not in (0, 1):
        raise ProtocolError("invalid chunk ground-up flag")
    bitmask = buffer.read_varint()
    data_length = buffer.read_varint()
    if bitmask < 0 or data_length < 0 or data_length > buffer.remaining:
        raise ProtocolError("invalid chunk data length or bitmask")
    chunk_data = buffer.read(data_length)
    # Block-entity NBT compounds follow this byte array. Keep the remainder
    # opaque until the complete tile-entity schema is available.
    return ChunkDataPacket(chunk_x, chunk_z, bool(ground_up), bitmask,
                           chunk_data + buffer.read_remaining())


def decode_clientbound_keep_alive(payload: bytes) -> int:
    buffer = PacketBuffer(payload)
    value = buffer.read_varint()
    if buffer.remaining:
        raise ProtocolError("trailing keep-alive payload")
    return value


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
           "JoinGamePacket", "PlayerPositionLookPacket", "ChunkDataPacket",
           "decode_clientbound_join_game", "decode_clientbound_player_position_look",
           "decode_clientbound_chunk_data"]
