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
        "serverbound_chat": 0x02, "serverbound_keep_alive": 0x0B,
        "serverbound_player": 0x0C, "serverbound_position": 0x0D,
        "serverbound_position_look": 0x0E, "serverbound_look": 0x0F,
        "serverbound_player_abilities": 0x13, "serverbound_digging": 0x14,
        "serverbound_held_item": 0x19,
        "serverbound_block_placement": 0x1E, "serverbound_use_item": 0x1F,
        "clientbound_chat": 0x0F, "clientbound_disconnect": 0x1A,
        "clientbound_keep_alive": 0x1F, "clientbound_chunk_data": 0x20,
        "clientbound_join_game": 0x23, "clientbound_player_position": 0x2F,
        "clientbound_player_abilities": 0x2C,
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
