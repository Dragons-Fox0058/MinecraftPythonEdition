"""Offline-mode protocol 340 login client.

Online-mode encryption/session authentication is deliberately rejected until
the RSA/AES-CFB8 and Mojang session-authentication components are supplied.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from engine.network.codec import PacketBuffer, ProtocolError
from engine.network.connection import (
    ConnectionState, MinecraftConnection, encode_login_start,
)


@dataclass(frozen=True)
class LoginIdentity:
    player_uuid: uuid.UUID
    username: str


def login_offline(host: str, port: int, username: str, timeout: float = 10.0):
    """Log into an offline-mode 1.12.2 server and return (connection, identity)."""
    connection = MinecraftConnection.connect(host, port, timeout)
    try:
        connection.send_handshake(host, port, ConnectionState.LOGIN)
        connection.socket.sendall(encode_login_start(username))
        while True:
            packet_id, payload = connection.receive()
            if packet_id == 0x03:  # Set Compression
                buffer = PacketBuffer(payload)
                threshold = buffer.read_varint()
                if buffer.remaining:
                    raise ProtocolError("trailing Set Compression payload")
                connection.set_compression(threshold)
                continue
            if packet_id == 0x00:  # Login Disconnect
                buffer = PacketBuffer(payload)
                reason = buffer.read_string()
                try:
                    detail = json.loads(reason)
                except json.JSONDecodeError:
                    detail = reason
                raise ProtocolError(f"login rejected: {detail}")
            if packet_id == 0x01:  # Encryption Request
                raise ProtocolError(
                    "server requires online-mode encryption; this client currently supports offline-mode only"
                )
            if packet_id == 0x02:  # Login Success
                buffer = PacketBuffer(payload)
                raw_uuid = buffer.read_string(max_chars=36)
                accepted_name = buffer.read_string(max_chars=16)
                if buffer.remaining:
                    raise ProtocolError("trailing Login Success payload")
                try:
                    player_uuid = uuid.UUID(raw_uuid)
                except ValueError as exc:
                    raise ProtocolError("invalid Login Success UUID") from exc
                if accepted_name != username:
                    raise ProtocolError("server returned a different username")
                connection.state = ConnectionState.PLAY
                return connection, LoginIdentity(player_uuid, accepted_name)
            raise ProtocolError(f"unexpected login packet ID: {packet_id}")
    except Exception:
        connection.close()
        raise


__all__ = ["LoginIdentity", "login_offline"]
