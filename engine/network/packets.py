"""Typed packet payload builders for common protocol-340 play actions."""
from __future__ import annotations

import struct

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
           "decode_clientbound_keep_alive", "decode_clientbound_chat"]
