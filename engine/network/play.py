"""Protocol-340 play-state packet codecs and a small safe dispatcher.

Only packet layouts implemented below are registered. Unknown packet IDs remain
available to callers and are never guessed or silently decoded.
"""
from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from typing import Callable

from engine.network.codec import PacketBuffer, ProtocolError


# Protocol 340 (Java Edition 1.12.2), Play state.
SERVERBOUND = {
    "teleport_confirm": 0x00,
    "chat": 0x02,
    "client_status": 0x03,
    "client_settings": 0x04,
    "keep_alive": 0x0B,
    "player": 0x0C,
    "player_position": 0x0D,
    "player_position_look": 0x0E,
    "player_look": 0x0F,
    "player_digging": 0x13,
    "held_item_change": 0x19,
}
CLIENTBOUND = {
    "chat": 0x0F,
    "window_items": 0x14,
    "set_slot": 0x16,
    "disconnect": 0x1A,
    "unload_chunk": 0x1D,
    "keep_alive": 0x1F,
    "chunk_data": 0x20,
    "join_game": 0x23,
    "player_abilities": 0x2B,
    "player_position_look": 0x2F,
    "respawn": 0x35,
    "update_health": 0x41,
    "time_update": 0x47,
    "block_change": 0x0B,
}


def serverbound_teleport_confirm(teleport_id: int) -> tuple[int, bytes]:
    if isinstance(teleport_id, bool) or not isinstance(teleport_id, int) or teleport_id < 0:
        raise ValueError("teleport_id must be a non-negative integer")
    out = PacketBuffer()
    out.write_varint(teleport_id)
    return SERVERBOUND["teleport_confirm"], out.to_bytes()


def serverbound_client_status(action: int) -> tuple[int, bytes]:
    # 0 = respawn, 1 = request statistics, 2 = open inventory achievement (legacy).
    if isinstance(action, bool) or not isinstance(action, int) or action not in (0, 1, 2):
        raise ValueError("client status action must be 0, 1, or 2")
    out = PacketBuffer()
    out.write_varint(action)
    return SERVERBOUND["client_status"], out.to_bytes()


def serverbound_client_settings(locale: str = "en_US", view_distance: int = 10,
                                chat_mode: int = 0, chat_colors: bool = True,
                                skin_parts: int = 0x7F, main_hand: int = 1
                                ) -> tuple[int, bytes]:
    if not isinstance(locale, str) or not 1 <= len(locale) <= 16:
        raise ValueError("locale must contain 1..16 characters")
    if isinstance(view_distance, bool) or not isinstance(view_distance, int) or not -1 <= view_distance <= 32:
        raise ValueError("view_distance must be -1..32")
    if isinstance(chat_mode, bool) or not isinstance(chat_mode, int) or chat_mode not in (0, 1, 2):
        raise ValueError("chat_mode must be 0, 1, or 2")
    if not isinstance(chat_colors, bool):
        raise TypeError("chat_colors must be bool")
    if isinstance(skin_parts, bool) or not isinstance(skin_parts, int) or not 0 <= skin_parts <= 0x7F:
        raise ValueError("skin_parts must be a 7-bit mask")
    if isinstance(main_hand, bool) or not isinstance(main_hand, int) or main_hand not in (0, 1):
        raise ValueError("main_hand must be 0 or 1")
    out = PacketBuffer()
    out.write_string(locale, max_chars=16)
    out.write(struct.pack(">b", view_distance))
    out.write_varint(chat_mode)
    out.write(bytes((int(chat_colors), skin_parts)))
    out.write_varint(main_hand)
    return SERVERBOUND["client_settings"], out.to_bytes()


@dataclass(frozen=True)
class BlockChange:
    x: int
    y: int
    z: int
    state_id: int


@dataclass(frozen=True)
class UnloadChunk:
    chunk_x: int
    chunk_z: int


@dataclass(frozen=True)
class Disconnect:
    reason: object


@dataclass(frozen=True)
class UpdateHealth:
    health: float
    food: int
    food_saturation: float


@dataclass(frozen=True)
class TimeUpdate:
    world_age: int
    time_of_day: int


@dataclass(frozen=True)
class PlayerAbilities:
    flags: int
    flying_speed: float
    walking_speed: float


def decode_block_change(payload: bytes) -> BlockChange:
    buf = PacketBuffer(payload)
    x, y, z = buf.read_position()
    state_id = buf.read_varint()
    if state_id < 0 or buf.remaining:
        raise ProtocolError("invalid Block Change payload")
    return BlockChange(x, y, z, state_id)


def decode_unload_chunk(payload: bytes) -> UnloadChunk:
    if len(payload) != 8:
        raise ProtocolError("Unload Chunk payload must be exactly 8 bytes")
    return UnloadChunk(*struct.unpack(">ii", payload))


def decode_disconnect(payload: bytes) -> Disconnect:
    buf = PacketBuffer(payload)
    raw = buf.read_string()
    if buf.remaining:
        raise ProtocolError("trailing Disconnect payload")
    try:
        reason = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProtocolError("Disconnect reason is not valid chat-component JSON") from exc
    if not isinstance(reason, (dict, list, str)):
        raise ProtocolError("Disconnect reason must be a chat component")
    return Disconnect(reason)


def decode_update_health(payload: bytes) -> UpdateHealth:
    # 1.12.2 encodes food as a VarInt, not a fixed-width 32-bit integer.
    buf = PacketBuffer(payload)
    health = struct.unpack(">f", buf.read(4))[0]
    food = buf.read_varint()
    saturation = struct.unpack(">f", buf.read(4))[0]
    if buf.remaining or not math.isfinite(health) or not math.isfinite(saturation) or food < 0:
        raise ProtocolError("invalid Update Health payload")
    return UpdateHealth(health, food, saturation)


def decode_time_update(payload: bytes) -> TimeUpdate:
    if len(payload) != 16:
        raise ProtocolError("Time Update payload must be exactly 16 bytes")
    return TimeUpdate(*struct.unpack(">qq", payload))


def decode_player_abilities(payload: bytes) -> PlayerAbilities:
    if len(payload) != 9:
        raise ProtocolError("Player Abilities payload must be exactly 9 bytes")
    flags, flying, walking = struct.unpack(">Bff", payload)
    if flags & ~0x0F or not math.isfinite(flying) or not math.isfinite(walking):
        raise ProtocolError("invalid Player Abilities values")
    return PlayerAbilities(flags, flying, walking)


class PlayPacketDispatcher:
    """Dispatch explicitly registered packet IDs; unknown IDs are returned intact."""

    def __init__(self) -> None:
        self._handlers: dict[int, Callable[[bytes], object]] = {}

    def register(self, packet_id: int, decoder: Callable[[bytes], object]) -> None:
        if isinstance(packet_id, bool) or not isinstance(packet_id, int) or packet_id < 0:
            raise ValueError("packet_id must be a non-negative integer")
        if not callable(decoder):
            raise TypeError("decoder must be callable")
        if packet_id in self._handlers:
            raise ValueError(f"decoder already registered for packet ID {packet_id}")
        self._handlers[packet_id] = decoder

    def dispatch(self, packet_id: int, payload: bytes):
        decoder = self._handlers.get(packet_id)
        return (decoder(payload) if decoder is not None else None)


def create_clientbound_dispatcher() -> PlayPacketDispatcher:
    dispatcher = PlayPacketDispatcher()
    dispatcher.register(CLIENTBOUND["block_change"], decode_block_change)
    dispatcher.register(CLIENTBOUND["unload_chunk"], decode_unload_chunk)
    dispatcher.register(CLIENTBOUND["disconnect"], decode_disconnect)
    dispatcher.register(CLIENTBOUND["update_health"], decode_update_health)
    dispatcher.register(CLIENTBOUND["time_update"], decode_time_update)
    dispatcher.register(CLIENTBOUND["player_abilities"], decode_player_abilities)
    return dispatcher


__all__ = [
    "SERVERBOUND", "CLIENTBOUND", "serverbound_teleport_confirm",
    "serverbound_client_status", "serverbound_client_settings", "BlockChange",
    "UnloadChunk", "Disconnect", "UpdateHealth", "TimeUpdate",
    "PlayerAbilities", "decode_block_change", "decode_unload_chunk",
    "decode_disconnect", "decode_update_health", "decode_time_update",
    "decode_player_abilities", "PlayPacketDispatcher",
    "create_clientbound_dispatcher",
]
