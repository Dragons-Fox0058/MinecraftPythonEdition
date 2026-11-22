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
    "tab_complete": 0x01,
    "chat": 0x02,
    "client_status": 0x03,
    "client_settings": 0x04,
    "confirm_transaction": 0x05,
    "enchant_item": 0x06,
    "click_window": 0x07,
    "close_window": 0x08,
    "plugin_message": 0x09,
    "use_entity": 0x0A,
    "keep_alive": 0x0B,
    "player": 0x0C,
    "player_position": 0x0D,
    "player_position_look": 0x0E,
    "player_look": 0x0F,
    "vehicle_move": 0x10,
    "steer_boat": 0x11,
    "craft_recipe_request": 0x12,
    "player_abilities": 0x13,
    "player_digging": 0x14,
    "entity_action": 0x15,
    "steer_vehicle": 0x16,
    "crafting_book_data": 0x17,
    "resource_pack_status": 0x18,
    "held_item_change": 0x19,
    "creative_inventory_action": 0x1A,
    "update_sign": 0x1B,
    "animation": 0x1C,
    "spectate": 0x1D,
    "player_block_placement": 0x1E,
    "use_item": 0x1F,
}
CLIENTBOUND = {
    "chat": 0x0F,
    "window_items": 0x14,
    "set_slot": 0x16,
    "disconnect": 0x1A,
    "unload_chunk": 0x1D,
    "keep_alive": 0x1F,
    "entity_status": 0x1B,
    "explosion": 0x1C,
    "chunk_data": 0x20,
    "effect": 0x21,
    "particle": 0x22,
    "join_game": 0x23,
    "map": 0x24,
    "entity": 0x25,
    "entity_relative_move": 0x26,
    "entity_look_and_relative_move": 0x27,
    "entity_look": 0x28,
    "vehicle_move": 0x29,
    "open_sign_editor": 0x2A,
    "craft_recipe_response": 0x2B,
    "player_abilities": 0x2C,
    "combat_event": 0x2D,
    "player_list_item": 0x2E,
    "player_position_look": 0x2F,
    "use_bed": 0x30,
    "unlock_recipes": 0x31,
    "destroy_entities": 0x32,
    "remove_entity_effect": 0x33,
    "resource_pack_send": 0x34,
    "respawn": 0x35,
    "entity_head_look": 0x36,
    "select_advancement_tab": 0x37,
    "world_border": 0x38,
    "camera": 0x39,
    "held_item_change": 0x3A,
    "display_scoreboard": 0x3B,
    "entity_metadata": 0x3C,
    "attach_entity": 0x3D,
    "entity_velocity": 0x3E,
    "entity_equipment": 0x3F,
    "set_experience": 0x40,
    "scoreboard_objective": 0x42,
    "set_passengers": 0x43,
    "teams": 0x44,
    "update_score": 0x45,
    "spawn_position": 0x46,
    "time_update": 0x47,
    "title": 0x48,
    "sound_effect": 0x49,
    "player_list_header_footer": 0x4A,
    "collect_item": 0x4B,
    "entity_teleport": 0x4C,
    "advancements": 0x4D,
    "entity_properties": 0x4E,
    "entity_effect": 0x4F,
    "update_health": 0x41,
    "spawn_object": 0x00,
    "spawn_experience_orb": 0x01,
    "spawn_global_entity": 0x02,
    "spawn_mob": 0x03,
    "spawn_painting": 0x04,
    "spawn_player": 0x05,
    "animation": 0x06,
    "statistics": 0x07,
    "block_break_animation": 0x08,
    "update_block_entity": 0x09,
    "block_action": 0x0A,
    "block_change": 0x0B,
    "boss_bar": 0x0C,
    "server_difficulty": 0x0D,
    "tab_complete": 0x0E,
    "multi_block_change": 0x10,
    "confirm_transaction": 0x11,
    "close_window": 0x12,
    "open_window": 0x13,
    "window_items": 0x14,
    "window_property": 0x15,
    "set_slot": 0x16,
    "set_cooldown": 0x17,
    "plugin_message": 0x18,
    "named_sound_effect": 0x19,
    "change_game_state": 0x1E,
}


def serverbound_teleport_confirm(teleport_id: int) -> tuple[int, bytes]:
    if isinstance(teleport_id, bool) or not isinstance(teleport_id, int) or teleport_id < 0:
        raise ValueError("teleport_id must be a non-negative integer")
    out = PacketBuffer()
    out.write_varint(teleport_id)
    return SERVERBOUND["teleport_confirm"], out.to_bytes()


def serverbound_client_status(action: int) -> tuple[int, bytes]:
    # 0 = respawn, 1 = request statistics.
    if isinstance(action, bool) or not isinstance(action, int) or action not in (0, 1):
        raise ValueError("client status action must be 0 or 1")
    out = PacketBuffer()
    out.write_varint(action)
    return SERVERBOUND["client_status"], out.to_bytes()


def serverbound_player_abilities(flags: int, flying_speed: float = 0.05,
                                 walking_speed: float = 0.1) -> tuple[int, bytes]:
    if isinstance(flags, bool) or not isinstance(flags, int) or flags & ~0x0F:
        raise ValueError("player ability flags must be a 4-bit mask")
    if not all(math.isfinite(value) and value >= 0
               for value in (flying_speed, walking_speed)):
        raise ValueError("player ability speeds must be finite and non-negative")
    return SERVERBOUND["player_abilities"], struct.pack(
        ">Bff", flags, float(flying_speed), float(walking_speed)
    )


def serverbound_plugin_message(channel: str, data: bytes) -> tuple[int, bytes]:
    if not isinstance(channel, str) or not 1 <= len(channel) <= 20:
        raise ValueError("plugin channel must contain 1..20 characters")
    if not isinstance(data, bytes):
        raise TypeError("plugin message data must be bytes")
    out = PacketBuffer()
    out.write_string(channel, max_chars=20)
    out.write(data)
    return SERVERBOUND["plugin_message"], out.to_bytes()


def serverbound_use_entity(entity_id: int, action: int, *,
                           target: tuple[float, float, float] | None = None,
                           hand: int = 0) -> tuple[int, bytes]:
    if isinstance(entity_id, bool) or not isinstance(entity_id, int) or entity_id < 0:
        raise ValueError("entity_id must be a non-negative integer")
    if action not in (0, 1, 2):
        raise ValueError("entity interaction action must be 0, 1, or 2")
    if action == 2:
        if target is None or len(target) != 3 or not all(math.isfinite(v) for v in target):
            raise ValueError("interact-at action requires a finite 3D target")
    elif target is not None:
        raise ValueError("target coordinates are only valid for interact-at")
    if action in (0, 2) and hand not in (0, 1):
        raise ValueError("hand must be 0 or 1")
    out = PacketBuffer()
    out.write_varint(entity_id)
    out.write_varint(action)
    if action == 2:
        out.write(struct.pack(">fff", *target))
    if action in (0, 2):
        out.write_varint(hand)
    return SERVERBOUND["use_entity"], out.to_bytes()


def serverbound_entity_action(entity_id: int, action: int,
                              jump_boost: int = 0) -> tuple[int, bytes]:
    if isinstance(entity_id, bool) or not isinstance(entity_id, int):
        raise ValueError("entity_id must be an integer")
    if isinstance(action, bool) or not isinstance(action, int) or not 0 <= action <= 8:
        raise ValueError("entity action must be 0..8")
    if isinstance(jump_boost, bool) or not isinstance(jump_boost, int) or jump_boost < 0:
        raise ValueError("jump_boost must be non-negative")
    out = PacketBuffer()
    out.write(struct.pack(">i", entity_id))
    out.write_varint(action)
    out.write_varint(jump_boost)
    return SERVERBOUND["entity_action"], out.to_bytes()


def serverbound_use_item(hand: int = 0) -> tuple[int, bytes]:
    if isinstance(hand, bool) or not isinstance(hand, int) or hand not in (0, 1):
        raise ValueError("hand must be 0 or 1")
    out = PacketBuffer()
    out.write_varint(hand)
    return SERVERBOUND["use_item"], out.to_bytes()


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
class MultiBlockChange:
    chunk_x: int
    chunk_z: int
    records: tuple[BlockChange, ...]


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
    fov_modifier: float


@dataclass(frozen=True)
class Respawn:
    dimension: int
    difficulty: int
    game_mode: int
    level_type: str


@dataclass(frozen=True)
class PluginMessage:
    channel: str
    data: bytes


@dataclass(frozen=True)
class ChangeGameState:
    reason: int
    value: float


def decode_block_change(payload: bytes) -> BlockChange:
    buf = PacketBuffer(payload)
    x, y, z = buf.read_position()
    state_id = buf.read_varint()
    if state_id < 0 or buf.remaining:
        raise ProtocolError("invalid Block Change payload")
    return BlockChange(x, y, z, state_id)


def decode_multi_block_change(payload: bytes) -> MultiBlockChange:
    buf = PacketBuffer(payload)
    chunk_x, chunk_z = struct.unpack(">ii", buf.read(8))
    count = buf.read_varint()
    if not 0 <= count <= 4096:
        raise ProtocolError("invalid Multi Block Change record count")
    records = []
    for _ in range(count):
        horizontal = buf.read(1)[0]
        y = buf.read(1)[0]
        state_id = buf.read_varint()
        if state_id < 0:
            raise ProtocolError("negative block state in Multi Block Change")
        x = chunk_x * 16 + ((horizontal >> 4) & 0x0F)
        z = chunk_z * 16 + (horizontal & 0x0F)
        records.append(BlockChange(x, y, z, state_id))
    if buf.remaining:
        raise ProtocolError("trailing Multi Block Change payload")
    return MultiBlockChange(chunk_x, chunk_z, tuple(records))


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
    if buf.remaining or not math.isfinite(health) or not math.isfinite(saturation) or not 0 <= food <= 20 or saturation < 0:
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
    if flying < 0 or walking < 0:
        raise ProtocolError("player ability modifiers cannot be negative")
    return PlayerAbilities(flags, flying, walking)


def decode_respawn(payload: bytes) -> Respawn:
    buf = PacketBuffer(payload)
    dimension = struct.unpack(">i", buf.read(4))[0]
    difficulty, game_mode = buf.read(2)
    level_type = buf.read_string(max_chars=16)
    if buf.remaining or difficulty > 3 or game_mode & 0x07 > 3:
        raise ProtocolError("invalid Respawn payload")
    return Respawn(dimension, difficulty, game_mode, level_type)


def decode_plugin_message(payload: bytes) -> PluginMessage:
    buf = PacketBuffer(payload)
    channel = buf.read_string(max_chars=20)
    if not channel:
        raise ProtocolError("plugin message channel cannot be empty")
    return PluginMessage(channel, buf.read_remaining())


def decode_change_game_state(payload: bytes) -> ChangeGameState:
    if len(payload) != 5:
        raise ProtocolError("Change Game State payload must be exactly 5 bytes")
    reason, value = struct.unpack(">Bf", payload)
    if not math.isfinite(value):
        raise ProtocolError("Change Game State value must be finite")
    return ChangeGameState(reason, value)


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
    dispatcher.register(CLIENTBOUND["multi_block_change"], decode_multi_block_change)
    dispatcher.register(CLIENTBOUND["unload_chunk"], decode_unload_chunk)
    dispatcher.register(CLIENTBOUND["disconnect"], decode_disconnect)
    dispatcher.register(CLIENTBOUND["update_health"], decode_update_health)
    dispatcher.register(CLIENTBOUND["time_update"], decode_time_update)
    dispatcher.register(CLIENTBOUND["player_abilities"], decode_player_abilities)
    dispatcher.register(CLIENTBOUND["respawn"], decode_respawn)
    dispatcher.register(CLIENTBOUND["plugin_message"], decode_plugin_message)
    dispatcher.register(CLIENTBOUND["change_game_state"], decode_change_game_state)
    return dispatcher


__all__ = [
    "SERVERBOUND", "CLIENTBOUND", "serverbound_teleport_confirm",
    "serverbound_client_status", "serverbound_client_settings", "BlockChange",
    "UnloadChunk", "Disconnect", "UpdateHealth", "TimeUpdate",
    "PlayerAbilities", "Respawn", "PluginMessage", "ChangeGameState",
    "MultiBlockChange", "decode_block_change", "decode_multi_block_change",
    "decode_unload_chunk", "decode_disconnect",
    "decode_update_health", "decode_time_update", "decode_player_abilities",
    "decode_respawn", "decode_plugin_message", "decode_change_game_state",
    "serverbound_player_abilities", "serverbound_plugin_message",
    "serverbound_use_entity", "serverbound_entity_action", "serverbound_use_item",
    "PlayPacketDispatcher",
    "create_clientbound_dispatcher",
]
