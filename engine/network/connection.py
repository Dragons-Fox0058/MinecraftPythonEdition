"""Protocol 340 connection state and handshake packet helpers."""
from __future__ import annotations

import json
import math
import socket
import struct
from enum import Enum

from engine.network.codec import (
    PROTOCOL_VERSION, MAX_PACKET_LENGTH, PacketBuffer, ProtocolError,
    encode_packet, decode_packet, encode_compressed_packet,
    decode_compressed_packet,
)


class ConnectionState(Enum):
    HANDSHAKE = "handshake"
    STATUS = "status"
    LOGIN = "login"
    PLAY = "play"


# Packet IDs from the 1.12.2 protocol (340).
PACKET_IDS = {
    ConnectionState.HANDSHAKE: {"handshake": 0x00},
    ConnectionState.STATUS: {"status_request": 0x00, "ping": 0x01},
    ConnectionState.LOGIN: {"login_start": 0x00, "encryption_response": 0x01},
    ConnectionState.PLAY: {
        # Serverbound Play packets.
        "serverbound_teleport_confirm": 0x00,
        "serverbound_tab_complete": 0x01,
        "serverbound_chat": 0x02,
        "serverbound_client_status": 0x03,
        "serverbound_client_settings": 0x04,
        "serverbound_confirm_transaction": 0x05,
        "serverbound_enchant_item": 0x06,
        "serverbound_click_window": 0x07,
        "serverbound_close_window": 0x08,
        "serverbound_plugin_message": 0x09,
        "serverbound_use_entity": 0x0A,
        "serverbound_keep_alive": 0x0B,
        "serverbound_player": 0x0C,
        "serverbound_position": 0x0D,
        "serverbound_position_look": 0x0E,
        "serverbound_look": 0x0F,
        "serverbound_vehicle_move": 0x10,
        "serverbound_steer_boat": 0x11,
        "serverbound_craft_recipe_request": 0x12,
        "serverbound_player_abilities": 0x13,
        "serverbound_digging": 0x14,
        "serverbound_entity_action": 0x15,
        "serverbound_steer_vehicle": 0x16,
        "serverbound_crafting_book_data": 0x17,
        "serverbound_resource_pack_status": 0x18,
        "serverbound_held_item": 0x19,
        "serverbound_creative_inventory_action": 0x1A,
        "serverbound_update_sign": 0x1B,
        "serverbound_animation": 0x1C,
        "serverbound_spectate": 0x1D,
        "serverbound_block_placement": 0x1E,
        "serverbound_use_item": 0x1F,
        # Clientbound Play packets.
        "clientbound_spawn_object": 0x00,
        "clientbound_spawn_experience_orb": 0x01,
        "clientbound_spawn_global_entity": 0x02,
        "clientbound_spawn_mob": 0x03,
        "clientbound_spawn_painting": 0x04,
        "clientbound_spawn_player": 0x05,
        "clientbound_animation": 0x06,
        "clientbound_statistics": 0x07,
        "clientbound_block_break_animation": 0x08,
        "clientbound_update_block_entity": 0x09,
        "clientbound_block_action": 0x0A,
        "clientbound_block_change": 0x0B,
        "clientbound_boss_bar": 0x0C,
        "clientbound_server_difficulty": 0x0D,
        "clientbound_tab_complete": 0x0E,
        "clientbound_chat": 0x0F,
        "clientbound_multi_block_change": 0x10,
        "clientbound_confirm_transaction": 0x11,
        "clientbound_close_window": 0x12,
        "clientbound_open_window": 0x13,
        "clientbound_window_items": 0x14,
        "clientbound_window_property": 0x15,
        "clientbound_set_slot": 0x16,
        "clientbound_set_cooldown": 0x17,
        "clientbound_plugin_message": 0x18,
        "clientbound_named_sound_effect": 0x19,
        "clientbound_disconnect": 0x1A,
        "clientbound_entity_status": 0x1B,
        "clientbound_explosion": 0x1C,
        "clientbound_unload_chunk": 0x1D,
        "clientbound_change_game_state": 0x1E,
        "clientbound_keep_alive": 0x1F,
        "clientbound_chunk_data": 0x20,
        "clientbound_effect": 0x21,
        "clientbound_particle": 0x22,
        "clientbound_join_game": 0x23,
        "clientbound_map": 0x24,
        "clientbound_entity": 0x25,
        "clientbound_entity_relative_move": 0x26,
        "clientbound_entity_look_and_relative_move": 0x27,
        "clientbound_entity_look": 0x28,
        "clientbound_vehicle_move": 0x29,
        "clientbound_open_sign_editor": 0x2A,
        "clientbound_craft_recipe_response": 0x2B,
        "clientbound_player_abilities": 0x2C,
        "clientbound_combat_event": 0x2D,
        "clientbound_player_list_item": 0x2E,
        "clientbound_player_position": 0x2F,
        "clientbound_use_bed": 0x30,
        "clientbound_unlock_recipes": 0x31,
        "clientbound_destroy_entities": 0x32,
        "clientbound_remove_entity_effect": 0x33,
        "clientbound_resource_pack_send": 0x34,
        "clientbound_respawn": 0x35,
        "clientbound_entity_head_look": 0x36,
        "clientbound_select_advancement_tab": 0x37,
        "clientbound_world_border": 0x38,
        "clientbound_camera": 0x39,
        "clientbound_held_item_change": 0x3A,
        "clientbound_display_scoreboard": 0x3B,
        "clientbound_entity_metadata": 0x3C,
        "clientbound_attach_entity": 0x3D,
        "clientbound_entity_velocity": 0x3E,
        "clientbound_entity_equipment": 0x3F,
        "clientbound_set_experience": 0x40,
        "clientbound_update_health": 0x41,
        "clientbound_scoreboard_objective": 0x42,
        "clientbound_set_passengers": 0x43,
        "clientbound_teams": 0x44,
        "clientbound_update_score": 0x45,
        "clientbound_spawn_position": 0x46,
        "clientbound_time_update": 0x47,
        "clientbound_title": 0x48,
        "clientbound_sound_effect": 0x49,
        "clientbound_player_list_header_footer": 0x4A,
        "clientbound_collect_item": 0x4B,
        "clientbound_entity_teleport": 0x4C,
        "clientbound_advancements": 0x4D,
        "clientbound_entity_properties": 0x4E,
        "clientbound_entity_effect": 0x4F,
    },
}


def encode_handshake(server_address: str, port: int,
                     next_state: ConnectionState,
                     protocol_version: int = PROTOCOL_VERSION) -> bytes:
    if next_state not in (ConnectionState.STATUS, ConnectionState.LOGIN):
        raise ValueError("handshake next state must be STATUS or LOGIN")
    if not isinstance(server_address, str) or not server_address:
        raise ValueError("server address must be non-empty")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be from 0 to 65535")
    payload = PacketBuffer()
    payload.write_varint(protocol_version)
    payload.write_string(server_address, max_chars=255)
    payload.write(struct.pack(">H", port))
    payload.write_varint(1 if next_state is ConnectionState.STATUS else 2)
    return encode_packet(0x00, payload.to_bytes())


def decode_handshake(payload: bytes) -> tuple[int, str, int, ConnectionState]:
    buffer = PacketBuffer(payload)
    version = buffer.read_varint()
    address = buffer.read_string(max_chars=255)
    port = struct.unpack(">H", buffer.read(2))[0]
    state_id = buffer.read_varint()
    if buffer.remaining:
        raise ProtocolError("trailing handshake payload")
    if state_id == 1:
        state = ConnectionState.STATUS
    elif state_id == 2:
        state = ConnectionState.LOGIN
    else:
        raise ProtocolError("invalid handshake next state")
    return version, address, port, state


def encode_login_start(username: str) -> bytes:
    if not isinstance(username, str) or not 1 <= len(username) <= 16:
        raise ValueError("offline username must contain 1..16 characters")
    payload = PacketBuffer()
    payload.write_string(username, max_chars=16)
    return encode_packet(0x00, payload.to_bytes())


def decode_status_response(payload: bytes) -> dict:
    buffer = PacketBuffer(payload)
    raw = buffer.read_string(max_chars=32767)
    if buffer.remaining:
        raise ProtocolError("trailing status response payload")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProtocolError("invalid status JSON") from exc
    if not isinstance(value, dict):
        raise ProtocolError("status response must be a JSON object")
    return value


class MinecraftConnection:
    """Synchronous framed socket transport; TLS/authentication are not implied."""

    def __init__(self, sock: socket.socket):
        self.socket = sock
        self.state = ConnectionState.HANDSHAKE
        self.compression_threshold: int | None = None
        self._encryptor = None
        self._decryptor = None

    @classmethod
    def connect(cls, host: str, port: int, timeout: float = 10.0):
        sock = socket.create_connection((host, port), timeout=timeout)
        return cls(sock)

    def close(self):
        # Wake a thread blocked in recv() before releasing the socket.
        shutdown = getattr(self.socket, "shutdown", None)
        if callable(shutdown):
            try:
                shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        try:
            self.socket.close()
        except OSError:
            pass

    def set_timeout(self, timeout: float | None) -> None:
        if timeout is not None and (not math.isfinite(timeout) or timeout <= 0):
            raise ValueError("timeout must be positive and finite, or None")
        if hasattr(self.socket, "settimeout"):
            self.socket.settimeout(timeout)

    def _recv_exact(self, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            part = self.socket.recv(size - len(chunks))
            if not part:
                raise EOFError("Minecraft server closed the connection")
            if self._decryptor is not None:
                part = self._decryptor.update(part)
            chunks.extend(part)
        return bytes(chunks)

    def _recv_varint(self) -> tuple[int, bytes]:
        raw = bytearray()
        result = 0
        for index in range(5):
            byte = self._recv_exact(1)[0]
            raw.append(byte)
            if index == 4 and (byte & 0xF0):
                raise ProtocolError("incoming frame length VarInt overflows 32 bits")
            result |= (byte & 0x7F) << (7 * index)
            if not byte & 0x80:
                if result > MAX_PACKET_LENGTH:
                    raise ProtocolError("incoming packet exceeds maximum length")
                return result, bytes(raw)
        raise ProtocolError("incoming frame length VarInt exceeds five bytes")

    def receive(self) -> tuple[int, bytes]:
        length, prefix = self._recv_varint()
        if length <= 0:
            raise ProtocolError("incoming frame length must be positive")
        frame = self._recv_exact(length)
        if self.compression_threshold is None:
            return decode_packet(prefix + frame)
        return decode_compressed_packet(prefix + frame, self.compression_threshold)

    def send(self, packet_id: int, payload: bytes = b""):
        if self.compression_threshold is None:
            frame = encode_packet(packet_id, payload)
        else:
            frame = encode_compressed_packet(packet_id, payload, self.compression_threshold)
        self.send_raw(frame)

    def send_raw(self, data: bytes):
        if self._encryptor is not None:
            data = self._encryptor.update(data)
        self.socket.sendall(data)

    def enable_encryption(self, shared_secret: bytes):
        if not isinstance(shared_secret, bytes) or len(shared_secret) != 16:
            raise ValueError("Minecraft shared secret must be exactly 16 bytes")
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        except ImportError as exc:
            raise RuntimeError("online-mode login requires the cryptography package") from exc
        cipher = Cipher(algorithms.AES(shared_secret), modes.CFB8(shared_secret))
        self._encryptor = cipher.encryptor()
        self._decryptor = cipher.decryptor()

    def set_compression(self, threshold: int):
        if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 0:
            raise ValueError("compression threshold must be a non-negative integer")
        self.compression_threshold = threshold

    def send_handshake(self, host: str, port: int, next_state: ConnectionState):
        self.send_raw(encode_handshake(host, port, next_state))
        self.state = next_state


__all__ = ["ConnectionState", "PACKET_IDS", "encode_handshake",
           "decode_handshake", "encode_login_start", "decode_status_response",
           "MinecraftConnection"]
